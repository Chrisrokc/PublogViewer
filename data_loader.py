"""
Data loading and indexing utilities for PubLog Application
Handles initial data indexing and provides query interfaces
"""
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from database import get_db, PubLogDatabase
from config import MAX_SEARCH_RESULTS, DEFAULT_PAGE_SIZE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataLoader:
    """Handles data loading and provides query interfaces"""

    def __init__(self):
        self.db = get_db()

    def initialize_database(self, force: bool = False, priority_only: bool = False) -> Dict[str, Any]:
        """Initialize the database by indexing all CSV files"""
        logger.info("Starting database initialization...")

        if priority_only:
            results = self.db.index_priority_tables(force)
        else:
            results = self.db.index_all_tables(force)

        # Create useful indexes
        self._create_search_indexes()

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Indexed {success_count}/{len(results)} tables successfully")

        return {
            "success": success_count == len(results),
            "indexed": success_count,
            "total": len(results),
            "details": results
        }

    def _create_search_indexes(self):
        """Create indexes for common search patterns"""
        index_definitions = {
            "P_CAGE": ["CAGE_CODE", "COMPANY", "CITY", "STATE_PROVINCE"],
            "V_H2_FSC": ["FSC", "FSC_TITLE"],
            "V_H2_FSG": ["FSG", "FSG_TITLE"],
            "V_H6_NAME_INC": ["INC", "FIIG_TITLE"],
            "V_FLIS_IDENTIFICATION": ["NIIN", "FSC", "ITEM_NAME"],
            "P_FLIS_NSN": ["NIIN", "FSC"],
            "FLISV": ["NIIN", "FSC"],
        }

        for table, columns in index_definitions.items():
            if self.db.is_table_indexed(table):
                self.db.create_indexes(table, columns)


class CAGEService:
    """Service for CAGE (Contractor) data queries"""

    def __init__(self):
        self.db = get_db()

    def get_by_code(self, cage_code: str) -> Optional[Dict[str, Any]]:
        """Get CAGE record by code"""
        results = self.db.query(
            "SELECT * FROM P_CAGE WHERE CAGE_CODE = ? LIMIT 1",
            [cage_code.upper()]
        )
        return results[0] if results else None

    def search(self, query: str, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0) -> List[Dict[str, Any]]:
        """Search CAGE records by company name, city, or code"""
        search_term = f"%{query.upper()}%"
        return self.db.query(f"""
            SELECT * FROM P_CAGE
            WHERE UPPER(COMPANY) LIKE ?
               OR UPPER(CITY) LIKE ?
               OR CAGE_CODE LIKE ?
            ORDER BY COMPANY
            LIMIT ? OFFSET ?
        """, [search_term, search_term, search_term, limit, offset])

    def search_by_location(self, state: Optional[str] = None,
                           city: Optional[str] = None,
                           country: Optional[str] = None,
                           limit: int = DEFAULT_PAGE_SIZE) -> List[Dict[str, Any]]:
        """Search CAGE records by location"""
        conditions = []
        params = []

        if state:
            conditions.append("UPPER(STATE_PROVINCE) = ?")
            params.append(state.upper())
        if city:
            conditions.append("UPPER(CITY) LIKE ?")
            params.append(f"%{city.upper()}%")
        if country:
            conditions.append("UPPER(COUNTRY) LIKE ?")
            params.append(f"%{country.upper()}%")

        if not conditions:
            return []

        where_clause = " AND ".join(conditions)
        params.append(limit)

        return self.db.query(f"""
            SELECT * FROM P_CAGE
            WHERE {where_clause}
            ORDER BY COMPANY
            LIMIT ?
        """, params)

    def get_stats(self) -> Dict[str, Any]:
        """Get CAGE statistics"""
        try:
            total = self.db.query("SELECT COUNT(*) as count FROM P_CAGE")[0]["count"]
            by_status = self.db.query("""
                SELECT CAGE_STATUS, COUNT(*) as count
                FROM P_CAGE
                GROUP BY CAGE_STATUS
                ORDER BY count DESC
            """)
            by_country = self.db.query("""
                SELECT COUNTRY, COUNT(*) as count
                FROM P_CAGE
                GROUP BY COUNTRY
                ORDER BY count DESC
                LIMIT 10
            """)
            return {
                "total_records": total,
                "by_status": by_status,
                "top_countries": by_country
            }
        except Exception as e:
            logger.error(f"Error getting CAGE stats: {e}")
            return {}


