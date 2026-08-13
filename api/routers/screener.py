from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Request
from typing import Any, List, Optional, Dict
from pydantic import BaseModel, Field
import asyncio
import sqlite3
import pandas as pd
import json
import os
import math
from datetime import datetime, timedelta

from api.dependencies import (
    manager, blocking_io_semaphore, ticker_io_semaphore, portfolio_tracker, risk_governor,
    regime_cache, movers_cache, regime_cache_lock, movers_cache_lock,
    CACHE_QUARTERLY, CACHE_FUNDAMENTALS, CACHE_PEERS, CACHE_AUDIT_TTL,
    _run_blocking, _run_ticker_blocking, _cache_is_fresh, _cache_set, _cache_invalidate,
    OrderRequest
)
import config
from modules.market_data import MarketDataProvider
from database import get_connection

router = APIRouter()

@router.get("/api/stocks")
async def get_multibaggers(as_of_date: str | None = None):
    """Fetch Top Multibagger Picks"""
    try:
        if as_of_date:
            import database as database_module

            def _read_as_of_records():
                df, snapshot_date = database_module.load_fundamentals_universe_as_of(
                    as_of_date
                )
                if df.empty:
                    return []
                df = df.replace([np.inf, -np.inf], np.nan).replace({np.nan: None})
                records = df.to_dict(orient="records")
                for record in records:
                    if not record.get("as_of_date"):
                        record["as_of_date"] = snapshot_date
                return records

            return await _run_blocking(_read_as_of_records)

        # 1. Fetch Multibaggers (Phase 6: Deterministic Tie-Breaker Sorting)
        records = await _run_blocking(
            _read_records, "SELECT * FROM multibaggers ORDER BY score DESC, rs_rating DESC, market_cap_cr DESC"
        )

        if not records:
            return []

        return _json_safe_clean(records)
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/multibagger-hunt")
async def get_multibagger_hunt():
    """Fetch stocks meeting the strict Multibagger Hunt criteria"""
    try:
        # Framework Filters from ticker_list.py
        query = """
            SELECT * FROM multibaggers
            WHERE sales_cagr_5y >= 0.15
              AND avg_roe_5y >= 0.15
              AND debt_equity <= 0.5
              AND cfo_pat_ratio >= 0.80
              AND promoter_holding >= 50.0
              AND (pledge_pct = 0.0 OR pledge_pct IS NULL)
              AND (piotroski_score >= 6 OR (piotroski_score IS NULL AND f_score >= 6))
              AND market_cap_cr <= 5000
            ORDER BY ml_rank_score DESC, score DESC
        """
        records = await _run_blocking(_read_records, query)
        
        if not records:
            return []
            
        return _json_safe_clean(records)
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/microcaps")
async def get_microcaps():
    """Fetch Hidden Microcap Gems"""
    try:
        return await _run_blocking(
            _read_records, "SELECT * FROM microcaps ORDER BY score DESC"
        )
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/liquidity")
def get_liquidity():
    try:
        if os.path.exists("liquidity.json"):
            with open("liquidity.json", "r") as f:
                return json.load(f)
        return {"error": "Report not generated yet."}
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/recovery")
def get_recovery():
    try:
        if os.path.exists("recovery.json"):
            with open("recovery.json", "r") as f:
                return json.load(f)
        return {"error": "Report not generated yet."}
    except Exception as e:
        return {"error": str(e)}

@router.post("/api/scan")
async def run_scan():
    """Trigger a full market scan using screener.py"""
    try:
        import sys
        process = await asyncio.create_subprocess_exec(
            sys.executable, "screener.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        return {"status": "scan_initiated", "pid": process.pid}
    except Exception as e:
        return {"error": str(e)}

