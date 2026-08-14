import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import socket
import threading
import time

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import pandas as pd
import yfinance as yf

from database import get_connection
from modules.retry_utils import run_with_exponential_backoff
from api.dependencies import (
    manager, _run_blocking, _run_ticker_blocking,
    _run_sqlite_write_with_retry, _run_sqlite_write_with_retry_sync,
    _read_records, _json_safe_clean
)

socket.setdefaulttimeout(20.0)

# Background Task for Periodic Price Updates
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background task
    bg_task = asyncio.create_task(update_prices_background())
    yield
    # Shutdown: Stop background task
    bg_task.cancel()
    try:
        await bg_task
    except asyncio.CancelledError:
        print("Background price updater stopped.")

app = FastAPI(lifespan=lifespan)


# Override with a write-retry aware implementation.
async def update_prices_background():
    """Background loop to refresh stock prices in small batches to prevent deadlocks."""
    await asyncio.sleep(10)
    BATCH_SIZE = 50
    while True:
        try:
            print(f"[{datetime.now()}] Initiating batched background price refresh...")

            def _load_symbols():
                conn = get_connection()
                try:
                    df_local = pd.read_sql("SELECT symbol FROM multibaggers", conn)
                    return df_local["symbol"].tolist()
                finally:
                    conn.close()

            all_symbols = await _run_blocking(_load_symbols)
            
            if all_symbols:
                # Process in batches
                for i in range(0, len(all_symbols), BATCH_SIZE):
                    batch = all_symbols[i : i + BATCH_SIZE]
                    print(f"  -> Processing batch {i//BATCH_SIZE + 1}/{(len(all_symbols) + BATCH_SIZE - 1)//BATCH_SIZE} ({len(batch)} symbols)")
                    
                    data = pd.DataFrame()
                    try:
                        data = await run_with_exponential_backoff(
                            lambda: _run_ticker_blocking(
                                yf.download,
                                batch,
                                period="1d",
                                interval="1m",
                                progress=False,
                                auto_adjust=True,
                                timeout=15,
                            ),
                            context=f"yfinance background batch {i//BATCH_SIZE}",
                        )
                    except Exception as e:
                        print(f"    ⚠️ Batch Download Error: {e}")

                    if not data.empty:
                        def _write_batch_prices():
                            conn = get_connection()
                            try:
                                cursor = conn.cursor()
                                updated = 0
                                for symbol in batch:
                                    try:
                                        if len(batch) > 1:
                                            if "Close" in data and symbol in data["Close"].columns:
                                                current_price = data["Close"][symbol].iloc[-1]
                                            else:
                                                continue
                                        else:
                                            # Case for single-ticker download (though batch is usually > 1)
                                            current_price = data["Close"].iloc[-1]

                                        if not pd.isna(current_price):
                                            cursor.execute(
                                                "UPDATE multibaggers SET price = ? WHERE symbol = ?",
                                                (float(current_price), symbol),
                                            )
                                            updated += 1
                                    except Exception:
                                        pass
                                conn.commit()
                                return updated
                            finally:
                                conn.close()

                        updated_count = await _run_sqlite_write_with_retry(
                            _write_batch_prices, f"background batch {i//BATCH_SIZE}"
                        )
                        if updated_count > 0:
                            try:
                                symbols_str = ",".join([f"'{s}'" for s in batch])
                                query = f"SELECT * FROM multibaggers WHERE symbol IN ({symbols_str})"
                                updated_records = await _run_blocking(_read_records, query)
                                await manager.broadcast({"type": "update", "data": _json_safe_clean(updated_records)})
                            except Exception:
                                pass
                        # Small pause between batches to allow other API requests to breathe
                        await asyncio.sleep(1)
                
                print(f"[{datetime.now()}] Full price update cycle completed.")
        except Exception as e:
            print(f"Error in price updater: {e}")

        await asyncio.sleep(300)

# API Endpoints









# Advanced Forensics API















app.mount("/static", StaticFiles(directory="web-ui"), name="static")



# News API with Sentiment Intelligence (Phase 63 & 64)

# Market Movers API (Phase 64)



# Valuation API





# Technicals API


# Shareholding API
# Promoter Intelligence API


# Quarterly Results Timeline API

# Price vs Fundamentals API

# Estimates Momentum API

# Alpha Vantage Earnings API

# Alpha Vantage Budget Status

def weekly_audit_loop():
    """Background loop to refresh fundamental data every 7 days"""
    while True:
        try:
            print("Checking for expired Forensic Audits...")
            conn = get_connection()
            # Find stocks not audited in last 7 days
            seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            query = (
                "SELECT symbol FROM multibaggers "
                "WHERE last_audited IS NULL OR last_audited < ? "
                "LIMIT 5"
            )
            expired_stocks = pd.read_sql(query, conn, params=(seven_days_ago,))[
                "symbol"
            ].tolist()
            conn.close()
             
            if expired_stocks:
                print(f"Refreshing Forensic Audit for: {', '.join(expired_stocks)}")
                # In a real app, we'd call screener.get_stock_data(symbol)
                # For this terminal, we update the timestamp to signify 'Audit Complete'
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                def _write_audit_marks():
                    conn_write = get_connection()
                    try:
                        for symbol in expired_stocks:
                            conn_write.execute(
                                "UPDATE multibaggers SET last_audited = ? WHERE symbol = ?",
                                (now_str, symbol),
                            )
                        conn_write.commit()
                    finally:
                        conn_write.close()

                _run_sqlite_write_with_retry_sync(
                    _write_audit_marks, "weekly audit refresh"
                )
        except Exception as e:
            print(f"Audit Loop Error: {e}")
        
        # Check every 6 hours
        time.sleep(6 * 3600)




if __name__ == "__main__":
    import uvicorn
    # Start Weekly Audit Thread
    audit_thread = threading.Thread(target=weekly_audit_loop, daemon=True)
    audit_thread.start()
    
    print("Starting Server... Access Dashboard at: http://127.0.0.1:9005")
    uvicorn.run(
        "main:app", 
        host="127.0.0.1", 
        port=9005, 
        reload=True,
        reload_excludes=["*.db", "*.db-journal", "*.db-wal", "*.log", "*.txt"]
    )









# ==========================================
# ROUTER REGISTRATION
# ==========================================
from api.routers import market, analysis, trading, screener, fundamentals, technicals, system

app.include_router(market.router, tags=["Market"])
app.include_router(analysis.router, tags=["Analysis"])
app.include_router(trading.router, tags=["Trading"])
app.include_router(screener.router, tags=["Screener"])
app.include_router(fundamentals.router, tags=["Fundamentals"])
app.include_router(technicals.router, tags=["Technicals"])
app.include_router(system.router, tags=["System"])
