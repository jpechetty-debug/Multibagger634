import pandas as pd
import numpy as np
from dataclasses import dataclass, field


class TickerShim:
    """
    Lightweight shim that wraps DataSourceManager output to look like a yfinance Ticker.
    Allows fundamentals.py functions (calculate_piotroski_f_score, etc.) to work
    without modification while benefiting from the fallback chain.
    """
    financials: pd.DataFrame = field(default_factory=pd.DataFrame)
    balance_sheet: pd.DataFrame = field(default_factory=pd.DataFrame)
    cashflow: pd.DataFrame = field(default_factory=pd.DataFrame)
    quarterly_financials: pd.DataFrame = field(default_factory=pd.DataFrame)

# --- Utils ---

# --- V3.1: Data Quality Gate ---
_DATA_QUALITY_FIELDS = [
    'PE_Ratio', 'PEG_Ratio', 'ROE%', 'Avg_ROE_5Y%', 'Debt_Equity',
    'EPS_Growth%', 'Sales_Growth_5Y%', 'CFO_PAT_Ratio', 'F_Score', 'Market_Cap_Cr'
]
_DATA_QUALITY_WEIGHTS = {
    "PE_Ratio": 12,
    "PEG_Ratio": 6,
    "ROE%": 12,
    "Avg_ROE_5Y%": 10,
    "Debt_Equity": 8,
    "EPS_Growth%": 10,
    "Sales_Growth_5Y%": 12,
    "CFO_PAT_Ratio": 12,
    "F_Score": 8,
    "Market_Cap_Cr": 10,
}
_SOURCE_CONFIDENCE = {
    "pnsea": 1.00,
    "nsepython": 0.90,
    "yfinance": 0.75,
    "fallback_failed": 0.30,
    "unknown": 0.55,
}
_FETCH_CORE_FIELDS = [
    "Market_Cap_Cr",
    "PE_Ratio",
    "ROE%",
    "Debt_Equity",
    "Sales_Growth_TTM%",
    "CFO_PAT_Ratio",
]
_FETCH_CORE_FLAG_FIELDS = [
    "Market_Cap_Cr",
    "PE_Ratio",
    "ROE%",
    "F_Score",
    "Debt_Equity",
    "Sales_Growth_5Y%",
    "EPS_Growth%",
    "CFO_PAT_Ratio",
]
_INFO_BACKFILL_KEYS = [
    "marketCap",
    "trailingPE",
    "returnOnEquity",
    "debtToEquity",
    "earningsGrowth",
    "revenueGrowth",
    "bookValue",
    "trailingEps",
    "fiftyTwoWeekHigh",
    "fiftyTwoWeekLow",
    "sector",
    "industry",
]


def _is_missing_info_value(value):
    if value is None:
        return True
    if isinstance(value, str):
        return not bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _needs_info_backfill(info):
    if not isinstance(info, dict) or not info:
        return True
    if _is_missing_info_value(info.get("marketCap")):
        return True
    missing = sum(1 for key in _INFO_BACKFILL_KEYS if _is_missing_info_value(info.get(key)))
    return missing >= 5


def _merge_info(primary_info, fallback_info):
    merged = {}
    if isinstance(fallback_info, dict):
        for key, value in fallback_info.items():
            if not _is_missing_info_value(value):
                merged[key] = value
    if isinstance(primary_info, dict):
        for key, value in primary_info.items():
            if not _is_missing_info_value(value):
                merged[key] = value
    if _is_missing_info_value(merged.get("sector")) and not _is_missing_info_value(merged.get("industry")):
        merged["sector"] = merged.get("industry")
    return merged


def _is_finite_number(value):
    if value is None:
        return False
    if isinstance(value, (int, float, np.floating)):
        return np.isfinite(value)
    try:
        parsed = float(value)
        return np.isfinite(parsed)
    except Exception as e: 
        import logging
        logging.error(f"Error: {e}", exc_info=True)
        return False


def _is_present_metric(value):
    if not _is_finite_number(value):
        return False
    return float(value) != 0.0


def _freshness_score(price_age_days):
    if price_age_days is None:
        return 20.0
    if price_age_days <= 1:
        return 100.0
    if price_age_days <= 3:
        return 85.0
    if price_age_days <= 7:
        return 65.0
    if price_age_days <= 14:
        return 45.0
    return 20.0

def calculate_data_quality(data, *, zero_valuation_cap=20.0):
    """Weighted data quality score (0-100): completeness + source confidence + freshness."""
    flags = data.get("_dq_flags")
    if not isinstance(flags, dict):
        flags = {dq_field: _is_present_metric(data.get(dq_field)) for dq_field in _DATA_QUALITY_FIELDS}

    total_weight = float(sum(_DATA_QUALITY_WEIGHTS.values()) or 100.0)
    completeness_points = 0.0
    for dq_field in _DATA_QUALITY_FIELDS:
        if bool(flags.get(dq_field, False)):
            completeness_points += float(_DATA_QUALITY_WEIGHTS.get(dq_field, 0))
    completeness_score = (completeness_points / total_weight) * 100.0

    source = str(data.get("Data_Source", "unknown")).strip().lower()
    source_score = float(_SOURCE_CONFIDENCE.get(source, _SOURCE_CONFIDENCE["unknown"])) * 100.0

    price_age_days = data.get("Price_Age_Days")
    try:
        price_age_days = int(price_age_days) if price_age_days is not None else None
    except Exception as e: 
        import logging
        logging.error(f"Error: {e}", exc_info=True)
        price_age_days = None
    freshness = _freshness_score(price_age_days)

    final = (0.70 * completeness_score) + (0.20 * source_score) + (0.10 * freshness)
    valuation_missing = not _is_present_metric(data.get("Market_Cap_Cr")) and not _is_present_metric(data.get("PE_Ratio"))
    if valuation_missing:
        final = min(final, float(zero_valuation_cap))
    data["_dq_breakdown"] = {
        "completeness_score": round(completeness_score, 1),
        "source_score": round(source_score, 1),
        "freshness_score": round(freshness, 1),
        "zero_valuation_block": bool(valuation_missing),
    }
    data["_dq_blocked"] = bool(valuation_missing)
    return round(max(0.0, min(100.0, final)), 1)


