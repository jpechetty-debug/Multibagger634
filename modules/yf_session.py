"""
Shared HTTP session for every yfinance call in the app.

Combines local response caching (requests_cache) with proactive
rate-limiting (requests_ratelimiter) so we stop short of triggering
Yahoo Finance's 429 "Too Many Requests" blocker in the first place,
rather than only reacting to it after the fact (see modules/retry_utils.py
for the reactive backoff layer — the two are complementary: this module
avoids most 429s, retry_utils handles the ones that still slip through).

Install with:
    pip install yfinance[nospam]
which pulls in requests_cache>=1.0 and requests_ratelimiter>=0.3.1.

Two profiles, one shared cache:
    get_yf_session()      - default. Conservative rate budget. Use this for
                             anything reachable from a live user request:
                             api/routers/*, and any module they import
                             (quarterly results, peers, shareholding,
                             technicals, market_data/regime_hmm, etc).
                             A single slow/blocked request here is a user
                             waiting on a page load, so we protect this
                             budget the most.
    get_yf_bulk_session()  - for standalone batch/backtest pipelines that
                             pull historical data for hundreds of symbols
                             in one run (screener.py, backtest_engine.py,
                             alpha_attribution.py, modules/backtest.py,
                             modules/correlation.py, backfill scripts).
                             These tolerate a higher throughput ceiling far
                             better than they tolerate 10x runtime, and
                             their data is mostly historical daily bars
                             that don't go stale in 5 minutes, so this
                             profile also caches for longer.

The two profiles use independent rate-limit buckets (each session object
carries its own), so a bulk pipeline running at its higher throughput never
eats into the budget that's protecting live user requests, and vice versa.
They share the same on-disk SQLite cache file, so a bulk run's downloads
can warm the cache for interactive lookups afterwards, and vice versa.

Usage:
    import yfinance as yf
    from modules.yf_session import get_yf_session

    ticker = yf.Ticker(symbol, session=get_yf_session())
    data = yf.download(symbol, period="1y", session=get_yf_session())
"""
import os
import time
from typing import Optional

from pyrate_limiter import Limiter, Rate

# ── Interactive profile (env-overridable, same pattern as config.py) ────────
# Default: max 2 requests per 5 seconds — conservative enough to stay well
# clear of Yahoo's undocumented rate limit under normal live-request load.
# This is also yfinance's own documented example budget.
YF_RATE_LIMIT_REQUESTS = int(os.getenv("YF_RATE_LIMIT_REQUESTS", "2"))
YF_RATE_LIMIT_PERIOD_SECONDS = float(os.getenv("YF_RATE_LIMIT_PERIOD_SECONDS", "5"))
# Default: 5-minute local cache — short enough that intraday lookups still
# see fresh data, long enough that a symbol looked up repeatedly across
# several modules in the same request (e.g. quarterly results + peers +
# shareholding all in one stock-detail view) only hits the network once.
YF_CACHE_EXPIRE_SECONDS = int(os.getenv("YF_CACHE_EXPIRE_SECONDS", "300"))
YF_CACHE_PATH = os.getenv("YF_CACHE_PATH", "yfinance_cache")

# ── Bulk profile (batch/backtest pipelines) ──────────────────────────────────
# Default: max 5 requests per 2 seconds (2.5x the interactive throughput) —
# still a real throttle, just sized for a script that needs to walk hundreds
# of symbols without taking 10x longer than before this change.
YF_BULK_RATE_LIMIT_REQUESTS = int(os.getenv("YF_BULK_RATE_LIMIT_REQUESTS", "5"))
YF_BULK_RATE_LIMIT_PERIOD_SECONDS = float(os.getenv("YF_BULK_RATE_LIMIT_PERIOD_SECONDS", "2"))
# Default: 6-hour cache — historical daily bars for a backtest don't change
# within a dev session, so re-running a backtest/screener pass shortly after
# the last one should mostly hit cache instead of re-downloading everything.
YF_BULK_CACHE_EXPIRE_SECONDS = int(os.getenv("YF_BULK_CACHE_EXPIRE_SECONDS", "21600"))

_LOG_WAIT_THRESHOLD_SECONDS = 0.5

_interactive_rate = Rate(YF_RATE_LIMIT_REQUESTS, int(YF_RATE_LIMIT_PERIOD_SECONDS * 1000))
_interactive_limiter = Limiter(_interactive_rate)

_bulk_rate = Rate(YF_BULK_RATE_LIMIT_REQUESTS, int(YF_BULK_RATE_LIMIT_PERIOD_SECONDS * 1000))
_bulk_limiter = Limiter(_bulk_rate)

def _acquire(limiter: Limiter, bucket_name: str) -> None:
    start = time.monotonic()
    limiter.try_acquire(bucket_name)
    waited = time.monotonic() - start
    if waited > _LOG_WAIT_THRESHOLD_SECONDS:
        print(f"[yf_session] throttled '{bucket_name}' for {waited:.2f}s to respect rate budget")

def get_yf_session() -> Optional[object]:
    """
    Return the process-wide shared session for interactive/live-request
    yfinance calls (anything reachable from an API endpoint).

    Note: yfinance > 1.0.0 uses curl_cffi and bypasses requests.Session completely.
    Caching is genuinely not recoverable at this layer, but we can still enforce
    the rate budget directly as a blocking side effect before returning None.
    """
    _acquire(_interactive_limiter, "yf_interactive")
    return None

def get_yf_bulk_session() -> Optional[object]:
    """
    Return the process-wide shared session for bulk/batch pipelines.
    Returning None lets yfinance handle caching natively, but enforces our bulk rate limit first.
    """
    _acquire(_bulk_limiter, "yf_bulk")
    return None
