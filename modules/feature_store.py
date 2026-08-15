import duckdb
import pandas as pd
from datetime import datetime
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parents[1]
STORE_DIR = ROOT_DIR / "feature_store"
DB_PATH = STORE_DIR / "features.duckdb"

# Ensure directory exists
STORE_DIR.mkdir(parents=True, exist_ok=True)

def _get_conn():
    """Get a connection to the DuckDB feature store."""
    # Using a single file for transactional safety and lightning fast columnar access
    return duckdb.connect(str(DB_PATH))

def save_features(df: pd.DataFrame, category: str, as_of_date: str = None):
    """
    Saves a DataFrame of computed factors/features into the Feature Store.
    
    Args:
        df: Pandas DataFrame containing the features. Must have a 'Symbol' column.
        category: The factor family (e.g., 'quality', 'valuation', 'momentum').
        as_of_date: The point-in-time date (YYYY-MM-DD). Defaults to today.
    """
    if as_of_date is None:
        as_of_date = datetime.now().strftime("%Y-%m-%d")
        
    if df.empty:
        return
        
    # Inject the PIT date
    df_insert = df.copy()
    df_insert['as_of_date'] = as_of_date
    
    table_name = f"fs_{category}"
    
    with _get_conn() as conn:
        # Check if table exists
        tables = conn.execute("SHOW TABLES").df()
        if table_name not in tables['name'].values:
            # Create table directly from the dataframe schema
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df_insert")
        else:
            # Table exists. 
            # 1. Delete existing records for this date to avoid duplicates (upsert behavior)
            conn.execute(f"DELETE FROM {table_name} WHERE as_of_date = ?", [as_of_date])
            # 2. Insert new records
            conn.execute(f"INSERT INTO {table_name} SELECT * FROM df_insert")

def load_features(category: str, as_of_date: str = None, symbols: list = None) -> pd.DataFrame:
    """
    Loads features for a specific category, optionally filtered by date and symbol.
    """
    table_name = f"fs_{category}"
    
    with _get_conn() as conn:
        tables = conn.execute("SHOW TABLES").df()
        if table_name not in tables['name'].values:
            return pd.DataFrame()
            
        query = f"SELECT * FROM {table_name} WHERE 1=1"
        params = []
        
        if as_of_date:
            query += " AND as_of_date = ?"
            params.append(as_of_date)
            
        if symbols:
            # Create a placeholder string ?, ?, ?
            placeholders = ", ".join(["?"] * len(symbols))
            query += f" AND Symbol IN ({placeholders})"
            params.extend(symbols)
            
        return conn.execute(query, params).df()

def export_to_parquet():
    """
    Exports all DuckDB tables to Parquet files for cold storage or external sharing.
    """
    with _get_conn() as conn:
        tables = conn.execute("SHOW TABLES").df()
        for table in tables['name']:
            out_path = STORE_DIR / f"{table}.parquet"
            conn.execute(f"COPY {table} TO '{out_path}' (FORMAT PARQUET)")
            print(f"Exported {table} to {out_path}")
