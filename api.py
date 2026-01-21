"""
FastAPI REST API for PubLog Data
Provides endpoints for external applications to query PubLog data
"""
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from config import API_PREFIX, DEFAULT_PAGE_SIZE, MAX_SEARCH_RESULTS
from data_loader import (
    CAGEService, FSCService, NSNService, ItemNameService,
    UnifiedSearchService, DataLoader
)
from database import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PubLog API",
    description="""
    REST API for Federal Logistics Information Service (FLIS) / PubLog Data.

    Provides access to:
    - **CAGE** - Commercial and Government Entity codes (contractor data)
    - **NSN** - National Stock Numbers (item identification)
    - **FSC/FSG** - Federal Supply Classification codes
    - **Item Names** - Item nomenclature and definitions
    - **Management Data** - Pricing, units, service-specific data

    All endpoints are unauthenticated for prototype purposes.
    """,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
cage_service = CAGEService()
fsc_service = FSCService()
nsn_service = NSNService()
item_name_service = ItemNameService()
search_service = UnifiedSearchService()


# ============== Pydantic Models ==============

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    database_connected: bool
    indexed_tables: int


class PaginatedResponse(BaseModel):
    data: List[Dict[str, Any]]
    count: int
    limit: int
    offset: int


class SearchResponse(BaseModel):
    query: str
    results: Dict[str, List[Dict[str, Any]]]
    total_results: int


class CAGERecord(BaseModel):
    CAGE_CODE: str
    CAGE_STATUS: Optional[str] = None
    TYPE: Optional[str] = None
    CAO: Optional[str] = None
    COMPANY: Optional[str] = None
    CITY: Optional[str] = None
    STATE_PROVINCE: Optional[str] = None
    ZIP_POSTAL_ZONE: Optional[str] = None
    COUNTRY: Optional[str] = None


class FSCRecord(BaseModel):
    FSC: str
    FSC_NAME: Optional[str] = None


class FSGRecord(BaseModel):
    FSG: str
    FSG_NAME: Optional[str] = None


class DatabaseStats(BaseModel):
    total_tables: int
    total_rows: int
    tables: List[Dict[str, Any]]
    db_file_size_mb: float


# ============== Health & Status Endpoints ==============

@app.get(f"{API_PREFIX}/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check API health and database connection status"""
    try:
        db = get_db()
        tables = db.get_indexed_tables()
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            database_connected=True,
            indexed_tables=len(tables)
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow().isoformat(),
            database_connected=False,
            indexed_tables=0
        )


