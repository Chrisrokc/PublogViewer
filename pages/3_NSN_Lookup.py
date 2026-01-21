"""
NSN Lookup Page - Search and view National Stock Number information
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader import NSNService, FSCService
from database import get_db

st.set_page_config(page_title="NSN Lookup - PubLog", page_icon="📦", layout="wide")

st.title("📦 NSN / NIIN Lookup")
st.markdown("""
Search for National Stock Numbers (NSN) and National Item Identification Numbers (NIIN).
View item details, management data, and characteristics.
""")

@st.cache_resource
def get_services():
    return {
        "nsn": NSNService(),
        "fsc": FSCService()
    }

services = get_services()

# Search tabs
tab1, tab2, tab3 = st.tabs(["🔍 Search Items", "📊 Browse by FSC", "📋 Item Details"])

with tab1:
    st.subheader("Search NSN/NIIN")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        search_input = st.text_input(
            "Search",
            placeholder="Enter NIIN (9 digits) or item name...",
            key="nsn_search"
        )

    with col2:
        fsc_filter = st.text_input(
            "Filter by FSC",
            placeholder="4-digit FSC",
            max_chars=4
        )

    with col3:
        search_limit = st.number_input("Max results", min_value=10, max_value=500, value=50)

    if search_input:
        # Check if it looks like a NIIN (9 digits)
        clean_input = search_input.replace("-", "").replace(" ", "")
        if len(clean_input) == 9 and clean_input.isdigit():
            # Direct NIIN lookup
            result = services["nsn"].get_by_niin(clean_input)
            if result:
                st.success(f"Found NIIN: {clean_input}")

                # Display item information
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### Item Information")
                    st.write(f"**NIIN:** {result.get('NIIN', 'N/A')}")
                    st.write(f"**FSC:** {result.get('FSC', 'N/A')}")
                    st.write(f"**Item Name:** {result.get('ITEM_NAME', 'N/A')}")
                    if result.get('INC'):
                        st.write(f"**INC:** {result.get('INC', 'N/A')}")

                with col2:
                    st.markdown("### Additional Details")
                    # Display other available fields
                    excluded = ['NIIN', 'FSC', 'ITEM_NAME', 'INC']
                    for key, value in result.items():
                        if key not in excluded and value:
                            st.write(f"**{key}:** {value}")

                # Show raw data
                with st.expander("View Raw Data"):
                    st.json(result)

                # Get management data
                st.markdown("---")
                st.markdown("### Management Data")
                mgmt_data = services["nsn"].get_management_data(clean_input)
                if mgmt_data:
                    mgmt_df = pd.DataFrame(mgmt_data)
                    st.dataframe(mgmt_df, use_container_width=True)
                else:
                    st.info("No management data available for this NIIN")

                # Get characteristics
                st.markdown("### Characteristics")
                char_data = services["nsn"].get_characteristics(clean_input)
                if char_data:
                    char_df = pd.DataFrame(char_data)
                    st.dataframe(char_df, use_container_width=True)
                else:
                    st.info("No characteristics data available for this NIIN")

            else:
                st.warning(f"NIIN {clean_input} not found. Searching by text...")
                results = services["nsn"].search(search_input, fsc=fsc_filter if fsc_filter else None, limit=search_limit)
                if results:
                    st.info(f"Found {len(results)} items")
                    df = pd.DataFrame(results)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No results found")
        else:
            # Text search
            with st.spinner("Searching..."):
                results = services["nsn"].search(
                    search_input,
                    fsc=fsc_filter if fsc_filter else None,
                    limit=search_limit
                )

            if results:
                st.info(f"Found {len(results)} items")
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True)

                # Download option
                csv = df.to_csv(index=False)
                st.download_button(
                    "📥 Download Results (CSV)",
                    csv,
                    file_name=f"nsn_search_{search_input[:20]}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No results found")

with tab2:
    st.subheader("Browse by Federal Supply Class")

    # FSC selector
    col1, col2 = st.columns([1, 2])

    with col1:
        fsc_code = st.text_input(
            "Enter FSC Code",
            placeholder="4-digit FSC code",
            max_chars=4,
            key="fsc_browse"
        )

    with col2:
        # Quick FSC search
        fsc_search = st.text_input(
            "Or search FSC by name",
            placeholder="e.g., aircraft, ammunition, electronics..."
        )

    if fsc_search:
        fsc_results = services["fsc"].search_fsc(fsc_search)
        if fsc_results:
            st.info(f"Found {len(fsc_results)} matching FSC codes:")
            fsc_df = pd.DataFrame(fsc_results)
            st.dataframe(fsc_df, use_container_width=True)

    if fsc_code and len(fsc_code) == 4:
        # Get FSC info
        fsc_info = services["fsc"].get_fsc_by_code(fsc_code)
        if fsc_info:
            st.success(f"**FSC {fsc_code}:** {fsc_info.get('FSC_TITLE', 'Unknown')}")

        # Get items in this FSC
        with st.spinner("Loading items..."):
            browse_limit = st.slider("Number of items to display", 10, 200, 50)
            items = services["nsn"].get_by_fsc(fsc_code, limit=browse_limit)

        if items:
            st.info(f"Showing {len(items)} items in FSC {fsc_code}")
            df = pd.DataFrame(items)
            st.dataframe(df, use_container_width=True)

            # Download option
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Download Items (CSV)",
                csv,
                file_name=f"fsc_{fsc_code}_items.csv",
                mime="text/csv"
            )
        else:
            st.info(f"No items found in FSC {fsc_code}")

with tab3:
    st.subheader("Detailed Item Lookup")

    niin_input = st.text_input(
        "Enter NIIN for detailed view",
        placeholder="9-digit NIIN",
        max_chars=9,
        key="niin_detail"
    )

    if niin_input and len(niin_input) == 9:
        # Get all available data for this NIIN
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("#### Basic Info")
            result = services["nsn"].get_by_niin(niin_input)
            if result:
                for key, value in result.items():
                    if value:
                        st.write(f"**{key}:** {value}")
            else:
                st.warning("NIIN not found")

        with col2:
            st.markdown("#### Management Data")
            mgmt_data = services["nsn"].get_management_data(niin_input)
            if mgmt_data:
                for record in mgmt_data[:5]:  # Show first 5
                    with st.expander(f"Record {mgmt_data.index(record) + 1}"):
                        for key, value in record.items():
                            if value:
                                st.write(f"**{key}:** {value}")
            else:
                st.info("No management data")

        with col3:
            st.markdown("#### Characteristics")
            char_data = services["nsn"].get_characteristics(niin_input)
            if char_data:
                for record in char_data[:5]:  # Show first 5
                    with st.expander(f"Characteristic {char_data.index(record) + 1}"):
                        for key, value in record.items():
                            if value:
                                st.write(f"**{key}:** {value}")
            else:
                st.info("No characteristics data")

# Sidebar info
with st.sidebar:
    st.markdown("### About NSN/NIIN")
    st.markdown("""
    **NSN** (National Stock Number) is a 13-digit number used to identify items in the
    federal supply system.

    **Format:** `XXXX-XX-XXX-XXXX`
    - First 4 digits: FSC (Federal Supply Class)
    - Next 9 digits: NIIN (National Item Identification Number)

    **NIIN** uniquely identifies an item regardless of which country manages it.
    """)

    st.markdown("### Common FSC Groups")
    st.markdown("""
    - **10xx** - Weapons
    - **14xx** - Ammunition
    - **15xx** - Aircraft
    - **17xx** - Aircraft Components
    - **28xx** - Engines
    - **58xx** - Communication Equipment
    - **59xx** - Electrical Equipment
    """)
