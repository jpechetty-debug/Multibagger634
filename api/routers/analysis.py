from fastapi import APIRouter
import json
import os
from datetime import datetime

import csv

from api.dependencies import (
    _run_blocking, _read_records, _json_safe_clean
)
from database import get_connection
from modules.symbol_utils import normalize_symbol

router = APIRouter()

@router.get("/api/reports/{symbol}")
async def get_stock_report_markdown(symbol: str):
    """Generate Analyst Report (Markdown)"""
    try:
        from report_generator import generate_analyst_report
        symbol = normalize_symbol(symbol)
        report = await generate_analyst_report(symbol)
        return {"content": report}
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/thesis/{symbol}")
async def get_llm_thesis(symbol: str):
    """Generate concise AI investment thesis via local Ollama."""
    try:
        from modules.llm_engine import generate_thesis
        import pandas as pd
        conn = get_connection()
        try:
            target = pd.read_sql("SELECT * FROM multibaggers WHERE symbol = ?", conn, params=(symbol,))
            if target.empty:
                return {"thesis": "Stock not found in database to generate thesis."}
            stock_data = target.iloc[0].to_dict()
        finally:
            conn.close()
            
        thesis = await _run_blocking(generate_thesis, stock_data)
        return {"thesis": thesis}
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/history/{symbol}")
def get_stock_history(symbol: str):
    """Fetch historical score data for a stock."""
    try:
        conn = get_connection() # Use get_connection instead of get_db_connection
        cursor = conn.cursor()
        
        # Normalize symbol
        if not symbol.endswith(".NS"):
            symbol = f"{symbol}.NS"
            
        cursor.execute("""
            SELECT as_of_date, score, price 
            FROM fundamentals_pit 
            WHERE symbol = ? 
            ORDER BY as_of_date ASC
        """, (symbol,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "date": row["as_of_date"],
                "score": row["score"],
                "price": row["price"]
            }
            for row in rows
        ]
    except Exception as e:
        print(f"History Error: {e}")
        return []

@router.get("/api/reports/html/{symbol}")
async def get_stock_report_html(symbol: str):
    """Serve Premium HTML Report with cache-busting."""
    try:
        from modules.html_report import generate_premium_html_report
        symbol = normalize_symbol(symbol)
        
        path = await generate_premium_html_report(symbol)
        if os.path.exists(path):
            from fastapi.responses import FileResponse
            return FileResponse(
                path, 
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache"
                }
            )
        return {"error": "Report generation failed"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/thesis_break")
async def get_thesis_break():
    """Fetch all thesis break statuses (upgraded: live engine with fallback)."""
    try:
        if os.path.exists("thesis_break.json"):
            with open("thesis_break.json", "r") as f:
                return json.load(f)
        from modules.thesis_monitor import check_all_thesis_breaks
        results = await _run_blocking(check_all_thesis_breaks)
        return {
            "timestamp": datetime.now().isoformat(),
            "signals_count": sum(1 for r in results if r["status"] == "THESIS_BREAK"),
            "status": "HEALTHY" if all(r["status"] in ("INTACT", "NO_THESIS", "NO_DATA") for r in results) else "ACTION_REQUIRED",
            "signals": results,
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/thesis_status/{symbol}")
async def get_thesis_status(symbol: str):
    """Fetch thesis status for a single stock."""
    try:
        from modules.thesis_monitor import check_thesis, get_thesis_summary
        if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
            symbol += ".NS"
        status = await _run_blocking(check_thesis, symbol)
        thesis = await _run_blocking(get_thesis_summary, symbol)
        result = status.to_dict()
        if thesis:
            result["thesis_detail"] = thesis
        return result
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/rejections")
def get_rejections():
    """Fetch latest 20 rejected trades from Black Box Recorder"""
    try:
        if not os.path.exists("rejected_trades.csv"):
            return []
        with open("rejected_trades.csv", "r", encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            return rows[-20:][::-1]
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/backtest-metrics")
async def get_backtest_metrics():
    """Fetch aggregate portfolio backtesting metrics."""
    import os
    try:
        if not os.path.exists("backtest_report.md"):
            return {"status": "pending"}
            
        metrics = {"status": "success"}
        with open("backtest_report.md", "r", encoding="utf-8") as f:
            for line in f:
                if "Average CAGR" in line:
                    metrics["cagr"] = line.split(":")[-1].replace("*", "").replace("%", "").strip()
                elif "Win Rate" in line:
                    metrics["win_rate"] = line.split(":")[-1].replace("*", "").replace("%", "").strip()
                elif "Max Drawdown" in line:
                    metrics["max_dd"] = line.split(":")[-1].replace("*", "").replace("%", "").strip()
                elif "Sharpe Ratio" in line:
                    metrics["sharpe"] = line.split(":")[-1].replace("*", "").strip()
                elif "Sortino Ratio" in line:
                    metrics["sortino"] = line.split(":")[-1].replace("*", "").strip()
                elif "Calmar Ratio" in line:
                    metrics["calmar"] = line.split(":")[-1].replace("*", "").strip()
                    
        return metrics
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/slippage_stats")
async def get_slippage_stats():
    """Fetch Execution Quality Metrics (Slippage Calibration)"""
    try:
        query = "SELECT * FROM slippage_metrics ORDER BY tier"
        data = await _run_blocking(_read_records, query)
        return _json_safe_clean(data)
    except Exception as e:
        return {"error": str(e)}

