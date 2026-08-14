from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Request
from typing import Any, List, Optional, Dict
from pydantic import BaseModel, Field
import asyncio
import sqlite3
import pandas as pd
import json
import os
import math
import numpy as np
from datetime import datetime, timedelta

from api.dependencies import (
    manager, blocking_io_semaphore, ticker_io_semaphore, portfolio_tracker, risk_governor,
    regime_cache, movers_cache, regime_cache_lock, movers_cache_lock,
    CACHE_QUARTERLY, CACHE_FUNDAMENTALS, CACHE_PEERS, CACHE_AUDIT_TTL,
    _run_blocking, _run_ticker_blocking, _cache_is_fresh, _cache_set, _cache_invalidate,
    _json_safe_clean,
    OrderRequest
)
import config
from modules.market_data import MarketDataProvider
from database import get_connection

router = APIRouter()

async def _with_cache(cache_dict, symbol, fetch_fn):
    import time
    start_time = time.time()
    
    from api.dependencies import _cache_is_fresh, _cache_set, CACHE_AUDIT_TTL
    if _cache_is_fresh(cache_dict.get(symbol, {}), CACHE_AUDIT_TTL):
        print(f"CACHE HIT for {symbol}")
        return cache_dict[symbol]["payload"]
        
    print(f"API Request for {symbol}")
    result = await fetch_fn()
    
    cleaned = _json_safe_clean(result)
    
    if symbol not in cache_dict:
        cache_dict[symbol] = {}
    _cache_set(cache_dict[symbol], cleaned)
    
    print(f"JSON cleaned and cached for {symbol} (took {time.time() - start_time:.2f}s)")
    return cleaned


