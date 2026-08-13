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

@router.get("/api/technicals/{symbol}")
async def get_technicals(symbol: str):
    try:
        from modules.technicals import get_technical_analysis
        return _json_safe_clean(await get_technical_analysis(symbol))
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/drift/{symbol}")
async def get_drift(symbol: str):
    """Detect investment thesis drift for a single stock."""
    try:
        symbol = normalize_symbol(symbol)
        def _fetch_drift_data():
            conn = get_connection()
            try:
                # Fetch recent technicals and fundamentals
                row = pd.read_sql("SELECT * FROM multibaggers WHERE symbol = ?", conn, params=(symbol,))
                if row.empty:
                    return None
                return row.iloc[0].to_dict()
            finally:
                conn.close()
        
        stock_data = await _run_blocking(_fetch_drift_data)
        if not stock_data:
            return {"error": "Stock data not found"}
            
        status, reason = monitor_drift(stock_data)
        return {
            "symbol": symbol,
            "status": status,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/allocation/hrp")
async def get_hrp_allocation():
    """Calculate HRP weights for top 15 stocks based on 1Y returns."""
    try:
        def _get_top_symbols():
            conn = get_connection()
            try:
                df = pd.read_sql("SELECT symbol FROM multibaggers ORDER BY score DESC LIMIT 15", conn)
                return df["symbol"].tolist()
            finally:
                conn.close()
        
        symbols = await _run_blocking(_get_top_symbols)
        if not symbols:
            return {"error": "No stocks found for allocation"}
            
        # Download historical prices for 1 year
        data = await run_with_exponential_backoff(
            lambda: _run_ticker_blocking(
                yf.download,
                symbols,
                period="1y",
                interval="1d",
                progress=False,
                auto_adjust=True
            ),
            context="hrp allocation price fetch"
        )
        
        if data.empty:
            return {"error": "Failed to fetch historical data"}
            
        # Calculate returns - handle MultiIndex carefully
        if isinstance(data.columns, pd.MultiIndex):
            prices = data["Close"] if "Close" in data else data.xs('Close', axis=1, level=0)
        else:
            prices = data[["Close"]] if "Close" in data.columns else data
            
        returns = prices.pct_change().dropna(how='all').fillna(0)
        
        allocator = HRPAllocator()
        weights = allocator.allocate(returns)
        
        # Sort by weight descending
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "weights": {k: float(v) for k, v in sorted_weights},
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

