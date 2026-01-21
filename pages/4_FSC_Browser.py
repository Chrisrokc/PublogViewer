"""
FSC Browser Page - Browse Federal Supply Classifications
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader import FSCService, ItemNameService
from database import get_db

st.set_page_config(page_title="FSC Browser - PubLog", page_icon="📊", layout="wide")

st.title("📊 Federal Supply Classification Browser")
st.markdown("""
Browse the Federal Supply Classification (FSC) system.
FSC organizes supplies into groups and classes for standardized procurement.
""")

@st.cache_resource
def get_services():
    return {
        "fsc": FSCService(),
        "item_name": ItemNameService()
    }

services = get_services()

# Tabs
tab1, tab2, tab3 = st.tabs(["📁 Browse Groups & Classes", "🔍 Search FSC", "📝 Item Names (INC)"])

with tab1:
    st.subheader("Federal Supply Groups (FSG)")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### Supply Groups")
        try:
            fsg_list = services["fsc"].get_all_fsg()
            if fsg_list:
                # Create selection
                fsg_options = {f"{r['FSG']} - {r.get('FSG_TITLE', 'Unknown')[:40]}": r['FSG'] for r in fsg_list}
                selected_fsg_label = st.selectbox(
                    "Select a Federal Supply Group",
                    options=list(fsg_options.keys())
                )
                selected_fsg = fsg_options[selected_fsg_label] if selected_fsg_label else None

                st.info(f"Total FSGs: {len(fsg_list)}")
            else:
                st.warning("FSG data not available. Database may need indexing.")
                selected_fsg = None
        except Exception as e:
            st.error(f"Error loading FSG data: {e}")
            selected_fsg = None

    with col2:
        if selected_fsg:
            st.markdown(f"### Federal Supply Classes in FSG {selected_fsg}")

            fsc_in_fsg = services["fsc"].get_fsc_by_fsg(selected_fsg)
            if fsc_in_fsg:
                st.info(f"Found {len(fsc_in_fsg)} classes in this group")

                # Display as dataframe
                fsc_df = pd.DataFrame(fsc_in_fsg)
                st.dataframe(fsc_df, use_container_width=True)

                # Download option
                csv = fsc_df.to_csv(index=False)
                st.download_button(
                    "📥 Download FSC List (CSV)",
                    csv,
                    file_name=f"fsc_group_{selected_fsg}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No FSC codes found in this group")

    # Show all FSG data
    st.markdown("---")
    st.markdown("### All Federal Supply Groups")
    if st.button("Load All FSG Data"):
        try:
            all_fsg = services["fsc"].get_all_fsg()
            if all_fsg:
                fsg_df = pd.DataFrame(all_fsg)
                st.dataframe(fsg_df, use_container_width=True)

                csv = fsg_df.to_csv(index=False)
                st.download_button(
                    "📥 Download All FSG (CSV)",
                    csv,
                    file_name="all_fsg.csv",
                    mime="text/csv"
                )
        except Exception as e:
            st.error(f"Error: {e}")

with tab2:
    st.subheader("Search Federal Supply Classes")

    search_query = st.text_input(
        "Search FSC by code or name",
        placeholder="e.g., 5820 or 'radio' or 'ammunition'..."
    )

    if search_query:
        with st.spinner("Searching..."):
            results = services["fsc"].search_fsc(search_query)

        if results:
            st.success(f"Found {len(results)} matching FSC codes")

            # Display results
            df = pd.DataFrame(results)
            st.dataframe(df, use_container_width=True)

            # Show details for selected FSC
            if len(results) <= 20:
                st.markdown("### FSC Details")
                for fsc in results:
                    with st.expander(f"FSC {fsc['FSC']} - {fsc.get('FSC_TITLE', 'Unknown')}"):
                        for key, value in fsc.items():
                            if value:
                                st.write(f"**{key}:** {value}")
        else:
            st.info("No matching FSC codes found")

    # Direct FSC lookup
    st.markdown("---")
    st.markdown("### Direct FSC Lookup")

    fsc_code = st.text_input(
        "Enter exact FSC code",
        placeholder="4-digit code (e.g., 5820)",
        max_chars=4
    )

    if fsc_code and len(fsc_code) == 4:
        fsc_info = services["fsc"].get_fsc_by_code(fsc_code)
        if fsc_info:
            st.success(f"Found FSC {fsc_code}")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**FSC Code:** {fsc_info.get('FSC', 'N/A')}")
                st.write(f"**Name:** {fsc_info.get('FSC_TITLE', 'N/A')}")
            with col2:
                for key, value in fsc_info.items():
                    if key not in ['FSC', 'FSC_TITLE'] and value:
                        st.write(f"**{key}:** {value}")
        else:
            st.warning(f"FSC {fsc_code} not found")

with tab3:
    st.subheader("Item Name Codes (INC)")
    st.markdown("Search for Item Name Codes that define standardized item nomenclature.")

    inc_search = st.text_input(
        "Search Item Names",
        placeholder="e.g., 'capacitor' or 'valve' or 'tube'..."
    )

    if inc_search:
        with st.spinner("Searching item names..."):
            results = services["item_name"].search(inc_search, limit=50)

        if results:
            st.success(f"Found {len(results)} item names")

            # Display as expandable cards
            for item in results:
                title = item.get('FIIG_TITLE', 'Unknown')
                inc = item.get('INC', 'N/A')

                with st.expander(f"**{inc}** - {title}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**INC:** {inc}")
                        st.write(f"**Title:** {title}")
                        st.write(f"**Status:** {item.get('INC_STATUS', 'N/A')}")
                        st.write(f"**FIIG:** {item.get('FIIG', 'N/A')}")

                    with col2:
                        st.write(f"**Concept No:** {item.get('CONCEPT_NO', 'N/A')}")
                        st.write(f"**Type Code:** {item.get('TYPE_CODE', 'N/A')}")
                        st.write(f"**Date Est/Canc:** {item.get('DT_ESTB_CANC', 'N/A')}")

                    st.markdown("**Definition:**")
                    st.write(item.get('DEFINITION', 'No definition available'))
        else:
            st.info("No matching item names found")

    # Direct INC lookup
    st.markdown("---")
    st.markdown("### Direct INC Lookup")

    inc_code = st.text_input(
        "Enter exact INC code",
        placeholder="5-digit code",
        max_chars=5
    )

    if inc_code and len(inc_code) == 5:
        inc_info = services["item_name"].get_by_inc(inc_code)
        if inc_info:
            st.success(f"Found INC {inc_code}")
            st.markdown(f"### {inc_info.get('FIIG_TITLE', 'Unknown')}")

            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**INC:** {inc_info.get('INC', 'N/A')}")
                st.write(f"**Status:** {inc_info.get('INC_STATUS', 'N/A')}")
                st.write(f"**FIIG:** {inc_info.get('FIIG', 'N/A')}")
            with col2:
                st.write(f"**Concept No:** {inc_info.get('CONCEPT_NO', 'N/A')}")
                st.write(f"**Type Code:** {inc_info.get('TYPE_CODE', 'N/A')}")
                st.write(f"**Condition Code:** {inc_info.get('COND_CODE', 'N/A')}")

            st.markdown("**Definition:**")
            st.info(inc_info.get('DEFINITION', 'No definition available'))
        else:
            st.warning(f"INC {inc_code} not found")

# Sidebar info
with st.sidebar:
    st.markdown("### About FSC")
    st.markdown("""
    The **Federal Supply Classification (FSC)** system organizes items into:

    - **FSG** (Federal Supply Group): 2-digit code grouping related classes
    - **FSC** (Federal Supply Class): 4-digit code within a group

    **Examples:**
    - FSG 58: Communication, Detection, and Coherent Radiation Equipment
    - FSC 5820: Radio and Television Communication Equipment
    - FSC 5821: Radio and TV Transmitting Equipment
    """)

    st.markdown("### About INC")
    st.markdown("""
    **Item Name Codes (INC)** provide standardized nomenclature for items:

    - 5-digit code
    - Includes definition and classification
    - Used in FIIG (Federal Item Identification Guide)
    """)
