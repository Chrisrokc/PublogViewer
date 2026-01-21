"""
Admin Dashboard - Database management and API monitoring
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader import DataLoader
from database import get_db, PubLogDatabase
from config import DATA_FILES, DB_PATH, API_PORT

st.set_page_config(page_title="Admin - PubLog", page_icon="⚙️", layout="wide")

st.title("⚙️ Admin Dashboard")
st.markdown("Database management, indexing, and system monitoring.")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Status", "🗄️ Database", "🔧 Indexing", "📡 API Info"])

with tab1:
    st.subheader("System Status")

    col1, col2, col3 = st.columns(3)

    try:
        db = get_db()
        stats = db.get_database_stats()
        tables = db.get_indexed_tables()

        with col1:
            st.metric("Indexed Tables", stats.get("total_tables", 0))

        with col2:
            st.metric("Total Rows", f"{stats.get('total_rows', 0):,}")

        with col3:
            st.metric("Database Size", f"{stats.get('db_file_size_mb', 0):.1f} MB")

        # Database file info
        st.markdown("---")
        st.markdown("### Database File")
        if DB_PATH.exists():
            st.success(f"✅ Database file exists: `{DB_PATH}`")
            st.write(f"**Size:** {DB_PATH.stat().st_size / (1024*1024):.2f} MB")
            st.write(f"**Modified:** {datetime.fromtimestamp(DB_PATH.stat().st_mtime)}")
        else:
            st.warning("⚠️ Database file not found. Run indexing to create it.")

        # Table list with row counts
        st.markdown("---")
        st.markdown("### Indexed Tables")
        if stats.get("tables"):
            table_df = pd.DataFrame(stats["tables"])
            table_df["rows"] = table_df["rows"].apply(lambda x: f"{x:,}")
            st.dataframe(table_df, use_container_width=True)
        else:
            st.info("No tables indexed yet")

    except Exception as e:
        st.error(f"Error getting system status: {e}")
        st.info("Database may not be initialized. Go to the Indexing tab to set up.")

with tab2:
    st.subheader("Database Management")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Available Data Files")

        # Count files by category
        for category, files in DATA_FILES.items():
            with st.expander(f"📁 {category.upper()} ({len(files)} files)"):
                for name, path in files.items():
                    if path.exists():
                        size_mb = path.stat().st_size / (1024 * 1024)
                        st.write(f"✅ **{name}**: {size_mb:.1f} MB")
                    else:
                        st.write(f"❌ **{name}**: File not found")

    with col2:
        st.markdown("### Database Operations")

        # Check table
        st.markdown("#### Check Table")
        table_name = st.text_input("Enter table name to check")
        if st.button("Check Table") and table_name:
            try:
                db = get_db()
                if db.is_table_indexed(table_name):
                    info = db.get_table_info(table_name)
                    st.success(f"Table '{table_name}' exists")
                    st.write(f"**Rows:** {info.get('row_count', 0):,}")
                    st.write("**Columns:**")
                    for col in info.get("columns", []):
                        st.write(f"  - {col['name']}: {col['type']}")
                else:
                    st.warning(f"Table '{table_name}' not found")
            except Exception as e:
                st.error(f"Error: {e}")

        # Raw query
        st.markdown("#### Execute Query")
        query = st.text_area("SQL Query (SELECT only)", height=100)
        if st.button("Execute") and query:
            try:
                db = get_db()
                results = db.query(f"{query} LIMIT 100")
                if results:
                    df = pd.DataFrame(results)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("Query returned no results")
            except Exception as e:
                st.error(f"Query error: {e}")

with tab3:
    st.subheader("Data Indexing")

    st.markdown("""
    Index CSV data files into DuckDB for fast querying.
    - **Priority tables**: Smaller, frequently-used tables (~2-5 minutes)
    - **NSN Item Data**: Large files needed for item browsing by FSC (~5-10 minutes)
    - **Full indexing**: All tables including characteristics (~30-60 minutes)
    """)

    # Check current indexing status
    db = get_db()
    indexed_tables = db.get_indexed_tables()

    # Key tables status
    st.markdown("### Current Status")
    col1, col2, col3 = st.columns(3)

    with col1:
        priority_indexed = "P_CAGE" in indexed_tables and "V_H2_FSC" in indexed_tables
        if priority_indexed:
            st.success("✅ Priority Tables")
        else:
            st.warning("⚠️ Priority Tables")

    with col2:
        nsn_indexed = "FLISV" in indexed_tables or "P_FLIS_NSN" in indexed_tables
        if nsn_indexed:
            st.success("✅ NSN Item Data")
        else:
            st.error("❌ NSN Item Data (needed for item browsing)")

    with col3:
        full_indexed = "V_CHARACTERISTICS" in indexed_tables and "V_FLIS_MANAGEMENT" in indexed_tables
        if full_indexed:
            st.success("✅ Full Data")
        else:
            st.info("ℹ️ Full Data (optional)")

    st.markdown("---")

    # NSN Data Indexing - Most Important for Item Browsing
    st.markdown("### 📦 Index NSN Item Data")
    st.info("**Required for browsing items by FSC.** This indexes the FLISV file (~2.2 GB) which contains all NSN items and descriptions.")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Show file info
        flisv_path = DATA_FILES.get("large_files", {}).get("FLISV")
        if flisv_path and flisv_path.exists():
            size_gb = flisv_path.stat().st_size / (1024**3)
            st.write(f"**File:** FLISV.CSV ({size_gb:.2f} GB)")

            if "FLISV" in indexed_tables:
                info = db.get_table_info("FLISV")
                st.write(f"**Status:** ✅ Indexed ({info.get('row_count', 0):,} rows)")
            else:
                st.write("**Status:** ❌ Not indexed")
        else:
            st.warning("FLISV.CSV file not found")

    with col2:
        force_flisv = st.checkbox("Force re-index", key="force_flisv")

        if st.button("🚀 Index NSN Data", type="primary", disabled=not (flisv_path and flisv_path.exists())):
            progress_bar = st.progress(0, text="Starting indexing...")

            try:
                progress_bar.progress(10, text="Loading FLISV.CSV (~2.2 GB)...")

                success = db.index_csv_file("FLISV", flisv_path, force=force_flisv)

                progress_bar.progress(100, text="Complete!")

                if success:
                    info = db.get_table_info("FLISV")
                    st.success(f"✅ Successfully indexed FLISV: {info.get('row_count', 0):,} rows")
                    st.balloons()
                else:
                    st.error("❌ Failed to index FLISV")
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")

    # Priority Tables
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Quick Index (Priority Tables)")
        st.caption("Reference data: CAGE codes, FSC classifications, item names")
        force_priority = st.checkbox("Force re-index (priority)", key="force_priority")

        if st.button("Index Priority Tables", type="secondary"):
            with st.spinner("Indexing priority tables... This may take several minutes."):
                try:
                    loader = DataLoader()
                    result = loader.initialize_database(force=force_priority, priority_only=True)

                    if result["success"]:
                        st.success(f"✅ Successfully indexed {result['indexed']}/{result['total']} tables")
                    else:
                        st.warning(f"⚠️ Indexed {result['indexed']}/{result['total']} tables (some failed)")

                    # Show details
                    with st.expander("Indexing Details"):
                        for table, success in result["details"].items():
                            if success:
                                st.write(f"✅ {table}")
                            else:
                                st.write(f"❌ {table}")
                except Exception as e:
                    st.error(f"Indexing error: {e}")

    with col2:
        st.markdown("### Full Index (All Tables)")
        st.caption("Includes characteristics, parts, management data (~8 GB)")
        st.warning("⚠️ This may take 30-60 minutes!")

        force_full = st.checkbox("Force re-index (all)", key="force_full")

        if st.button("Index All Tables"):
            with st.spinner("Indexing all tables... This may take 30-60 minutes for large files."):
                try:
                    loader = DataLoader()
                    result = loader.initialize_database(force=force_full, priority_only=False)

                    if result["success"]:
                        st.success(f"✅ Successfully indexed {result['indexed']}/{result['total']} tables")
                    else:
                        st.warning(f"⚠️ Indexed {result['indexed']}/{result['total']} tables (some failed)")

                    # Show details
                    with st.expander("Indexing Details"):
                        for table, success in result["details"].items():
                            if success:
                                st.write(f"✅ {table}")
                            else:
                                st.write(f"❌ {table}")
                except Exception as e:
                    st.error(f"Indexing error: {e}")

    # Index specific table
    st.markdown("---")
    st.markdown("### Index Specific Table")

    col1, col2 = st.columns(2)

    with col1:
        # Build list of available tables
        available_tables = []
        for category, files in DATA_FILES.items():
            for name, path in files.items():
                if path.exists():
                    available_tables.append(name)

        selected_table = st.selectbox("Select table", available_tables)

    with col2:
        force_single = st.checkbox("Force re-index", key="force_single")

    if st.button("Index Selected Table"):
        all_files = {}
        for category, files in DATA_FILES.items():
            all_files.update(files)

        if selected_table in all_files:
            with st.spinner(f"Indexing {selected_table}..."):
                try:
                    db = get_db()
                    success = db.index_csv_file(
                        selected_table,
                        all_files[selected_table],
                        force=force_single
                    )
                    if success:
                        st.success(f"✅ Successfully indexed {selected_table}")
                    else:
                        st.error(f"❌ Failed to index {selected_table}")
                except Exception as e:
                    st.error(f"Error: {e}")

with tab4:
    st.subheader("REST API Information")

    st.markdown(f"""
    ### API Endpoints

    The PubLog API provides RESTful endpoints for external applications.

    **Base URL:** `http://localhost:{API_PORT}/api/v1`

    **Documentation:** `http://localhost:{API_PORT}/api/docs` (Swagger UI)

    ### Available Endpoints

    | Endpoint | Method | Description |
    |----------|--------|-------------|
    | `/health` | GET | Health check |
    | `/stats` | GET | Database statistics |
    | `/search?q=...` | GET | Unified search |
    | `/cage/<code>` | GET | CAGE lookup by code |
    | `/cage/search?q=...` | GET | CAGE search |
    | `/nsn/<niin>` | GET | NSN lookup by NIIN |
    | `/nsn/search?q=...` | GET | NSN search |
    | `/fsc` | GET | List all FSC codes |
    | `/fsc/<code>` | GET | FSC lookup |
    | `/fsg` | GET | List all FSG codes |
    | `/inc/<code>` | GET | Item name lookup |
    | `/inc/search?q=...` | GET | Item name search |
    """)

    st.markdown("---")
    st.markdown("### Running the API")

    st.code("""
# Start the API server (in a separate terminal)
cd publog_app
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# Or run both Streamlit and API together:
python run.py
    """, language="bash")

# Sidebar
with st.sidebar:
    st.markdown("### Quick Actions")

    if st.button("🔄 Refresh Status"):
        st.rerun()

    st.markdown("---")
    st.markdown("### System Info")
    st.write(f"**Database:** `{DB_PATH.name}`")
    st.write(f"**API Port:** {API_PORT}")

    st.markdown("---")
    st.markdown("### Help")
    st.markdown("""
    1. **First time setup**: Go to Indexing tab and click "Index Priority Tables"
    2. **For full data**: Click "Index All Tables" (takes longer)
    3. **To use API**: Start the API server separately
    """)
