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
    # Startup: Check API_KEY auth configuration
    if not os.getenv("API_KEY"):
        print("⚠️  [SECURITY NOTICE] API_KEY environment variable is not set. Order placement (/api/order) will fail closed.")
    else:
        print("🔒 [SECURITY] API_KEY authentication configured for protected endpoints.")

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

import config
from fastapi.middleware.cors import CORSMiddleware

# ── CORS ── source from config, never wildcard in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

app.mount("/static", StaticFiles(directory="web-ui"), name="static")

def health_ping_loop():
    """Lightweight background loop to keep connections alive."""
    while True:
        try:
            print(f"[{datetime.now()}] Background health ping...")
            conn = get_connection()
            # Just do a trivial query to keep the DB connection alive if needed
            conn.execute("SELECT 1").fetchone()
            conn.close()
        except Exception as e:
            print(f"Health Ping Error: {e}")
        
        # Check every 6 hours
        time.sleep(6 * 3600)




if __name__ == "__main__":
    import uvicorn
    import os
    # Start Health Ping Thread
    audit_thread = threading.Thread(target=health_ping_loop, daemon=True)
    audit_thread.start()
    
    port = int(os.getenv("API_PORT", 9005))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    print(f"Starting Server... Access Dashboard at: http://{host}:{port}")
    uvicorn.run(
        "main:app", 
        host=host, 
        port=port
    )
