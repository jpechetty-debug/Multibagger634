# modules/bhavcopy.py
# NSE Bhavcopy downloader + SQLite store + DataProvider implementation
# Uses jugaad-data to fetch official EOD data for the full NSE universe.

import csv
import logging
import os
import sqlite3
import tempfile
from datetime import date, timedelta
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bhavcopy.db")
# Only keep EQ (equity) series
_VALID_SERIES = {"EQ", "BE", "BZ", "SM", "ST", ""}


# ── SQLite helpers ──────────────────────────────────────────────────
def _init_db(db_path: str = DB_PATH):
    with sqlite3.connect(db_path, timeout=10) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bhavcopy (
                symbol   TEXT NOT NULL,
                trade_dt TEXT NOT NULL,
                series   TEXT,
                open     REAL,
                high     REAL,
                low      REAL,
                close    REAL,
                last     REAL,
                prev_close REAL,
                volume   INTEGER,
                turnover REAL,
                isin     TEXT,
                PRIMARY KEY (symbol, trade_dt)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bhav_dt ON bhavcopy(trade_dt)")
        conn.commit()


def _latest_date_in_db(db_path: str = DB_PATH) -> Optional[str]:
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            row = conn.execute("SELECT MAX(trade_dt) FROM bhavcopy").fetchone()
            return row[0] if row and row[0] else None
    except Exception:
        return None


# ── Download + Parse ────────────────────────────────────────────────
def download_bhavcopy(dt: Optional[date] = None, db_path: str = DB_PATH) -> int:
    """Download bhavcopy for `dt` (default: latest trading day) and upsert
    into SQLite. Returns number of rows inserted."""
    from jugaad_data.nse import bhavcopy_save

    _init_db(db_path)

    if dt is None:
        # Walk back up to 5 days to find latest trading day
        for offset in range(0, 6):
            candidate = date.today() - timedelta(days=offset)
            if candidate.weekday() >= 5:
                continue
            dt = candidate
            break
        if dt is None:
            dt = date.today() - timedelta(days=2)

    # Check if already loaded
    dt_str = dt.strftime("%Y-%m-%d")
    existing = _latest_date_in_db(db_path)
    if existing == dt_str:
        logger.info(f"Bhavcopy for {dt_str} already in DB, skipping download.")
        return 0

    dest = tempfile.mkdtemp()
    try:
        csv_path = bhavcopy_save(dt, dest, skip_if_present=False)
    except Exception as e:
        logger.warning(f"Bhavcopy download failed for {dt_str}: {e}")
        # Try previous trading day
        for offset in range(1, 4):
            prev = dt - timedelta(days=offset)
            if prev.weekday() >= 5:
                continue
            try:
                csv_path = bhavcopy_save(prev, dest, skip_if_present=False)
                dt_str = prev.strftime("%Y-%m-%d")
                break
            except Exception:
                continue
        else:
            raise RuntimeError(f"Could not download bhavcopy for any recent date: {e}")

    rows = _parse_and_store(csv_path, db_path)
    logger.info(f"✅ Bhavcopy loaded: {rows} equity rows for {dt_str}")
    return rows


def _parse_and_store(csv_path: str, db_path: str = DB_PATH) -> int:
    """Parse the jugaad-data bhavcopy CSV and upsert into SQLite."""
    records = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            series = row.get("SctySrs", "").strip()
            if series not in _VALID_SERIES:
                continue
            # Skip non-stock instruments (gold bonds, etc.)
            fin_type = row.get("FinInstrmTp", "").strip()
            if fin_type != "STK":
                continue
            try:
                records.append((
                    row.get("TckrSymb", "").strip(),
                    row.get("TradDt", "").strip(),
                    series,
                    float(row.get("OpnPric", 0) or 0),
                    float(row.get("HghPric", 0) or 0),
                    float(row.get("LwPric", 0) or 0),
                    float(row.get("ClsPric", 0) or 0),
                    float(row.get("LastPric", 0) or 0),
                    float(row.get("PrvsClsgPric", 0) or 0),
                    int(float(row.get("TtlTradgVol", 0) or 0)),
                    float(row.get("TtlTrfVal", 0) or 0),
                    row.get("ISIN", "").strip(),
                ))
            except (ValueError, TypeError):
                continue

    with sqlite3.connect(db_path, timeout=10) as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO bhavcopy VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            records,
        )
        conn.commit()
    return len(records)


# ── Query API ───────────────────────────────────────────────────────
def get_eod_price(symbol: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Return latest EOD row for a symbol (without .NS suffix)."""
    bare = symbol.replace(".NS", "").replace(".BO", "").strip().upper()
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM bhavcopy WHERE symbol=? ORDER BY trade_dt DESC LIMIT 1",
                (bare,),
            ).fetchone()
            return dict(row) if row else None
    except Exception:
        return None


def get_all_eod(trade_dt: Optional[str] = None, db_path: str = DB_PATH) -> pd.DataFrame:
    """Return full bhavcopy for a date (default: latest)."""
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            if trade_dt:
                return pd.read_sql("SELECT * FROM bhavcopy WHERE trade_dt=?", conn, params=(trade_dt,))
            else:
                latest = _latest_date_in_db(db_path)
                if not latest:
                    return pd.DataFrame()
                return pd.read_sql("SELECT * FROM bhavcopy WHERE trade_dt=?", conn, params=(latest,))
    except Exception:
        return pd.DataFrame()