class FSCService:
    """Service for Federal Supply Classification queries"""

    def __init__(self):
        self.db = get_db()

    def get_all_fsg(self) -> List[Dict[str, Any]]:
        """Get all Federal Supply Groups"""
        # FSG table uses FSC column but contains 4-digit FSC codes with FSG_TITLE
        # Get unique FSG (first 2 digits) with titles
        return self.db.query("""
            SELECT DISTINCT
                CAST(FSC / 100 AS INTEGER) as FSG,
                FSG_TITLE
            FROM V_H2_FSG
            ORDER BY FSG
        """)

    def get_all_fsc(self) -> List[Dict[str, Any]]:
        """Get all Federal Supply Classes"""
        return self.db.query("""
            SELECT * FROM V_H2_FSC
            ORDER BY FSC
        """)

    def get_fsc_by_code(self, fsc: str) -> Optional[Dict[str, Any]]:
        """Get FSC details by code"""
        # Handle both numeric and string FSC codes
        try:
            fsc_int = int(fsc)
            results = self.db.query(
                "SELECT * FROM V_H2_FSC WHERE FSC = ? LIMIT 1",
                [fsc_int]
            )
        except ValueError:
            results = self.db.query(
                "SELECT * FROM V_H2_FSC WHERE CAST(FSC AS VARCHAR) = ? LIMIT 1",
                [fsc]
            )
        return results[0] if results else None

    def get_fsc_by_fsg(self, fsg: str) -> List[Dict[str, Any]]:
        """Get all FSCs within a FSG"""
        # FSG is first 2 digits of FSC
        try:
            fsg_int = int(fsg)
            return self.db.query("""
                SELECT * FROM V_H2_FSC
                WHERE FSC >= ? AND FSC < ?
                ORDER BY FSC
            """, [fsg_int * 100, (fsg_int + 1) * 100])
        except ValueError:
            return []

    def search_fsc(self, query: str) -> List[Dict[str, Any]]:
        """Search FSC by name or code"""
        search_term = f"%{query.upper()}%"
        # Handle numeric FSC code search
        try:
            fsc_int = int(query)
            return self.db.query("""
                SELECT * FROM V_H2_FSC
                WHERE FSC = ? OR UPPER(FSC_TITLE) LIKE ?
                ORDER BY FSC
                LIMIT 100
            """, [fsc_int, search_term])
        except ValueError:
            # Text search only
            return self.db.query("""
                SELECT * FROM V_H2_FSC
                WHERE UPPER(FSC_TITLE) LIKE ?
                ORDER BY FSC
                LIMIT 100
            """, [search_term])


