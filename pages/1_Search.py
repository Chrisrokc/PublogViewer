"""
Unified Search Page - Search across all PubLog data types
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader import UnifiedSearchService, CAGEService, FSCService, NSNService, ItemNameService
from database import get_db

st.set_page_config(page_title="Search - PubLog", page_icon="🔍", layout="wide")

st.title("🔍 Unified Search")
st.markdown("Search across all PubLog data: CAGE codes, NSN items, FSC classifications, and item names.")

# Initialize services
@st.cache_resource
def get_services():
    return {
        "unified": UnifiedSearchService(),
        "cage": CAGEService(),
        "fsc": FSCService(),
        "nsn": NSNService(),
        "item_name": ItemNameService()
    }

services = get_services()

# Search interface
col1, col2 = st.columns([3, 1])

with col1:
    search_query = st.text_input(
        "Enter search term",
        placeholder="Enter CAGE code, NSN/NIIN, company name, item name, or FSC...",
        help="Search across all data types"
    )

with col2:
    search_type = st.selectbox(
        "Search type",
        ["All", "CAGE Only", "NSN Only", "FSC Only", "Item Names Only"]
    )

# Advanced filters
with st.expander("Advanced Filters"):
    col1, col2, col3 = st.columns(3)

    with col1:
        fsc_filter = st.text_input("Filter by FSC (4 digits)", max_chars=4)

    with col2:
        state_filter = st.text_input("Filter by State", max_chars=2)

    with col3:
        max_results = st.slider("Max results per category", 10, 100, 25)

# Perform search
if search_query:
    with st.spinner("Searching..."):
        try:
            if search_type == "All":
                results = services["unified"].search_all(search_query, limit=max_results)

                # Display results in tabs
                tabs = st.tabs(["📋 All Results", "🏢 CAGE", "📦 NSN", "📊 FSC", "📝 Item Names"])

                with tabs[0]:
                    total = sum(len(v) for v in results.values())
                    st.metric("Total Results", total)

                    # Summary of results
                    summary_cols = st.columns(4)
                    with summary_cols[0]:
                        st.metric("CAGE Records", len(results.get("cage", [])))
                    with summary_cols[1]:
                        st.metric("NSN Items", len(results.get("nsn", [])))
                    with summary_cols[2]:
                        st.metric("FSC Codes", len(results.get("fsc", [])))
                    with summary_cols[3]:
                        st.metric("Item Names", len(results.get("item_names", [])))

                with tabs[1]:
                    if results.get("cage"):
                        df = pd.DataFrame(results["cage"])
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No CAGE records found")

                with tabs[2]:
                    if results.get("nsn"):
                        df = pd.DataFrame(results["nsn"])
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No NSN items found")

                with tabs[3]:
                    if results.get("fsc"):
                        df = pd.DataFrame(results["fsc"])
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No FSC codes found")

                with tabs[4]:
                    if results.get("item_names"):
                        df = pd.DataFrame(results["item_names"])
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No item names found")

            elif search_type == "CAGE Only":
                results = services["cage"].search(search_query, limit=max_results)
                if state_filter:
                    results = [r for r in results if r.get("STATE_PROVINCE", "").upper() == state_filter.upper()]

                st.subheader(f"CAGE Results ({len(results)})")
                if results:
                    df = pd.DataFrame(results)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No CAGE records found")

            elif search_type == "NSN Only":
                results = services["nsn"].search(
                    search_query,
                    fsc=fsc_filter if fsc_filter else None,
                    limit=max_results
                )

                st.subheader(f"NSN Results ({len(results)})")
                if results:
                    df = pd.DataFrame(results)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No NSN items found")

            elif search_type == "FSC Only":
                results = services["fsc"].search_fsc(search_query)[:max_results]

                st.subheader(f"FSC Results ({len(results)})")
                if results:
                    df = pd.DataFrame(results)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No FSC codes found")

            elif search_type == "Item Names Only":
                results = services["item_name"].search(search_query, limit=max_results)

                st.subheader(f"Item Name Results ({len(results)})")
                if results:
                    df = pd.DataFrame(results)
                    # Show definition in expandable sections
                    for idx, row in enumerate(results[:10]):
                        with st.expander(f"{row.get('INC', 'N/A')} - {row.get('FIIG_TITLE', 'Unknown')}"):
                            st.write(f"**Definition:** {row.get('DEFINITION', 'N/A')}")
                            st.write(f"**Status:** {row.get('INC_STATUS', 'N/A')}")
                            st.write(f"**FIIG:** {row.get('FIIG', 'N/A')}")
                else:
                    st.info("No item names found")

        except Exception as e:
            st.error(f"Search error: {str(e)}")

else:
    st.info("Enter a search term above to begin searching the PubLog database.")

    # Show quick stats
    st.markdown("---")
    st.subheader("Quick Tips")
    st.markdown("""
    - **CAGE Code**: Enter a 5-character code (e.g., `00000`)
    - **NIIN**: Enter a 9-digit number (e.g., `001234567`)
    - **Company Name**: Enter partial or full company name
    - **FSC Code**: Enter a 4-digit Federal Supply Class code
    - **Item Name**: Search by item description or title
    """)
