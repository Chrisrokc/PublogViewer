# PubLog Viewer

A Python Streamlit application for querying and exploring Federal Logistics Information Service (FLIS) PubLog data. Includes both a web-based UI for interactive exploration and a REST API for programmatic access.

## Features

- **Interactive Web UI** - Browse and search FLIS data through an intuitive Streamlit interface
- **NSN/NIIN Lookup** - Search National Stock Numbers by NIIN, item name, or FSC
- **CAGE Code Lookup** - Look up contractor and company information
- **FSC Browser** - Browse items by Federal Supply Class
- **REST API** - FastAPI-powered endpoints for external application integration
- **Fast Queries** - Uses DuckDB for high-performance analytical queries on large datasets
- **Admin Dashboard** - Monitor database status, manage indexing, and view system statistics

## Prerequisites

- Python 3.9 or higher
- ~10GB disk space for the DuckDB index (varies based on indexed tables)
- PubLog data files (see Data Setup below)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/publog-viewer.git
cd publog-viewer
```

2. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install streamlit pandas duckdb fastapi uvicorn
```

## Data Setup

This application requires PubLog data files from the Defense Logistics Agency (DLA). The data files are not included in this repository due to their size.

### Downloading PubLog Data

1. Visit the DLA Public FLIS website: https://www.dla.mil/Working-With-DLA/Applications/Public-FLIS/

2. Navigate to the **PubLog** section and download the data files. You will need to request access or download the publicly available FOIA version.

3. Alternative: Visit the FLIS Data page at https://www.logisticsinformationservice.dla.mil/

### Required Directory Structure

Create a `Data` directory in the project root with the following structure:

```
publog_app/
├── Data/
│   ├── CAGE/
│   │   ├── P_CAGE.CSV
│   │   ├── V_CAGE_ADDRESS.CSV
│   │   └── V_CAGE_STATUS_AND_TYPE.CSV
│   ├── H-SERIES/
│   │   ├── V_H2_FSC.CSV
│   │   ├── V_H2_FSG.CSV
│   │   ├── V_H6_NAME_INC.CSV
│   │   └── ... (other H-series files)
│   ├── IDENTIFICATION/
│   │   ├── P_FLIS_NSN.CSV          # Primary NSN data (~1GB)
│   │   ├── V_FLIS_IDENTIFICATION.CSV
│   │   └── ... (other identification files)
│   ├── MANAGEMENT/
│   │   ├── V_FLIS_MANAGEMENT.CSV
│   │   └── ... (other management files)
│   ├── FREIGHT_PACKAGING/
│   │   └── ... (freight and packaging files)
│   ├── HISTORY/
│   │   └── ... (history files)
│   ├── MRD/
│   │   ├── MRD0107.CSV
│   │   ├── MRD0300.CSV
│   │   ├── MRD0500.CSV
│   │   ├── MRD06P1.CSV
│   │   └── MRD06P2.CSV
│   ├── FLISV.CSV                   # Large characteristics file (~2.2GB)
│   ├── V_CHARACTERISTICS-2.CSV     # Optional large file
│   ├── V_FLIS_PART-2.CSV          # Optional large file
│   └── V_MOE_RULE-2.CSV           # Optional large file
```

### Key Data Files

| File | Description | Size | Priority |
|------|-------------|------|----------|
| P_FLIS_NSN.CSV | Primary NSN data with item names | ~1GB | Required for NSN search |
| V_H2_FSC.CSV | Federal Supply Class codes | Small | Required for FSC lookup |
| V_H2_FSG.CSV | Federal Supply Group codes | Small | Required for FSG lookup |
| P_CAGE.CSV | Contractor/CAGE codes | ~400MB | Required for CAGE lookup |
| V_H6_NAME_INC.CSV | Item Name Codes | Small | Required for INC lookup |
| FLISV.CSV | FLIS characteristics data | ~2.2GB | Optional |

## Running the Application

### Option 1: Streamlit UI Only