def validate_fetch_payload(
    data,
    *,
    min_history_bars,
    min_core_fields,
    min_core_fields_by_source=None,
    sparse_sources=None,
    sparse_source_min_core=1,
    hard_block_zero_valuation=True,
    short_history_policy=None,
):
    """Hard fetch-validity gate before counting scan success and before DB write."""
    reasons = []
    soft_flags = []
    source = str(data.get("Data_Source", "unknown")).strip().lower()
    sparse_sources = {str(s).strip().lower() for s in (sparse_sources or []) if s}
    source_thresholds = {}
    for k, v in (min_core_fields_by_source or {}).items():
        if k is None:
            continue
        key = str(k).strip().lower()
        try:
            source_thresholds[key] = int(v)
        except Exception as e: 
            import logging
            logging.error(f"Error: {e}", exc_info=True)
            continue
    required_core_fields = int(source_thresholds.get(source, min_core_fields))
    required_history_bars = int(min_history_bars)
    short_history_eligible = False

    policy = short_history_policy or {}
    short_history_enabled = bool(policy.get("enabled", False))
    short_history_soft_flag = str(policy.get("soft_flag", "short_history_ipo")).strip() or "short_history_ipo"
    try:
        short_history_min_bars = int(policy.get("min_bars", min_history_bars))
    except Exception as e: 
        import logging
        logging.error(f"Error: {e}", exc_info=True)
        short_history_min_bars = int(min_history_bars)
    try:
        short_history_min_core_fields = int(policy.get("min_core_fields", required_core_fields))
    except Exception as e: 
        import logging
        logging.error(f"Error: {e}", exc_info=True)
        short_history_min_core_fields = int(required_core_fields)
    try:
        max_price_age_days = policy.get("max_price_age_days", None)
        short_history_max_price_age_days = int(max_price_age_days) if max_price_age_days is not None else None
    except Exception as e: 
        import logging
        logging.error(f"Error: {e}", exc_info=True)
        short_history_max_price_age_days = None

    price = data.get("Price")
    if not _is_finite_number(price) or float(price) <= 0:
        reasons.append("invalid_price")

    history_bars = int(data.get("History_Bars_1Y", 0) or 0)
    price_age_days = data.get("Price_Age_Days")
    try:
        price_age_days = int(price_age_days) if price_age_days is not None else None
    except Exception as e: 
        import logging
        logging.error(f"Error: {e}", exc_info=True)
        price_age_days = None

    core_present = 0
    flags = data.get("_dq_flags")
    if isinstance(flags, dict):
        core_present = sum(1 for key in _FETCH_CORE_FLAG_FIELDS if bool(flags.get(key, False)))
    else:
        for field in _FETCH_CORE_FIELDS:
            if _is_present_metric(data.get(field)):
                core_present += 1
        sector = str(data.get("Sector", "") or "").strip()
        if sector and sector.lower() != "unknown":
            core_present += 1

    if core_present < required_core_fields:
        if source in sparse_sources and core_present >= int(sparse_source_min_core):
            soft_flags.append("incomplete_fundamentals")
        else:
            reasons.append("missing_core_fields")

    if history_bars < int(min_history_bars):
        required_short_core = max(required_core_fields, short_history_min_core_fields)
        fresh_enough = (
            short_history_max_price_age_days is None
            or price_age_days is None
            or price_age_days <= short_history_max_price_age_days
        )
        if (
            short_history_enabled
            and history_bars >= short_history_min_bars
            and core_present >= required_short_core
            and fresh_enough
        ):
            short_history_eligible = True
            required_history_bars = short_history_min_bars
            if short_history_soft_flag not in soft_flags:
                soft_flags.append(short_history_soft_flag)
        else:
            reasons.append("short_history")

    if source == "fallback_failed" and core_present == 0:
        reasons.append("no_fundamentals")
    if hard_block_zero_valuation:
        has_mcap = _is_present_metric(data.get("Market_Cap_Cr"))
        has_pe = _is_present_metric(data.get("PE_Ratio"))
        if not has_mcap and not has_pe:
            reasons.append("zero_valuation_fields")

    return {
        "is_valid": len(reasons) == 0,
        "core_fields_present": core_present,
        "required_core_fields": required_core_fields,
        "required_history_bars": required_history_bars,
        "short_history_eligible": short_history_eligible,
        "reasons": reasons,
        "soft_flags": soft_flags,
        "primary_reason": reasons[0] if reasons else None,
    }
