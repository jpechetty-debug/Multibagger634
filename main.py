import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import socket
import threading
import time

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import pandas as pd
import yfinance as yf
from modules.yf_session import get_yf_session

from database import get_connection
from modules.retry_utils import run_with_exponential_backoff
from api.dependencies import (
    manager, _run_blocking, _run_ticker_blocking,
    _run_sqlite_write_with_retry, _run_sqlite_write_with_retry_sync,
    _read_records, _json_safe_clean
)

socket.setdefaulttimeout(20.0)

# Background Tasks and Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Check API_KEY auth configuration
    if not os.getenv("API_KEY"):
        print("[SECURITY NOTICE] API_KEY environment variable is not set. Order placement (/api/order) will fail closed.")
    else:
        print("[SECURITY] API_KEY authentication configured for protected endpoints.")

    # Startup: Initialize Redis Pub/Sub for WebSockets
    await manager.init_redis()
    
    yield
    
    # Shutdown
    if manager.pubsub:
        await manager.pubsub.aclose()
    if manager.redis_client:
        await manager.redis_client.aclose()

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
from api.routers import market, analysis, trading, screener, fundamentals, technicals, system, terminal

app.include_router(market.router, tags=["Market"])
app.include_router(analysis.router, tags=["Analysis"])
app.include_router(trading.router, tags=["Trading"])
app.include_router(screener.router, tags=["Screener"])
app.include_router(fundamentals.router, tags=["Fundamentals"])
app.include_router(technicals.router, tags=["Technicals"])
app.include_router(system.router, tags=["System"])
app.include_router(terminal.router, tags=["Terminal"])



# Serves the built frontend (web-ui/dist, produced by `npm run build` — see
# the Dockerfile's web-build stage for the production build). html=True
# means a request to "/" automatically serves dist/index.html, and
# /assets/... resolves to the built JS/CSS. The api routers registered
# above still take priority for /api/* and /ws/* since they were added
# first — this mount is intentionally the last route added. Note this does
# NOT do SPA-style fallback for arbitrary deep paths (e.g. /some/route
# 404s rather than serving index.html) — fine today since the UI uses
# in-page tab state rather than client-side path routing; revisit if that
# changes.
app.mount("/", StaticFiles(directory="web-ui/dist", html=True), name="static")

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