@app.get(f"{API_PREFIX}/stats", response_model=DatabaseStats, tags=["System"])
async def get_database_stats():
    """Get database statistics including table counts and sizes"""
    try:
        db = get_db()
        return db.get_database_stats()
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{API_PREFIX}/tables", tags=["System"])
async def list_tables():
    """List all indexed tables"""
    try:
        db = get_db()
        tables = db.get_indexed_tables()
        return {"tables": tables, "count": len(tables)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{API_PREFIX}/tables/{{table_name}}/info", tags=["System"])
async def get_table_info(table_name: str):
    """Get information about a specific table"""
    try:
        db = get_db()
        info = db.get_table_info(table_name)
        if not info:
            raise HTTPException(status_code=404, detail=f"Table {table_name} not found")
        return info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Unified Search ==============

@app.get(f"{API_PREFIX}/search", response_model=SearchResponse, tags=["Search"])
async def unified_search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_SEARCH_RESULTS, description="Results per category")
):
    """
    Search across all data types (CAGE, NSN, FSC, Item Names).
    Returns results grouped by category.
    """
    try:
        results = search_service.search_all(q, limit=limit)
        total = sum(len(v) for v in results.values())
        return SearchResponse(
            query=q,
            results=results,
            total_results=total
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== CAGE Endpoints ==============
# Note: Specific paths must come before parameterized paths

@app.get(f"{API_PREFIX}/cage/search", tags=["CAGE"])
async def search_cage(
    q: str = Query(..., min_length=1, description="Search query (company name, city, or code)"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_SEARCH_RESULTS),
    offset: int = Query(0, ge=0)
):
    """Search CAGE records by company name, city, or code"""
    results = cage_service.search(q, limit=limit, offset=offset)
    return {
        "data": results,
        "count": len(results),
        "limit": limit,
        "offset": offset
    }


@app.get(f"{API_PREFIX}/cage/location", tags=["CAGE"])
async def search_cage_by_location(
    state: Optional[str] = Query(None, description="State/Province code"),
    city: Optional[str] = Query(None, description="City name"),
    country: Optional[str] = Query(None, description="Country name"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_SEARCH_RESULTS)
):
    """Search CAGE records by location"""
    if not any([state, city, country]):
        raise HTTPException(status_code=400, detail="At least one location parameter required")

    results = cage_service.search_by_location(state=state, city=city, country=country, limit=limit)
    return {
        "data": results,
        "count": len(results),
        "limit": limit,
        "offset": 0
    }


@app.get(f"{API_PREFIX}/cage/stats", tags=["CAGE"])
async def get_cage_stats():
    """Get CAGE statistics (counts by status, top countries)"""
    return cage_service.get_stats()


@app.get(f"{API_PREFIX}/cage/{{cage_code}}", tags=["CAGE"])
async def get_cage_by_code(
    cage_code: str = Path(..., min_length=5, max_length=5, description="5-character CAGE code")
):
    """Get CAGE record by code"""
    result = cage_service.get_by_code(cage_code)
    if not result:
        raise HTTPException(status_code=404, detail=f"CAGE code {cage_code} not found")
    return result


# ============== FSC/FSG Endpoints ==============
# Note: Specific paths must come before parameterized paths

@app.get(f"{API_PREFIX}/fsg", tags=["FSC/FSG"])
async def list_all_fsg():
    """List all Federal Supply Groups"""
    results = fsc_service.get_all_fsg()
    return {"data": results, "count": len(results)}


@app.get(f"{API_PREFIX}/fsc", tags=["FSC/FSG"])
async def list_all_fsc():
    """List all Federal Supply Classes"""
    results = fsc_service.get_all_fsc()
    return {"data": results, "count": len(results)}


@app.get(f"{API_PREFIX}/fsc/search", tags=["FSC/FSG"])
async def search_fsc(
    q: str = Query(..., min_length=1, description="Search query")
):
    """Search FSC by name or code"""
    results = fsc_service.search_fsc(q)
    return {"data": results, "count": len(results)}


@app.get(f"{API_PREFIX}/fsg/{{fsg_code}}/fsc", tags=["FSC/FSG"])
async def get_fsc_by_fsg(
    fsg_code: str = Path(..., min_length=2, max_length=2, description="2-digit FSG code")
):
    """Get all FSCs within a Federal Supply Group"""
    results = fsc_service.get_fsc_by_fsg(fsg_code)
    return {"data": results, "count": len(results)}


@app.get(f"{API_PREFIX}/fsc/{{fsc_code}}", tags=["FSC/FSG"])
async def get_fsc_by_code(
    fsc_code: str = Path(..., min_length=4, max_length=4, description="4-digit FSC code")
):
    """Get FSC details by code"""
    result = fsc_service.get_fsc_by_code(fsc_code)
    if not result:
        raise HTTPException(status_code=404, detail=f"FSC {fsc_code} not found")
    return result


# ============== NSN Endpoints ==============

@app.get(f"{API_PREFIX}/nsn/{{niin}}", tags=["NSN"])
async def get_nsn_by_niin(
    niin: str = Path(..., min_length=9, max_length=9, description="9-digit NIIN")
):
    """Get NSN record by NIIN (National Item Identification Number)"""
    result = nsn_service.get_by_niin(niin)
    if not result:
        raise HTTPException(status_code=404, detail=f"NIIN {niin} not found")
    return result


@app.get(f"{API_PREFIX}/nsn/search", tags=["NSN"])
async def search_nsn(
    q: str = Query(..., min_length=1, description="Search query (NIIN or item name)"),
    fsc: Optional[str] = Query(None, min_length=4, max_length=4, description="Filter by FSC"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_SEARCH_RESULTS),
    offset: int = Query(0, ge=0)
):
    """Search NSN records by NIIN or item name"""
    results = nsn_service.search(q, fsc=fsc, limit=limit, offset=offset)
    return {
        "data": results,
        "count": len(results),
        "limit": limit,
        "offset": offset
    }


@app.get(f"{API_PREFIX}/nsn/fsc/{{fsc_code}}", tags=["NSN"])
async def get_nsn_by_fsc(
    fsc_code: str = Path(..., min_length=4, max_length=4, description="4-digit FSC code"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_SEARCH_RESULTS),
    offset: int = Query(0, ge=0)
):
    """Get NSN records by Federal Supply Class"""
    results = nsn_service.get_by_fsc(fsc_code, limit=limit, offset=offset)
    return {
        "data": results,
        "count": len(results),
        "limit": limit,
        "offset": offset
    }


@app.get(f"{API_PREFIX}/nsn/{{niin}}/management", tags=["NSN"])
async def get_nsn_management_data(
    niin: str = Path(..., min_length=9, max_length=9, description="9-digit NIIN")
):
    """Get management data (pricing, units, service data) for a NIIN"""
    results = nsn_service.get_management_data(niin)
    return {"data": results, "count": len(results)}


@app.get(f"{API_PREFIX}/nsn/{{niin}}/characteristics", tags=["NSN"])
async def get_nsn_characteristics(
    niin: str = Path(..., min_length=9, max_length=9, description="9-digit NIIN")
):
    """Get characteristics data for a NIIN"""
    results = nsn_service.get_characteristics(niin)
    return {"data": results, "count": len(results)}


# ============== Item Name (INC) Endpoints ==============
# Note: Specific paths must come before parameterized paths

@app.get(f"{API_PREFIX}/inc", tags=["Item Names"])
async def list_item_names(
    limit: int = Query(100, ge=1, le=1000)
):
    """List item names (limited)"""
    results = item_name_service.get_all(limit=limit)
    return {"data": results, "count": len(results)}


@app.get(f"{API_PREFIX}/inc/search", tags=["Item Names"])
async def search_inc(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_SEARCH_RESULTS)
):
    """Search item names by title or definition"""
    results = item_name_service.search(q, limit=limit)
    return {"data": results, "count": len(results)}


