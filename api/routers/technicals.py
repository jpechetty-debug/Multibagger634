from fastapi import APIRouter
import pandas as pd
from datetime import datetime

import yfinance as yf

from api.dependencies import (
    _run_blocking, _run_ticker_blocking, _json_safe_clean
)
from database import get_connection
from modules.symbol_utils import normalize_symbol
from modules.drift_monitor import monitor_drift
from modules.retry_utils import run_with_exponential_backoff
from modules.allocation_hrp import HRPAllocator

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

