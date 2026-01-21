"""
Configuration for PubLog Application
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = Path(__file__).parent.parent / "Data"
# Use temp directory for DuckDB to avoid filesystem permission issues
DB_PATH = Path("/tmp/publog_index.duckdb")

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000
API_PREFIX = "/api/v1"

# Data file mappings - organized by category
DATA_FILES = {
    # CAGE - Contractor/Company data
    "cage": {
        "P_CAGE": DATA_DIR / "CAGE" / "P_CAGE.CSV",
        "V_CAGE_ADDRESS": DATA_DIR / "CAGE" / "V_CAGE_ADDRESS.CSV",
        "V_CAGE_STATUS_AND_TYPE": DATA_DIR / "CAGE" / "V_CAGE_STATUS_AND_TYPE.CSV",
    },

    # H-Series - Classification and Reference Data
    "h_series": {
        "V_H2_FSC": DATA_DIR / "H-SERIES" / "V_H2_FSC.CSV",
        "V_H2_FSG": DATA_DIR / "H-SERIES" / "V_H2_FSG.CSV",
        "V_H3_AMMUNITION": DATA_DIR / "H-SERIES" / "V_H3_AMMUNITION.CSV",
        "V_H5_BUSINESS": DATA_DIR / "H-SERIES" / "V_H5_BUSINESS.CSV",
        "V_H5_CORPORATE": DATA_DIR / "H-SERIES" / "V_H5_CORPORATE.CSV",
        "V_H5_DOMESTIC": DATA_DIR / "H-SERIES" / "V_H5_DOMESTIC.CSV",
        "V_H5_FOREIGN": DATA_DIR / "H-SERIES" / "V_H5_FOREIGN.CSV",
        "V_H6_NAME_INC": DATA_DIR / "H-SERIES" / "V_H6_NAME_INC.CSV",
        "V_H6_MODIFIER": DATA_DIR / "H-SERIES" / "V_H6_MODIFIER.CSV",
        "V_H6_RELATED": DATA_DIR / "H-SERIES" / "V_H6_RELATED.CSV",
        "V_FSC_IMM": DATA_DIR / "H-SERIES" / "V_FSC_IMM.CSV",
    },

    # Identification - NSN/Item data
    "identification": {
        "P_FLIS_NSN": DATA_DIR / "IDENTIFICATION" / "P_FLIS_NSN.CSV",
        "V_COLLOQUIAL_NAME": DATA_DIR / "IDENTIFICATION" / "V_COLLOQUIAL_NAME.CSV",
        "V_FLIS_CANCELLED_NIIN": DATA_DIR / "IDENTIFICATION" / "V_FLIS_CANCELLED_NIIN.CSV",
        "V_FLIS_IDENTIFICATION": DATA_DIR / "IDENTIFICATION" / "V_FLIS_IDENTIFICATION.CSV",
        "V_FLIS_STANDARDIZATION": DATA_DIR / "IDENTIFICATION" / "V_FLIS_STANDARDIZATION.CSV",
    },

    # Management - Pricing, units, management data
    "management": {
        "V_FLIS_MANAGEMENT": DATA_DIR / "MANAGEMENT" / "V_FLIS_MANAGEMENT.CSV",
        "V_FLIS_MANAGEMENT_FUTURE": DATA_DIR / "MANAGEMENT" / "V_FLIS_MANAGEMENT_FUTURE.CSV",
        "V_FLIS_PHRASE": DATA_DIR / "MANAGEMENT" / "V_FLIS_PHRASE.CSV",
        "V_MGMT_AIR_FORCE": DATA_DIR / "MANAGEMENT" / "V_MGMT_AIR_FORCE.CSV",
        "V_MGMT_ARMY": DATA_DIR / "MANAGEMENT" / "V_MGMT_ARMY.CSV",
        "V_MGMT_COAST_GUARD": DATA_DIR / "MANAGEMENT" / "V_MGMT_COAST_GUARD.CSV",
        "V_MGMT_MARINE_CORPS": DATA_DIR / "MANAGEMENT" / "V_MGMT_MARINE_CORPS.CSV",
        "V_MGMT_NAVY": DATA_DIR / "MANAGEMENT" / "V_MGMT_NAVY.CSV",
        "V_SOCOM_MANAGEMENT": DATA_DIR / "MANAGEMENT" / "V_SOCOM_MANAGEMENT.CSV",
    },

    # Freight and Packaging
    "freight_packaging": {
        "V_FREIGHT": DATA_DIR / "FREIGHT_PACKAGING" / "V_FREIGHT.CSV",
        "V_FLIS_PACKAGING_1": DATA_DIR / "FREIGHT_PACKAGING" / "V_FLIS_PACKAGING_1.CSV",
        "V_FLIS_PACKAGING_2": DATA_DIR / "FREIGHT_PACKAGING" / "V_FLIS_PACKAGING_2.CSV",
        "V_FLIS_PACKAGING_3": DATA_DIR / "FREIGHT_PACKAGING" / "V_FLIS_PACKAGING_3.CSV",
    },

    # History
    "history": {
        "V_ITEM_IDENTIFICATION_HISTORY": DATA_DIR / "HISTORY" / "V_ITEM_IDENTIFICATION_HISTORY.CSV",
        "V_MANAGEMENT_HISTORY": DATA_DIR / "HISTORY" / "V_MANAGEMENT_HISTORY.CSV",
        "V_REFERENCE_NUMBER_HISTORY": DATA_DIR / "HISTORY" / "V_REFERENCE_NUMBER_HISTORY.CSV",
    },

    # MRD - Master Reference Data (Requirement Statement codes, Reply Tables, etc.)
    "mrd": {
        "MRD0107": DATA_DIR / "MRD" / "MRD0107.CSV",  # MRC Requirement Statements
        "MRD0300": DATA_DIR / "MRD" / "MRD0300.CSV",  # Reply Table Decoded Values
        "MRD0500": DATA_DIR / "MRD" / "MRD0500.CSV",  # INC/FIIG/MRC Mapping
        "MRD06P1": DATA_DIR / "MRD" / "MRD06P1.CSV",  # FIIG/INC/MRC Reply Table Decode
        "MRD06P2": DATA_DIR / "MRD" / "MRD06P2.CSV",  # Reply Table Decode Details
    },

    # Large standalone files
    "large_files": {
        "FLISV": DATA_DIR / "FLISV.CSV",
        "V_CHARACTERISTICS": DATA_DIR / "V_CHARACTERISTICS-2.CSV",
        "V_FLIS_PART": DATA_DIR / "V_FLIS_PART-2.CSV",
        "V_MOE_RULE": DATA_DIR / "V_MOE_RULE-2.CSV",
    },
}

# Tables to prioritize for indexing (smaller, frequently used)
PRIORITY_TABLES = [
    "P_CAGE",
    "V_H2_FSC",
    "V_H2_FSG",
    "V_H6_NAME_INC",
    "V_H6_MODIFIER",
    "V_FSC_IMM",
    "V_FLIS_CANCELLED_NIIN",
    "V_COLLOQUIAL_NAME",
    "V_FLIS_STANDARDIZATION",
    "V_H3_AMMUNITION",
    "V_H5_BUSINESS",
    "V_H5_CORPORATE",
    "V_H5_DOMESTIC",
    "V_H5_FOREIGN",
    "V_H6_RELATED",
    "V_FREIGHT",
    "V_FLIS_PACKAGING_1",
    "V_FLIS_PACKAGING_2",
    "V_FLIS_PACKAGING_3",
    "V_FLIS_PHRASE",
    "V_MGMT_AIR_FORCE",
    "V_MGMT_ARMY",
    "V_MGMT_COAST_GUARD",
    "V_MGMT_MARINE_CORPS",
    "V_MGMT_NAVY",
    "V_SOCOM_MANAGEMENT",
    "V_FLIS_MANAGEMENT_FUTURE",
]

# Large tables - index with specific columns only
LARGE_TABLES = [
    "FLISV",
    "V_CHARACTERISTICS",
    "V_FLIS_PART",
    "V_MOE_RULE",
    "V_FLIS_MANAGEMENT",
    "P_FLIS_NSN",
    "V_FLIS_IDENTIFICATION",
]

# Search configuration
MAX_SEARCH_RESULTS = 1000
DEFAULT_PAGE_SIZE = 50
