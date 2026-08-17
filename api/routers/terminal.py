from fastapi import APIRouter
from typing import Dict, Any, List
# We mock most of these APIs to allow frontend to build out the structure,
# and will map them to real engines in subsequent iterations.

router = APIRouter()

@router.get("/api/overview")
async def get_overview() -> Dict[str, Any]:
    """Returns top-level overview metrics for the terminal."""
    return {
        "regime": {"state": "Bull Trend", "confidence": 82},
        "market_health": {
            "score": 75,
            "pct_above_20dma": 60,
            "pct_above_50dma": 55,
            "pct_above_200dma": 70,
            "new_highs": 120,
            "new_lows": 15
        },
        "top_sector": "Capital Goods",
        "cash_allocation": 15
    }

@router.get("/api/command_center")
async def get_command_center() -> Dict[str, Any]:
    """Returns the Command Center widget data."""
    return {
        "market_state": "Bull Trend (82%)",
        "recommended_action": "Deploy Capital",
        "cash_target": "15%",
        "best_factor": "Momentum",
        "best_sector": "Capital Goods",
        "top_idea": "TRENT"
    }

@router.get("/api/explain/{symbol}")
async def get_explainability(symbol: str) -> Dict[str, Any]:
    """Returns 4 layers of explainability for the drawer."""
    return {
        "symbol": symbol,
        "score": 92,
        "why_it_matters": {
            "rank": 3,
            "positives": ["Earnings Acceleration", "Sector Leadership"],
            "negatives": ["Expensive Valuation"]
        },
        "factor_contributions": {
            "quality": 26,
            "growth": 18,
            "momentum": 22,
            "valuation": 10,
            "risk": 7
        },
        "historical_evolution": [68, 74, 82, 92],
        "expected_behavior": {
            "30d_alpha": "+8.2%",
            "90d_alpha": "+15.7%"
        },
        "opportunity_score": 94,
        "compounder_score": 88,
        "discovery_score": 76
    }

@router.get("/api/discovery")
async def get_discovery() -> Dict[str, Any]:
    """Returns Discovery engine data."""
    return {
        "emerging_leaders": [{"symbol": "ZENTEC", "score": 82, "rs": "Rising"}],
        "rs_acceleration": [{"symbol": "KALYANKJIL", "rs_change": "+15"}],
        "earnings_acceleration": [{"symbol": "APARINDS", "pattern": "Q1 < Q2 < Q3 < Q4"}],
        "sector_breakouts": ["Capital Goods", "Pharma", "EMS"],
        "future_compounders": [{"symbol": "KPITTECH", "roce": 22, "sales_cagr": 25}]
    }

@router.get("/api/watchlist/events")
async def get_watchlist_events() -> List[Dict[str, Any]]:
    """Returns real-time watchlist events."""
    return [
        {"symbol": "TRENT", "event": "RS > 95"},
        {"symbol": "POLYCAB", "event": "Score +8"},
        {"symbol": "CGPOWER", "event": "Sector Rank Top 3"}
    ]

@router.get("/api/research/factors")
async def get_research_factors() -> Dict[str, Any]:
    return {
        "information_coefficient": [
            {"factor": "Momentum", "ic": 0.22},
            {"factor": "Quality", "ic": 0.14},
            {"factor": "Value", "ic": 0.02}
        ],
        "alpha_decay": {"7D": 0.05, "30D": 0.03, "90D": -0.01, "180D": -0.05},
        "rankings": ["Momentum", "Quality", "Growth", "Value"],
        "heatmap": {"Momentum": "Strong", "Value": "Weak", "Quality": "Neutral"}
    }

@router.get("/api/research/regimes")
async def get_research_regimes() -> Dict[str, Any]:
    return {
        "current_regime": {"name": "Bull Trend", "confidence": 83},
        "best_factors": [
            {"factor": "Momentum", "performance": 0.22},
            {"factor": "Quality", "performance": 0.08},
            {"factor": "Value", "performance": -0.02}
        ],
        "recommended_allocation": {"equity": 70, "cash": 20, "defensive": 10}
    }

@router.get("/api/research/alpha")
async def get_research_alpha() -> Dict[str, Any]:
    return {"status": "mock_alpha_data"}

@router.get("/api/research/attribution")
async def get_research_attribution() -> Dict[str, Any]:
    return {"status": "mock_attribution_data"}

@router.get("/api/market_intelligence")
async def get_market_intelligence() -> Dict[str, Any]:
    return {
        "market_breadth": "Improving",
        "sector_rotation": "Into Defensives",
        "new_highs": 85,
        "new_lows": 12,
        "regime_changes": "None recently"
    }