class NSNService:
    """Service for National Stock Number queries"""

    def __init__(self):
        self.db = get_db()

    def get_by_niin(self, niin: str) -> Optional[Dict[str, Any]]:
        """Get NSN record by NIIN"""
        # P_FLIS_NSN has FSC, ITEM_NAME - use it first for useful info
        if self.db.is_table_indexed("P_FLIS_NSN"):
            results = self.db.query(
                "SELECT * FROM P_FLIS_NSN WHERE NIIN = ? LIMIT 1",
                [niin]
            )
            if results:
                return results[0]

        # Fallback to FLISV (has characteristics data but no ITEM_NAME)
        if self.db.is_table_indexed("FLISV"):
            results = self.db.query(
                "SELECT * FROM FLISV WHERE NIIN = ? LIMIT 1",
                [niin]
            )
            if results:
                return results[0]

        return None

    def search(self, query: str, fsc: Optional[str] = None,
               limit: int = DEFAULT_PAGE_SIZE, offset: int = 0) -> List[Dict[str, Any]]:
        """Search NSN records"""
        # P_FLIS_NSN has ITEM_NAME and FSC - use it for searches
        # FLISV only has NIIN and characteristics data, no ITEM_NAME
        if not self.db.is_table_indexed("P_FLIS_NSN"):
            logger.warning("P_FLIS_NSN table not indexed - cannot search")
            return []

        conditions = []
        params = []

        # Text search - search by NIIN or ITEM_NAME
        if query:
            search_term = f"%{query.upper()}%"
            conditions.append("(NIIN LIKE ? OR UPPER(ITEM_NAME) LIKE ?)")
            params.extend([search_term, search_term])

        # FSC filter
        if fsc:
            try:
                fsc_int = int(fsc)
                conditions.append("FSC = ?")
                params.append(fsc_int)
            except ValueError:
                conditions.append("CAST(FSC AS VARCHAR) = ?")
                params.append(fsc)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit, offset])

        return self.db.query(f"""
            SELECT * FROM P_FLIS_NSN
            WHERE {where_clause}
            LIMIT ? OFFSET ?
        """, params)

    def get_by_fsc(self, fsc: str, limit: int = DEFAULT_PAGE_SIZE,
                   offset: int = 0) -> List[Dict[str, Any]]:
        """Get NSN records by FSC"""
        # P_FLIS_NSN has FSC column, FLISV does not - prioritize P_FLIS_NSN for FSC queries
        if self.db.is_table_indexed("P_FLIS_NSN"):
            try:
                fsc_int = int(fsc)
                return self.db.query("""
                    SELECT * FROM P_FLIS_NSN
                    WHERE FSC = ?
                    LIMIT ? OFFSET ?
                """, [fsc_int, limit, offset])
            except ValueError:
                return self.db.query("""
                    SELECT * FROM P_FLIS_NSN
                    WHERE CAST(FSC AS VARCHAR) = ?
                    LIMIT ? OFFSET ?
                """, [fsc, limit, offset])

        return []

    def get_management_data(self, niin: str) -> List[Dict[str, Any]]:
        """Get management data for a NIIN"""
        if not self.db.is_table_indexed("V_FLIS_MANAGEMENT"):
            return []

        return self.db.query("""
            SELECT * FROM V_FLIS_MANAGEMENT
            WHERE NIIN = ?
        """, [niin])

    def get_characteristics(self, niin: str) -> List[Dict[str, Any]]:
        """Get characteristics for a NIIN"""
        if not self.db.is_table_indexed("V_CHARACTERISTICS"):
            return []

        return self.db.query("""
            SELECT * FROM V_CHARACTERISTICS
            WHERE NIIN = ?
        """, [niin])


class ItemNameService:
    """Service for Item Name (INC) queries"""

    def __init__(self):
        self.db = get_db()

    def get_by_inc(self, inc: str) -> Optional[Dict[str, Any]]:
        """Get item name by INC code"""
        results = self.db.query(
            "SELECT * FROM V_H6_NAME_INC WHERE INC = ? LIMIT 1",
            [inc]
        )
        return results[0] if results else None

    def search(self, query: str, limit: int = DEFAULT_PAGE_SIZE) -> List[Dict[str, Any]]:
        """Search item names"""
        search_term = f"%{query.upper()}%"
        return self.db.query("""
            SELECT * FROM V_H6_NAME_INC
            WHERE UPPER(FIIG_TITLE) LIKE ?
               OR UPPER(DEFINITION) LIKE ?
               OR INC LIKE ?
            ORDER BY FIIG_TITLE
            LIMIT ?
        """, [search_term, search_term, search_term, limit])

    def get_all(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all item names (limited)"""
        return self.db.query(f"""
            SELECT * FROM V_H6_NAME_INC
            ORDER BY FIIG_TITLE
            LIMIT {limit}
        """)


class UnifiedSearchService:
    """Unified search across multiple data types"""

    def __init__(self):
        self.db = get_db()
        self.cage_service = CAGEService()
        self.fsc_service = FSCService()
        self.nsn_service = NSNService()
        self.item_name_service = ItemNameService()

    def search_all(self, query: str, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """Search across all data types"""
        results = {
            "cage": [],
            "fsc": [],
            "nsn": [],
            "item_names": []
        }

        # Search CAGE
        try:
            results["cage"] = self.cage_service.search(query, limit=limit)
        except Exception as e:
            logger.error(f"CAGE search error: {e}")

        # Search FSC
        try:
            results["fsc"] = self.fsc_service.search_fsc(query)[:limit]
        except Exception as e:
            logger.error(f"FSC search error: {e}")

        # Search NSN
        try:
            results["nsn"] = self.nsn_service.search(query, limit=limit)
        except Exception as e:
            logger.error(f"NSN search error: {e}")

        # Search Item Names
        try:
            results["item_names"] = self.item_name_service.search(query, limit=limit)
        except Exception as e:
            logger.error(f"Item name search error: {e}")

        return results
