import asyncio
import json
import os
import sqlite3
import time
from typing import Any, Callable
from fastapi import WebSocket
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from database import get_connection
from modules.risk import RiskGovernor
from modules.tracker import PortfolioTracker

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

manager = ConnectionManager()

DB_NAME = "stocks.db"
DB_PATH = DB_NAME

DB_BUSY_TIMEOUT_MS = 5000
SQLITE_WRITE_RETRIES = 5
SQLITE_RETRY_BASE_SECONDS = 0.05
BLOCKING_IO_CONCURRENCY = 32
REGIME_CACHE_TTL_SECONDS = int(os.getenv("REGIME_CACHE_TTL_SECONDS", "120"))
MOVERS_CACHE_TTL_SECONDS = int(os.getenv("MOVERS_CACHE_TTL_SECONDS", "120"))

blocking_io_semaphore = asyncio.Semaphore(BLOCKING_IO_CONCURRENCY)
ticker_io_semaphore = asyncio.Semaphore(10)  

portfolio_tracker = PortfolioTracker()
risk_governor = RiskGovernor()

regime_cache = {"payload": None, "timestamp": 0.0}
movers_cache = {"payload": None, "timestamp": 0.0}
regime_cache_lock = asyncio.Lock()
movers_cache_lock = asyncio.Lock()

CACHE_QUARTERLY = {}
CACHE_FUNDAMENTALS = {}
CACHE_PEERS = {}
CACHE_AUDIT_TTL = 3600  

def _json_safe_clean(obj):
    if isinstance(obj, list):
        return [_json_safe_clean(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _json_safe_clean(v) for k, v in obj.items()}
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
    return obj

def _cache_is_fresh(cache_dict, ttl):
    if not cache_dict or "timestamp" not in cache_dict:
        return False
    return (time.time() - cache_dict["timestamp"]) < ttl

def _cache_set(cache_dict, payload):
    cache_dict["payload"] = payload
    cache_dict["timestamp"] = time.time()

def _cache_invalidate(cache_dict):
    cache_dict["timestamp"] = 0.0

async def _run_blocking(fn: Callable[..., Any], *args, **kwargs):
    async with blocking_io_semaphore:
        return await asyncio.to_thread(fn, *args, **kwargs)

async def _run_ticker_blocking(fn: Callable[..., Any], *args, **kwargs):
    async with ticker_io_semaphore:
        async with blocking_io_semaphore:
            return await asyncio.to_thread(fn, *args, **kwargs)

def _is_sqlite_lock_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "database is locked" in msg or "database table is locked" in msg

async def _run_sqlite_write_with_retry(
    write_fn: Callable[[], Any], operation_name: str
):
    for attempt in range(SQLITE_WRITE_RETRIES):
        try:
            return await _run_blocking(write_fn)
        except sqlite3.OperationalError as exc:
            if _is_sqlite_lock_error(exc) and attempt < SQLITE_WRITE_RETRIES - 1:
                wait = SQLITE_RETRY_BASE_SECONDS * (2 ** attempt)
                print(f"SQLite lock during {operation_name}; retrying in {wait:.2f}s.")
                await asyncio.sleep(wait)
                continue
            raise

def _run_sqlite_write_with_retry_sync(
    write_fn: Callable[[], Any], operation_name: str
):
    for attempt in range(SQLITE_WRITE_RETRIES):
        try:
            return write_fn()
        except sqlite3.OperationalError as exc:
            if _is_sqlite_lock_error(exc) and attempt < SQLITE_WRITE_RETRIES - 1:
                wait = SQLITE_RETRY_BASE_SECONDS * (2 ** attempt)
                print(f"SQLite lock during {operation_name}; retrying in {wait:.2f}s.")
                time.sleep(wait)
                continue
            raise

def _read_records(query: str, params: tuple | None = None):
    conn = get_connection()
    try:
        if params is not None:
            df = pd.read_sql(query, conn, params=params)
        else:
            df = pd.read_sql(query, conn)
        return json.loads(df.to_json(orient="records", double_precision=2))
    finally:
        conn.close()

class OrderRequest(BaseModel):
    symbol: str = Field(min_length=1)
    side: str = Field(description="BUY or SELL")
    quantity: int = Field(default=1, ge=1)
    price: float = Field(gt=0)
    score: float = 0.0
    reason: str = "MANUAL"
    current_vix: float | None = None
    drawdown_rate_weekly: float | None = None
    portfolio_correlation: float | None = None
    projected_var_pct: float | None = None
    max_var_pct: float = 20.0
