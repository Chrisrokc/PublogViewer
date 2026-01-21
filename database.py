"""
Database connection and management for PubLog Application
Uses DuckDB for fast analytical queries on large CSV files
"""
import duckdb
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from config import DB_PATH, DATA_FILES, PRIORITY_TABLES, LARGE_TABLES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PubLogDatabase:
    """Manages DuckDB database for PubLog data"""

    _instance: Optional['PubLogDatabase'] = None
    _connection: Optional[duckdb.DuckDBPyConnection] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._connection is None:
            self._connection = duckdb.connect(str(DB_PATH))
            self._setup_extensions()

    def _setup_extensions(self):
        """Setup DuckDB extensions for better CSV handling"""
        try:
            self._connection.execute("INSTALL httpfs; LOAD httpfs;")
        except:
            pass  # Extension might already be installed

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        return self._connection

    def get_all_data_files(self) -> Dict[str, Path]:
        """Get flat dictionary of all data files"""
        all_files = {}
        for category, files in DATA_FILES.items():
            all_files.update(files)
        return all_files

    def is_table_indexed(self, table_name: str) -> bool:
        """Check if a table is already indexed in DuckDB"""
        try:
            # DuckDB stores table names - check both upper and lower case
            result = self._connection.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE UPPER(table_name) = UPPER(?)",
                [table_name]
            ).fetchone()
            return result[0] > 0
        except Exception as e:
            logger.error(f"Error checking table {table_name}: {e}")
            return False

    def get_indexed_tables(self) -> List[str]:
        """Get list of all indexed tables"""
        try:
            result = self._connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Error getting indexed tables: {e}")
            return []

    def index_csv_file(self, table_name: str, file_path: Path, force: bool = False) -> bool:
        """Index a CSV file into DuckDB"""
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return False

        if self.is_table_indexed(table_name) and not force:
            logger.info(f"Table {table_name} already indexed, skipping")
            return True

        try:
            # Drop existing table if force
            if force:
                self._connection.execute(f"DROP TABLE IF EXISTS {table_name}")

            # Get file size for logging
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"Indexing {table_name} ({file_size_mb:.1f} MB)...")

            # Create table from CSV
            self._connection.execute(f"""
                CREATE TABLE {table_name} AS
                SELECT * FROM read_csv_auto('{file_path}',
                    header=true,
                    quote='"',
                    escape='"',
                    ignore_errors=true,
                    sample_size=10000
                )
            """)

            # Get row count
            count = self._connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            logger.info(f"Indexed {table_name}: {count:,} rows")

            return True
        except Exception as e:
            logger.error(f"Error indexing {table_name}: {e}")
            return False

    def create_indexes(self, table_name: str, columns: List[str]):
        """Create indexes on specific columns for faster lookups"""
        for col in columns:
            try:
                index_name = f"idx_{table_name}_{col}".lower()
                self._connection.execute(
                    f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({col})"
                )
                logger.info(f"Created index {index_name}")
            except Exception as e:
                logger.warning(f"Could not create index on {table_name}.{col}: {e}")

    def index_priority_tables(self, force: bool = False) -> Dict[str, bool]:
        """Index priority (smaller) tables first"""
        results = {}
        all_files = self.get_all_data_files()

        for table_name in PRIORITY_TABLES:
            if table_name in all_files:
                results[table_name] = self.index_csv_file(
                    table_name, all_files[table_name], force
                )

        return results

    def index_large_tables(self, force: bool = False) -> Dict[str, bool]:
        """Index large tables (may take longer)"""
        results = {}
        all_files = self.get_all_data_files()

        for table_name in LARGE_TABLES:
            if table_name in all_files:
                results[table_name] = self.index_csv_file(
                    table_name, all_files[table_name], force
                )

        return results

    def index_all_tables(self, force: bool = False) -> Dict[str, bool]:
        """Index all available tables"""
        results = {}
        all_files = self.get_all_data_files()

        # Index priority tables first
        results.update(self.index_priority_tables(force))

        # Then large tables
        results.update(self.index_large_tables(force))

        # Any remaining tables
        for table_name, file_path in all_files.items():
            if table_name not in results:
                results[table_name] = self.index_csv_file(table_name, file_path, force)

        return results

    def query(self, sql: str, params: Optional[List] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dicts"""
        try:
            if params:
                result = self._connection.execute(sql, params)
            else:
                result = self._connection.execute(sql)

            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()

            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Query error: {e}")
            raise

    def query_df(self, sql: str, params: Optional[List] = None):
        """Execute a query and return results as DataFrame"""
        try:
            if params:
                return self._connection.execute(sql, params).fetchdf()
            else:
                return self._connection.execute(sql).fetchdf()
        except Exception as e:
            logger.error(f"Query error: {e}")
            raise

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about a table"""
        try:
            # Get column info
            columns = self._connection.execute(
                f"DESCRIBE {table_name}"
            ).fetchall()

            # Get row count
            count = self._connection.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]

            return {
                "table_name": table_name,
                "row_count": count,
                "columns": [
                    {"name": col[0], "type": col[1]}
                    for col in columns
                ]
            }
        except Exception as e:
            logger.error(f"Error getting table info for {table_name}: {e}")
            return {}

    def get_database_stats(self) -> Dict[str, Any]:
        """Get overall database statistics"""
        tables = self.get_indexed_tables()
        total_rows = 0
        table_stats = []

        for table in tables:
            try:
                count = self._connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                total_rows += count
                table_stats.append({"table": table, "rows": count})
            except:
                pass

        return {
            "total_tables": len(tables),
            "total_rows": total_rows,
            "tables": sorted(table_stats, key=lambda x: x["rows"], reverse=True),
            "db_file_size_mb": DB_PATH.stat().st_size / (1024 * 1024) if DB_PATH.exists() else 0
        }

    def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
            PubLogDatabase._instance = None


# Singleton accessor
def get_db() -> PubLogDatabase:
    return PubLogDatabase()