@app.get(f"{API_PREFIX}/inc/{{inc_code}}", tags=["Item Names"])
async def get_inc_by_code(
    inc_code: str = Path(..., min_length=5, max_length=5, description="5-digit INC code")
):
    """Get item name by INC (Item Name Code)"""
    result = item_name_service.get_by_inc(inc_code)
    if not result:
        raise HTTPException(status_code=404, detail=f"INC {inc_code} not found")
    return result


# ============== Raw Query Endpoint (Admin) ==============

@app.post(f"{API_PREFIX}/query", tags=["Admin"])
async def execute_query(
    sql: str = Query(..., description="SQL query to execute"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum rows to return")
):
    """
    Execute a raw SQL query (read-only, for admin/debugging).
    Query is limited to SELECT statements only.
    """
    # Basic SQL injection protection
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")

    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"]
    for word in forbidden:
        if word in sql_upper:
            raise HTTPException(status_code=400, detail=f"{word} statements are not allowed")

    try:
        db = get_db()
        # Add LIMIT if not present
        if "LIMIT" not in sql_upper:
            sql = f"{sql.rstrip(';')} LIMIT {limit}"

        results = db.query(sql)
        return {"data": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============== Database Initialization ==============

@app.post(f"{API_PREFIX}/admin/initialize", tags=["Admin"])
async def initialize_database(
    force: bool = Query(False, description="Force re-indexing of all tables"),
    priority_only: bool = Query(False, description="Index only priority tables (faster)")
):
    """
    Initialize/index the database from CSV files.
    This may take several minutes for full indexing.
    """
    try:
        loader = DataLoader()
        result = loader.initialize_database(force=force, priority_only=priority_only)
        return result
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Root redirect to docs
@app.get("/")
async def root():
    """Redirect to API documentation"""
    return {"message": "PubLog API", "docs": "/api/docs", "health": f"{API_PREFIX}/health"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
