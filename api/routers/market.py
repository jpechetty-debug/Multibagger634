from fastapi import APIRouter
from datetime import datetime

from api.dependencies import (
    regime_cache, movers_cache, regime_cache_lock, movers_cache_lock,
    _run_blocking, _cache_is_fresh, _cache_set, _cache_invalidate,
    REGIME_CACHE_TTL_SECONDS, MOVERS_CACHE_TTL_SECONDS
)
from modules.retry_utils import run_with_exponential_backoff

router = APIRouter()

@router.get("/api/market-calendar")
def get_market_calendar():
    """Returns valid trading days for the current year"""
    try:
        from modules.data_manager import data_manager
        # Convert date objects to string list for JSON serialization
        valid_days = [d.isoformat() for d in data_manager.valid_trading_days]
        return {"valid_trading_days": valid_days}
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/regime_status")
async def get_regime_status():
    """Fetch 3-Factor Regime Voting Status"""
    try:
        if _cache_is_fresh(regime_cache, REGIME_CACHE_TTL_SECONDS):
            return regime_cache["payload"]

        async with regime_cache_lock:
            if _cache_is_fresh(regime_cache, REGIME_CACHE_TTL_SECONDS):
                return regime_cache["payload"]
            from modules.market_data import MarketDataProvider
            import config
            provider = MarketDataProvider()
            data = await _run_blocking(provider.get_market_regime)

            # Check for Admin Override
            regime = data["regime"]
            if config.FORCED_REGIME:
                regime = config.FORCED_REGIME
                data["is_forced"] = True
            else:
                data["is_forced"] = False

            details = data.get("details", {})
            votes = data.get("votes", {})
           
            payload = {
                "regime": regime,
                "vix": details.get("vix", 0),
                "vix_threshold": 18.0,
                "votes": votes,
                "is_forced": data.get("is_forced", False),
                "details": details,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            }
            _cache_set(regime_cache, payload)
            return payload
    except Exception as e:
        cached_payload = regime_cache.get("payload")
        if cached_payload:
            stale_payload = dict(cached_payload)
            stale_payload["stale"] = True
            stale_payload["error"] = str(e)
            return stale_payload
        return {"error": str(e)}

@router.post("/api/admin/force_regime")
def force_regime(regime: str):
    """Manually force the regime for next scans. options: BULL, BEAR, SIDEWAYS, AUTO"""
    try:
        import config
        
        regime = regime.upper()
        if regime not in ['BULL', 'BEAR', 'SIDEWAYS', 'AUTO']:
            return {"error": "Invalid regime. Use BULL, BEAR, SIDEWAYS, or AUTO."}
            
        if regime == 'AUTO':
            config.FORCED_REGIME = None
            print("Regime override cleared. Resuming auto mode.")
        else:
            config.FORCED_REGIME = regime
            print(f"Regime forced to {regime} by administrator.")

        _cache_invalidate(regime_cache)
        return {"status": "success", "regime": regime}

    except Exception as e:
        return {"error": str(e)}

@router.get("/api/market_movers")
async def get_market_movers():
    """Fetch Global Top Gainers, Losers, and Actively Traded"""
    try:
        if _cache_is_fresh(movers_cache, MOVERS_CACHE_TTL_SECONDS):
            return movers_cache["payload"]

        async with movers_cache_lock:
            if _cache_is_fresh(movers_cache, MOVERS_CACHE_TTL_SECONDS):
                return movers_cache["payload"]
            from modules.alpha_vantage import AlphaVantageProvider
            av = AlphaVantageProvider()
            # Run synchronous and potentially rate-limited call in a separate thread
            movers = await run_with_exponential_backoff(
                lambda: _run_blocking(av.get_market_movers),
                context="alpha vantage market movers",
            )
            payload = movers or {"gainers": [], "losers": [], "active": []}
            _cache_set(movers_cache, payload)
            return payload


    except Exception as e:
        cached_payload = movers_cache.get("payload")
        if cached_payload:
            stale_payload = dict(cached_payload)
            stale_payload["stale"] = True
            stale_payload["error"] = str(e)
            return stale_payload
        return {"error": str(e)}

@router.get("/api/av-budget")
async def get_av_budget():
    """Check remaining Alpha Vantage API calls for today."""
    try:
        from modules.alpha_vantage import get_remaining_budget, _DAILY_LIMIT
        remaining = get_remaining_budget()
        return {
            "remaining": remaining,
            "daily_limit": _DAILY_LIMIT,
            "used": _DAILY_LIMIT - remaining,
        }
    except Exception as e:
        return {"error": str(e)}