```bash
cd publog_app
python3 -m streamlit run app.py --server.port 8501
```

Access the UI at: http://localhost:8501

### Option 2: Both UI and REST API

```bash
cd publog_app
python run.py
```

This starts:
- Streamlit UI at http://localhost:8501
- REST API at http://localhost:8000

### Option 3: API Only

```bash
cd publog_app
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

API documentation available at: http://localhost:8000/api/docs

## First-Time Setup

1. Start the application
2. Navigate to the **Admin** page
3. Click **"Index Priority Tables"** to index the smaller, frequently-used tables
4. For full NSN search capability, click **"Index NSN Data"** to index P_FLIS_NSN (this may take several minutes)
5. Optionally index additional large tables as needed

The DuckDB index is stored at `/tmp/publog_index.duckdb` by default. You can change this in `config.py`.

## REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/stats` | GET | Database statistics |
| `/api/v1/search?q=...` | GET | Unified search |
| `/api/v1/cage/{code}` | GET | CAGE lookup by code |
| `/api/v1/cage/search?q=...` | GET | CAGE search |
| `/api/v1/nsn/{niin}` | GET | NSN lookup by NIIN |
| `/api/v1/nsn/search?q=...` | GET | NSN search |
| `/api/v1/fsc` | GET | List all FSC codes |
| `/api/v1/fsc/{code}` | GET | FSC lookup |
| `/api/v1/fsg` | GET | List all FSG codes |
| `/api/v1/inc/{code}` | GET | Item name lookup |
| `/api/v1/inc/search?q=...` | GET | Item name search |

### Example API Usage

```bash
# Search for items containing "RADOME"
curl "http://localhost:8000/api/v1/nsn/search?q=RADOME&limit=10"

# Look up a specific NIIN
curl "http://localhost:8000/api/v1/nsn/011519535"

# Look up a CAGE code
curl "http://localhost:8000/api/v1/cage/80205"

# Get all items in FSC 1560
curl "http://localhost:8000/api/v1/fsc/1560/items?limit=50"
```

## Project Structure

```
publog_app/
├── app.py              # Main Streamlit application
├── api.py              # FastAPI REST API
├── config.py           # Configuration and data file mappings
├── database.py         # DuckDB database management
├── data_loader.py      # Data services (CAGE, FSC, NSN, INC)
├── run.py              # Combined runner script
├── pages/
│   ├── 1_Search.py     # Unified search page
│   ├── 2_CAGE_Lookup.py    # CAGE code lookup
│   ├── 3_NSN_Lookup.py     # NSN/NIIN lookup
│   ├── 4_FSC_Browser.py    # FSC browser
│   └── 5_Admin.py      # Admin dashboard
└── Data/               # PubLog data files (not included)
```

## Configuration

Edit `config.py` to customize:

- `DB_PATH` - Location of the DuckDB database file
- `API_PORT` - REST API port (default: 8000)
- `DATA_FILES` - Mapping of table names to CSV file paths
- `PRIORITY_TABLES` - Tables to index first (smaller, frequently used)
- `LARGE_TABLES` - Large tables that take longer to index

## Troubleshooting

### "No items found" when browsing by FSC
Make sure you've indexed the P_FLIS_NSN table from the Admin page. This table contains the FSC-to-NIIN mappings.

### Database permission errors
The application stores the DuckDB database in `/tmp/publog_index.duckdb` by default. If you encounter permission issues, modify `DB_PATH` in `config.py` to a writable location.

### Streamlit command not found
Use `python3 -m streamlit run app.py` instead of `streamlit run app.py`.

### Large file indexing is slow
Indexing large files like FLISV.CSV (2.2GB) or P_FLIS_NSN.CSV (1GB) can take several minutes. The Admin page shows progress during indexing.

## License

MIT License - See LICENSE file for details.

## Disclaimer

This application is an unofficial tool for working with publicly available FLIS/PubLog data. It is not affiliated with or endorsed by the Defense Logistics Agency (DLA) or the U.S. Department of Defense.