@router.get("/api/valuation/{symbol}")
async def get_valuation(symbol: str, as_of_date: str | None = None):
    try:
        valuation_as_of = (as_of_date or datetime.now().date().isoformat())[:10]

        def _normalize_valuation_payload(payload: dict):
            if not payload:
                return payload

            def _component_or_none(value):
                try:
                    parsed = float(value)
                except (TypeError, ValueError):
                    return None
                if not np.isfinite(parsed) or parsed <= 0:
                    return None
                return parsed

            if isinstance(payload.get("components"), dict):
                components = payload.get("components", {})
                payload["components"] = {
                    "dcf": _component_or_none(components.get("dcf")),
                    "graham": _component_or_none(components.get("graham")),
                    "epv": _component_or_none(components.get("epv")),
                }
                payload.setdefault("symbol", symbol)
                payload.setdefault("as_of_date", valuation_as_of)
                if payload.get("intrinsic_value") in (0, 0.0):
                    payload["intrinsic_value"] = None
                return payload

            normalized = {
                "symbol": payload.get("symbol", symbol),
                "intrinsic_value": payload.get("intrinsic_value", 0) or None,
                "margin_of_safety": payload.get("margin_of_safety", 0),
                "verdict": payload.get("verdict", "UNKNOWN"),
                "confidence_score": payload.get("confidence_score"),
                "calculated_at": payload.get("calculated_at"),
                "as_of_date": payload.get("as_of_date") or valuation_as_of,
                "components": {
                    "dcf": _component_or_none(payload.get("dcf_value", 0)),
                    "graham": _component_or_none(payload.get("graham_value", 0)),
                    "epv": _component_or_none(payload.get("epv_value", 0)),
                },
            }
            return normalized

        def _ensure_valuation_table():
            conn = get_connection()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS valuation_metrics (
                        symbol TEXT PRIMARY KEY,
                        dcf_value REAL,
                        graham_value REAL,
                        epv_value REAL,
                        intrinsic_value REAL,
                        margin_of_safety REAL,
                        verdict TEXT,
                        confidence_score INTEGER,
                        as_of_date TEXT,
                        calculated_at TIMESTAMP
                    )
                    """
                )
                columns = [row[1] for row in conn.execute("PRAGMA table_info(valuation_metrics)").fetchall()]
                if "as_of_date" not in columns:
                    conn.execute("ALTER TABLE valuation_metrics ADD COLUMN as_of_date TEXT")
                conn.commit()
            finally:
                conn.close()

        await _run_sqlite_write_with_retry(_ensure_valuation_table, "valuation table init")

        def _read_cached():
            conn = get_connection()
            try:
                if as_of_date:
                    query = """
                        SELECT *
                        FROM valuation_metrics
                        WHERE symbol = ? AND as_of_date <= ?
                        ORDER BY as_of_date DESC, calculated_at DESC
                        LIMIT 1
                    """
                    existing_local = pd.read_sql(query, conn, params=(symbol, valuation_as_of))
                else:
                    query = """
                        SELECT *
                        FROM valuation_metrics
                        WHERE symbol = ?
                        ORDER BY calculated_at DESC
                        LIMIT 1
                    """
                    existing_local = pd.read_sql(query, conn, params=(symbol,))
                if not existing_local.empty:
                    return existing_local.iloc[0].to_dict()
                return None
            finally:
                conn.close()

        cached = await _run_blocking(_read_cached)
        if cached:
            return _normalize_valuation_payload(cached)

        ticker = yf.Ticker(symbol)

        info = await run_with_exponential_backoff(
            lambda: _run_blocking(lambda: ticker.info),
            context=f"yfinance valuation for {symbol}",
        )

        if not info:
            return {"error": f"Failed to fetch valuation data for {symbol} (Throttled)"}

        # --- Alpha Vantage Fallback for Missing Yahoo Data ---
        av_data = None
        critical_missing = (
            not info.get("trailingEps")
            or not info.get("bookValue")
            or not info.get("currentPrice")
        )
        if critical_missing:
            try:
                from modules.alpha_vantage import AlphaVantageProvider, get_remaining_budget
                if get_remaining_budget() >= 2:
                    av = AlphaVantageProvider()
                    av_data = await _run_blocking(av.get_company_overview, symbol)
                    if av_data:
                        print(f"  ✅ AV fallback for {symbol}: filling missing valuation fields")
            except Exception as av_err:
                print(f"  ⚠️ AV fallback skipped for {symbol}: {av_err}")

        # Merge: prefer Yahoo, fall back to AV
        def _get(yahoo_key, av_key=None, default=0):
            val = info.get(yahoo_key)
            if val not in (None, 0, ""):
                return val
            if av_data and av_key:
                av_val = av_data.get(av_key)
                if av_val is not None:
                    return av_val
            return default

        data = {
            "current_price": _get("currentPrice", None, 0),
            "eps_ttm": _get("trailingEps", "eps", 0),
            "book_value_per_share": _get("bookValue", "book_value", 0),
            "free_cash_flow_per_share": (
                (info.get("operatingCashflow", 0) - abs(info.get("capitalExpenditures", 0)))
                / info.get("sharesOutstanding", 1)
                if info.get("operatingCashflow")
                else 0
            ),
            "growth_rate_5y": _get("earningsGrowth", None, 0.10) * 100,
            "beta": _get("beta", "beta", 1.0),
            "data_source": "yahoo+alpha_vantage" if av_data else "yahoo",
        }

        from modules.valuation import ValuationEngine

        engine = ValuationEngine(data)
        metrics = engine.get_intrinsic_value()

        def _write_valuation():
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO valuation_metrics
                    (symbol, dcf_value, graham_value, epv_value, intrinsic_value, margin_of_safety, verdict, confidence_score, as_of_date, calculated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        symbol,
                        metrics["components"]["dcf"],
                        metrics["components"]["graham"],
                        metrics["components"]["epv"],
                        metrics["intrinsic_value"],
                        metrics["margin_of_safety"],
                        metrics["verdict"],
                        85,
                        valuation_as_of,
                        datetime.now(),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        await _run_sqlite_write_with_retry(_write_valuation, "valuation upsert")
        metrics["symbol"] = symbol
        metrics["as_of_date"] = valuation_as_of
        return _json_safe_clean(_normalize_valuation_payload(metrics))

    except Exception as e:
        print(f"Valuation Error: {e}")
        return {"error": str(e)}


@router.get("/api/governance/{symbol}")
async def get_governance_data(symbol: str):
    """Fetch 8-Point Governance Checklist Data"""
    try:
        if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
            symbol += ".NS"
            
        def _fetch_gov_data():
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Helper for safe extraction
            def get_val(key, default=None):
                v = info.get(key, default)
                return v if v is not None else default

            # Detect Sector for Debt/Equity logic
            sector = get_val('sector', 'Unknown')
            is_financial = 'Financial' in sector or 'Bank' in sector

            # 1. ROE
            roe_raw = get_val('returnOnEquity', 0)
            roe = round(roe_raw * 100, 2) if roe_raw else 0
            
            # 2. Debt/Equity
            de_raw = get_val('debtToEquity', 0)
            de = round(de_raw / 100, 2) if de_raw else 0
            
            # 3. Sales Growth (Quarterly YoY or TTM)
            sales_growth_raw = get_val('revenueGrowth', 0)
            sales_growth = round(sales_growth_raw * 100, 2) if sales_growth_raw else 0
            
            # 4. Profit Growth (Earnings Growth)
            profit_growth_raw = get_val('earningsGrowth', 0)
            profit_growth = round(profit_growth_raw * 100, 2) if profit_growth_raw else 0
            
            # 5. Promoter Holding
            promoter_holding_raw = get_val('heldPercentInsiders', 0)
            promoter_holding = round(promoter_holding_raw * 100, 2) if promoter_holding_raw else 0
            
            # 6. Pledged Algo (Not in YF usually, defaulting to 0 for check)
            pledged = 0 
            
            # 7. CFO/PAT Check (Need Cashflow and Net Income)
            cfo = get_val('operatingCashflow', 0)
            ni = get_val('netIncomeToCommon', 1) # Avoid div/0
            cfo_pat = round(cfo / ni, 2) if ni and cfo else 0
            
            return {
                "symbol": symbol,
                "sector": sector,
                "is_financial": is_financial,
                "roe": roe,
                "debt_to_equity": de,
                "sales_growth": sales_growth,
                "profit_growth": profit_growth,
                "promoter_holding": promoter_holding,
                "pledged_pct": pledged,
                "cfo_pat_ratio": cfo_pat
            }

        data = await _run_blocking(_fetch_gov_data)
        return data
        
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/peers/{symbol}")
async def get_stock_peers(symbol: str):
    """Fetch Sector Peers for Comparison"""
    try:
        if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
            symbol += ".NS"

        def _get_peers():
            conn = get_connection()
            try:
                # 1. Get Target Metrics
                target_query = "SELECT symbol, sector, price as current_price, score as terminal_score, pe_ratio as pe, roe, debt_equity, rs_rating as price_change_3m FROM multibaggers WHERE symbol = ?"
                target = pd.read_sql(target_query, conn, params=(symbol,))
                if target.empty:
                    return {"error": "Stock not found"}
                
                start_sector = target.iloc[0]['sector']

                # 2. Get Peers using Subquery for Sector (More robust)
                query = """
                    SELECT symbol, symbol as name, price as current_price, score as terminal_score, pe_ratio as pe, roe, debt_equity, rs_rating as price_change_3m
                    FROM multibaggers 
                    WHERE sector = (SELECT sector FROM multibaggers WHERE symbol = ?) 
                    AND symbol != ?
                    ORDER BY score DESC
                    LIMIT 5
                """
                peers_df = pd.read_sql(query, conn, params=(symbol, symbol))
                peers = peers_df.to_dict(orient="records")
                
                # 3. Sector Averages
                avg_query = """
                    SELECT 
                        AVG(pe_ratio) as pe, 
                        AVG(roe) as roe, 
                        AVG(score) as terminal_score 
                    FROM multibaggers 
                    WHERE sector = (SELECT sector FROM multibaggers WHERE symbol = ?)
                """
                # Use execute directly for scalar values to avoid overhead? No, pandas is fine.
                avg_df = pd.read_sql(avg_query, conn, params=(symbol,))
                if not avg_df.empty:
                    avgs = avg_df.iloc[0].to_dict()
                else:
                    avgs = {}
                
                return {
                    "sector": start_sector,
                    "peers": peers,
                    "sector_avg": avgs,
                    "stock_metrics": target.iloc[0].to_dict(),
                    "rankings": {"score_rank_desc": "Top 10"}
                }
            finally:
                conn.close()

        return await _run_blocking(_get_peers)

    except Exception as e:
        return {"error": str(e)}

@router.get("/api/promoter/{symbol}")
async def get_promoter_intel(symbol: str):
    """Fetch Promoter Behaviour Intelligence (trends, deals, pledge, scoring)."""
    try:
        from modules.promoter_intel import calculate_promoter_score
        if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
            symbol += ".NS"
        return await _run_blocking(calculate_promoter_score, symbol)
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/shareholding/{symbol}")
async def get_shareholding(symbol: str):
    try:
        from modules.shareholding import get_shareholding_pattern
        return _json_safe_clean(await get_shareholding_pattern(symbol))
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/quarterly-results/{symbol}")
async def quarterly_results_endpoint(symbol: str, quarters: int = 12):
    try:
        from modules.quarterly_results import get_quarterly_timeline
        return await _with_cache(CACHE_QUARTERLY, symbol, lambda: get_quarterly_timeline(symbol, quarters))
    except Exception as e:
        from fastapi import HTTPException
        print(f"Error in quarterly_results_endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch quarterly results: {str(e)}")

@router.get("/api/price-fundamentals/{symbol}")
async def price_fundamentals_endpoint(symbol: str, years: int = 5):
    try:
        from modules.price_fundamentals import get_price_vs_fundamentals
        years = min(max(years, 3), 10)
        return await _with_cache(CACHE_FUNDAMENTALS, symbol, lambda: get_price_vs_fundamentals(symbol, years))
    except Exception as e:
        from fastapi import HTTPException
        print(f"Error in price_fundamentals_endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch price vs fundamentals: {str(e)}")

@router.get("/api/estimates/{symbol}")
async def get_estimates(symbol: str):
    """Fetch forward-looking estimate momentum data."""
    try:
        from modules.estimates import get_estimate_data
        if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
            symbol += ".NS"
        return await _run_blocking(get_estimate_data, symbol)
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/earnings/{symbol}")
async def get_earnings(symbol: str):
    """Fetch earnings data from Alpha Vantage (EPS history + estimates)."""
    try:
        from modules.alpha_vantage import AlphaVantageProvider, get_remaining_budget

        remaining = get_remaining_budget()
        if remaining < 2:
            return {"error": f"Alpha Vantage daily budget low ({remaining} calls remaining). Try again tomorrow.", "budget_remaining": remaining}

        av = AlphaVantageProvider()
        result = await _run_blocking(av.get_earnings_calendar, symbol)

        if not result:
            return {"error": f"No earnings data available for {symbol}", "source": "alpha_vantage"}

        result["symbol"] = symbol
        result["source"] = "alpha_vantage"
        result["budget_remaining"] = get_remaining_budget()
        return _json_safe_clean(result)
    except Exception as e:
        print(f"Earnings API Error: {e}")
        return {"error": str(e)}

@router.get("/api/revisions/{symbol}")
async def get_revisions(symbol: str):
    """Fetch analyst recommendations trend and score impact."""
    try:
        symbol = normalize_symbol(symbol)
        ticker = yf.Ticker(symbol)
        score_impact, sentiment = await _run_blocking(analyze_revisions, ticker)
        return {
            "symbol": symbol,
            "score_impact": score_impact,
            "sentiment": sentiment,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

