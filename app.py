"""
PubLog Viewer - Main Streamlit Application
Federal Logistics Information Service (FLIS) Data Explorer
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Ensure imports work
sys.path.insert(0, str(Path(__file__).parent))

from database import get_db
from data_loader import DataLoader
from config import DB_PATH, API_PORT

# Page configuration
st.set_page_config(
    page_title="PubLog Viewer",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "# PubLog Viewer\nFederal Logistics Information Service (FLIS) Data Explorer"
    }
)

# Custom CSS
st.markdown("""
<style>
    /* Add PubLog Viewer title above navigation */
    [data-testid="stSidebarNav"]::before {
        content: "📦 PubLog Viewer";
        display: block;
        font-size: 1.4rem;
        font-weight: 600;
        padding: 15px 20px 15px 20px;
        color: #1f4e79;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 10px;
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f4e79;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-top: 0;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown('<p class="main-header">📦 PubLog Viewer</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Federal Logistics Information Service (FLIS) Data Explorer</p>', unsafe_allow_html=True)

st.markdown("---")

# Check database status
@st.cache_data(ttl=60)
def get_database_status():
    try:
        db = get_db()
        stats = db.get_database_stats()
        return {
            "connected": True,
            "tables": stats.get("total_tables", 0),
            "rows": stats.get("total_rows", 0),
            "size_mb": stats.get("db_file_size_mb", 0)
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e)
        }

status = get_database_status()

# Status display
if status["connected"] and status["tables"] > 0:
    # Database is ready
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📊 Tables Indexed", status["tables"])

    with col2:
        st.metric("📝 Total Records", f"{status['rows']:,}")

    with col3:
        st.metric("💾 Database Size", f"{status['size_mb']:.1f} MB")

    with col4:
        st.metric("🌐 API Port", API_PORT)

    st.success("✅ Database is ready! Use the sidebar to navigate to different features.")

else:
    # Database needs initialization
    st.warning("⚠️ Database not initialized or empty. Please run the indexing process first.")

    st.markdown("""
    ### Getting Started

    1. **Navigate to the Admin page** using the sidebar
    2. **Click "Index Priority Tables"** to index frequently-used data (~5-10 minutes)
    3. **Optionally, click "Index All Tables"** for complete data access (~30-60 minutes)

    Once indexing is complete, you'll be able to:
    - Search across all PubLog data
    - Look up CAGE codes (contractor information)
    - Browse NSN/NIIN items
    - Explore Federal Supply Classifications
    - Use the REST API for external applications
    """)

    if st.button("🚀 Quick Start: Index Priority Tables", type="primary"):
        with st.spinner("Indexing priority tables... This may take several minutes."):
            try:
                loader = DataLoader()
                result = loader.initialize_database(force=False, priority_only=True)

                if result["success"]:
                    st.success(f"✅ Indexed {result['indexed']} tables successfully!")
                    st.rerun()
                else:
                    st.warning(f"Indexed {result['indexed']}/{result['total']} tables. Some may have failed.")
                    st.rerun()
            except Exception as e:
                st.error(f"Indexing error: {e}")

st.markdown("---")

# Feature overview
st.markdown("### 🗂️ Features")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    #### 🔍 Unified Search
    Search across all data types simultaneously:
    - CAGE codes and company names
    - NSN/NIIN and item descriptions
    - FSC classifications
    - Item name definitions

    #### 🏢 CAGE Lookup
    Find contractor and manufacturer information:
    - Search by CAGE code
    - Search by company name
    - Filter by location
    - View company details
    """)

with col2:
    st.markdown("""
    #### 📦 NSN/NIIN Lookup
    Explore National Stock Numbers:
    - Direct NIIN lookup
    - Search by item name
    - Browse by FSC category
    - View management data & characteristics

    #### 📊 FSC Browser
    Navigate Federal Supply Classifications:
    - Browse FSG (Supply Groups)
    - Browse FSC (Supply Classes)
    - Search classifications
    - Item Name Code (INC) lookup
    """)

st.markdown("---")

# API Information
st.markdown("### 🌐 REST API")

st.markdown(f"""
The PubLog API provides programmatic access to all data for external applications.

**Endpoints available at:** `http://localhost:{API_PORT}/api/v1/`

| Endpoint | Description |
|----------|-------------|
| `GET /search?q=...` | Unified search across all data |
| `GET /cage/{{code}}` | CAGE lookup by code |
| `GET /cage/search?q=...` | CAGE search |
| `GET /nsn/{{niin}}` | NSN lookup by NIIN |
| `GET /nsn/search?q=...` | NSN search |
| `GET /fsc` | List all FSC codes |
| `GET /fsg` | List all FSG codes |
| `GET /health` | API health check |

**API Documentation:** Access Swagger UI at `http://localhost:{API_PORT}/api/docs`
""")

# Quick example
with st.expander("📝 API Usage Example"):
    st.code("""
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Unified search
response = requests.get(f"{BASE_URL}/search", params={"q": "capacitor"})
results = response.json()
print(f"Found {results['total_results']} results")

# CAGE lookup
cage = requests.get(f"{BASE_URL}/cage/00000").json()
print(f"Company: {cage['COMPANY']}")

# NSN search
nsn_results = requests.get(f"{BASE_URL}/nsn/search", params={"q": "radio", "fsc": "5820"}).json()
print(f"Found {nsn_results['count']} NSN items")

# FSC listing
fsc_list = requests.get(f"{BASE_URL}/fsc").json()
print(f"Total FSC codes: {fsc_list['count']}")
    """, language="python")

# Sidebar
with st.sidebar:
    st.markdown("## Navigation")
    st.markdown("""
    - **🔍 Search** - Unified search
    - **🏢 CAGE** - Contractor lookup
    - **📦 NSN** - Item lookup
    - **📊 FSC** - Classification browser
    - **⚙️ Admin** - Database management
    """)

    st.markdown("---")

    st.markdown("## About PubLog")
    st.markdown("""
    **PubLog** (Public Logistics) data from the
    Defense Logistics Agency (DLA) provides
    information about:

    - Federal supply items
    - Contractors & manufacturers
    - Item classifications
    - Technical characteristics

    This data is publicly available from the
    DLA FLIS Electronic Reading Room.
    """)

    st.markdown("---")

    st.markdown("## Quick Links")
    st.markdown(f"""
    - [API Docs](http://localhost:{API_PORT}/api/docs)
    - [DLA FLIS](https://www.dla.mil/Logistics-Operations/Services/FLIS/)
    """)
