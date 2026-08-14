from fastapi import APIRouter
import pandas as pd
import numpy as np
from datetime import datetime

from api.dependencies import (
    portfolio_tracker, risk_governor,
    regime_cache, _run_blocking, OrderRequest
)
from database import get_connection

router = APIRouter()

@router.get("/api/performance")
def get_performance():
    """Fetch Strategy Performance vs Benchmark"""
    return {
        "strategy": 12.4,
        "benchmark": 8.7,
        "alpha": 3.7,
        "win_rate": 68.2,
        "avg_hold": "47 Days"
    }

@router.post("/api/order")
async def place_order(order: OrderRequest):
    """Order lifecycle endpoint for paper execution (BUY/SELL)."""
    try:
        symbol = order.symbol.strip().upper()
        side = order.side.strip().upper()

        if not symbol:
            return {"status": "rejected", "error": "symbol is required"}

        if side not in {"BUY", "SELL"}:
            return {"status": "rejected", "error": "side must be BUY or SELL"}

        if "." not in symbol:
            symbol = f"{symbol}.NS"

        if side == "BUY":
            # Dynamic + static kill-switch checks.
            if order.current_vix is not None or order.drawdown_rate_weekly is not None:
                vix_for_check = order.current_vix if order.current_vix is not None else 0.0
                
                # Fetch dynamic threshold from regime cache
                dynamic_limit = None
                cached_regime = regime_cache.get("payload")
                if cached_regime and "details" in cached_regime:
                    dynamic_limit = cached_regime["details"].get("vix_relative_limit")
                    
                is_safe, message = risk_governor.check_kill_switch(
                    vix_for_check,
                    dynamic_threshold=dynamic_limit,
                    drawdown_rate_weekly=order.drawdown_rate_weekly,
                )
                if not is_safe:
                    risk_governor.log_rejected_trade(symbol, message, order.price)
                    return {
                        "status": "rejected",
                        "side": side,
                        "symbol": symbol,
                        "reason": message,
                    }

            # Pre-trade VaR budget gate.
            var_safe, var_message = risk_governor.validate_var_budget(
                order.projected_var_pct,
                order.max_var_pct,
            )
            if not var_safe:
                return {
                    "status": "rejected",
                    "side": side,
                    "symbol": symbol,
                    "reason": var_message,
                }

            # Correlation stress gate.
            adjusted_qty = order.quantity
            if order.portfolio_correlation is not None:
                corr_factor = risk_governor.validate_correlation_risk(
                    order.portfolio_correlation
                )
                if corr_factor <= 0:
                    return {
                        "status": "rejected",
                        "side": side,
                        "symbol": symbol,
                        "reason": "Correlation emergency de-risk triggered",
                    }
                adjusted_qty = max(1, int(round(order.quantity * corr_factor)))

            result = await _run_blocking(
                portfolio_tracker.log_entry,
                symbol,
                order.price,
                order.score,
                adjusted_qty,
            )

            # Record buy thesis for thesis break detection
            if result.get("status") != "rejected":
                try:
                    from modules.thesis_monitor import record_buy_thesis
                    # Fetch current fundamental data for thesis snapshot
                    def _fetch_thesis_data():
                        conn_t = get_connection()
                        try:
                            row = pd.read_sql(
                                "SELECT * FROM multibaggers WHERE symbol = ?",
                                conn_t, params=(symbol,)
                            )
                            return row.iloc[0].to_dict() if not row.empty else {}
                        finally:
                            conn_t.close()
                    stock_snapshot = await _run_blocking(_fetch_thesis_data)
                    if stock_snapshot:
                        await _run_blocking(
                            record_buy_thesis, symbol, stock_snapshot,
                            order.score, 0, "SIDEWAYS"
                        )
                except Exception as thesis_err:
                    print(f"Thesis recording skipped: {thesis_err}")
        else:
            result = await _run_blocking(
                portfolio_tracker.log_exit,
                symbol,
                order.price,
                order.reason,
            )

        if result.get("status") == "rejected":
            risk_governor.log_rejected_trade(symbol, result.get("reason", "Order rejected"), order.price)

        return {
            "status": result.get("status", "accepted"),
            "side": side,
            "symbol": symbol,
            "quantity": adjusted_qty if side == "BUY" else order.quantity,
            "price": order.price,
            "reason": result.get("reason", order.reason),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@router.get("/api/trades/open")
async def get_open_trades():
    try:
        df = await _run_blocking(portfolio_tracker.get_open_positions)
        if df.empty:
            return []
        clean_df = df.replace([np.inf, -np.inf], np.nan).replace({np.nan: None})
        return clean_df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/trades/history")
async def get_trade_history():
    try:
        df = await _run_blocking(portfolio_tracker.get_trade_history)
        if df.empty:
            return []
        clean_df = df.replace([np.inf, -np.inf], np.nan).replace({np.nan: None})
        return clean_df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}

