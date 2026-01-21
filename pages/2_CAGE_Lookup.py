"""
CAGE Lookup Page - Search and view contractor/company information
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader import CAGEService
from database import get_db

st.set_page_config(page_title="CAGE Lookup - PubLog", page_icon="🏢", layout="wide")

st.title("🏢 CAGE Code Lookup")
st.markdown("""
Search for Commercial and Government Entity (CAGE) codes.
CAGE codes identify contractors, manufacturers, and government activities.
""")

@st.cache_resource
def get_cage_service():
    return CAGEService()

cage_service = get_cage_service()

# Search tabs
tab1, tab2, tab3 = st.tabs(["🔍 Search", "📍 By Location", "📊 Statistics"])

with tab1:
    st.subheader("Search CAGE Records")

    col1, col2 = st.columns([2, 1])

    with col1:
        search_input = st.text_input(
            "Search",
            placeholder="Enter CAGE code, company name, or city...",
            key="cage_search"
        )

    with col2:
        search_limit = st.number_input("Max results", min_value=10, max_value=500, value=50)

    if search_input:
        # Check if it looks like a CAGE code (5 alphanumeric chars)
        if len(search_input) == 5 and search_input.isalnum():
            # Direct lookup
            result = cage_service.get_by_code(search_input)
            if result:
                st.success(f"Found CAGE code: {search_input}")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### Company Information")
                    st.write(f"**Company:** {result.get('COMPANY', 'N/A')}")
                    st.write(f"**CAGE Code:** {result.get('CAGE_CODE', 'N/A')}")
                    st.write(f"**Status:** {result.get('CAGE_STATUS', 'N/A')}")
                    st.write(f"**Type:** {result.get('TYPE', 'N/A')}")
                    st.write(f"**CAO:** {result.get('CAO', 'N/A')}")

                with col2:
                    st.markdown("### Location")
                    st.write(f"**City:** {result.get('CITY', 'N/A')}")
                    st.write(f"**State/Province:** {result.get('STATE_PROVINCE', 'N/A')}")
                    st.write(f"**ZIP/Postal:** {result.get('ZIP_POSTAL_ZONE', 'N/A')}")
                    st.write(f"**Country:** {result.get('COUNTRY', 'N/A')}")

                # Show raw data
                with st.expander("View Raw Data"):
                    st.json(result)
            else:
                st.warning(f"CAGE code {search_input} not found. Searching by text...")
                results = cage_service.search(search_input, limit=search_limit)
                if results:
                    st.info(f"Found {len(results)} results")
                    df = pd.DataFrame(results)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No results found")
        else:
            # Text search
            with st.spinner("Searching..."):
                results = cage_service.search(search_input, limit=search_limit)

            if results:
                st.info(f"Found {len(results)} results")
                df = pd.DataFrame(results)

                # Add clickable CAGE codes
                st.dataframe(df, use_container_width=True)

                # Download option
                csv = df.to_csv(index=False)
                st.download_button(
                    "📥 Download Results (CSV)",
                    csv,
                    file_name=f"cage_search_{search_input}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No results found")

with tab2:
    st.subheader("Search by Location")

    col1, col2, col3 = st.columns(3)

    with col1:
        state_input = st.text_input(
            "State/Province Code",
            placeholder="e.g., CA, TX, NY",
            max_chars=2
        )

    with col2:
        city_input = st.text_input(
            "City",
            placeholder="e.g., Los Angeles"
        )

    with col3:
        country_input = st.text_input(
            "Country",
            placeholder="e.g., UNITED STATES",
            value=""
        )

    location_limit = st.slider("Max results", 10, 200, 50, key="loc_limit")

    if st.button("Search by Location", type="primary"):
        if not any([state_input, city_input, country_input]):
            st.warning("Please enter at least one location criteria")
        else:
            with st.spinner("Searching..."):
                results = cage_service.search_by_location(
                    state=state_input if state_input else None,
                    city=city_input if city_input else None,
                    country=country_input if country_input else None,
                    limit=location_limit
                )

            if results:
                st.success(f"Found {len(results)} contractors")
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True)

                # Download option
                csv = df.to_csv(index=False)
                st.download_button(
                    "📥 Download Results (CSV)",
                    csv,
                    file_name=f"cage_location_search.csv",
                    mime="text/csv"
                )
            else:
                st.info("No results found for the specified location")

with tab3:
    st.subheader("CAGE Statistics")

    if st.button("Load Statistics", type="primary"):
        with st.spinner("Loading statistics..."):
            try:
                stats = cage_service.get_stats()

                if stats:
                    col1, col2 = st.columns(2)

                    with col1:
                        st.metric("Total CAGE Records", f"{stats.get('total_records', 0):,}")

                    st.markdown("### Records by Status")
                    if stats.get("by_status"):
                        status_df = pd.DataFrame(stats["by_status"])
                        st.bar_chart(status_df.set_index("CAGE_STATUS"))
                        st.dataframe(status_df, use_container_width=True)

                    st.markdown("### Top Countries")
                    if stats.get("top_countries"):
                        country_df = pd.DataFrame(stats["top_countries"])
                        st.bar_chart(country_df.set_index("COUNTRY"))
                        st.dataframe(country_df, use_container_width=True)
                else:
                    st.warning("Could not load statistics. Database may not be indexed.")
            except Exception as e:
                st.error(f"Error loading statistics: {str(e)}")

# Sidebar info
with st.sidebar:
    st.markdown("### About CAGE Codes")
    st.markdown("""
    **CAGE Code** (Commercial and Government Entity Code) is a 5-character identifier
    assigned to suppliers to various government agencies.

    **Status Codes:**
    - **A** - Active
    - **H** - Historical
    - **D** - Deleted

    **Type Codes:**
    - **A** - Activity (Government)
    - **C** - Commercial
    """)
