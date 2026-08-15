import numpy as np

def normalize_metric(value, min_val, max_val, invert=False):
    """
    Normalizes a metric to a 0-100 scale using a Sigmoid function.
    Replaces binary step cliffs with a smooth continuous gradient.
    """
    if value is None or not np.isfinite(value): return 0
    
    mid = (min_val + max_val) / 2.0
    span = float(max_val - min_val)
    if span == 0: span = 1e-5
    
    # Scale so min_val is approx at x=-3 (4.7%) and max_val at x=+3 (95%)
    x_scaled = (value - mid) / (span / 6.0)
    
    # Cap exponent to avoid overflow warnings
    x_scaled = max(-100, min(100, x_scaled))
    
    sigmoid_val = 1.0 / (1.0 + np.exp(-x_scaled))
    
    if invert:
        return (1.0 - sigmoid_val) * 100.0
    else:
        return sigmoid_val * 100.0

def normalize_zscore(value, mean, std, invert=False):
    """
    Normalizes a metric using Cross-Sectional Z-Score and a Sigmoid function.
    Provides robust scoring across different market regimes.
    """
    if value is None or not np.isfinite(value) or std is None or std == 0:
        return 0
    
    z = (value - mean) / std
    z = max(-4.0, min(4.0, z))
    
    # Sigmoid function, scaled so Z=2 is ~95%, Z=-2 is ~5%
    sigmoid_val = 1.0 / (1.0 + np.exp(-z * 1.5))
    
    if invert:
        return (1.0 - sigmoid_val) * 100.0
    else:
        return sigmoid_val * 100.0

def calculate_sector_medians(results):
    """Compute median ROE, Sales Growth, PE per sector for relative scoring."""
    sector_data = {}
    for stock in results:
        sector = stock.get("Sector", "Unknown")
        if sector == "Unknown":
            continue
        if sector not in sector_data:
            sector_data[sector] = {"roe": [], "growth": [], "pe": []}
        roe = stock.get("Avg_ROE_5Y%", 0) or stock.get("ROE%", 0) or 0
        growth = stock.get("Sales_Growth_5Y%", 0) or stock.get("Sales_Growth_TTM%", 0) or 0
        pe = stock.get("PE_Ratio", 0) or 0
        if roe != 0:
            sector_data[sector]["roe"].append(roe)
        if growth != 0:
            sector_data[sector]["growth"].append(growth)
        if pe > 0:
            sector_data[sector]["pe"].append(pe)
    
    medians = {}
    for sector, vals in sector_data.items():
        medians[sector] = {
            "median_roe": round(float(np.median(vals["roe"])), 1) if vals["roe"] else 15,
            "median_growth": round(float(np.median(vals["growth"])), 1) if vals["growth"] else 10,
            "median_pe": round(float(np.median(vals["pe"])), 1) if vals["pe"] else 20,
        }
    return medians

def get_stats(metric_name, fallback_min, fallback_max, cross_sectional_stats=None):
    if cross_sectional_stats and metric_name in cross_sectional_stats:
        return cross_sectional_stats[metric_name]
    return None

def apply_spline_cap(val, full_score_val, max_penalty_val, min_cap, name, disqualifiers, score_ceiling, invert=False):
    """
    Applies a continuous penalty spline instead of a hard cliff.
    If invert is False, higher is better. If invert is True, lower is better.
    Updates the score_ceiling and appends to disqualifiers if penalized.
    """
    if val is None or not np.isfinite(val):
        return score_ceiling

    # Calculate distance along the penalty spectrum (0.0 = no penalty, 1.0 = max penalty)
    if not invert:
        # Higher is better: e.g. ROE (full=15, max_penalty=0)
        if val >= full_score_val:
            return score_ceiling
        if val <= max_penalty_val:
            penalty_ratio = 1.0
        else:
            penalty_ratio = (full_score_val - val) / (full_score_val - max_penalty_val)
    else:
        # Lower is better: e.g. Debt/Equity (full=1.0, max_penalty=2.0)
        if val <= full_score_val:
            return score_ceiling
        if val >= max_penalty_val:
            penalty_ratio = 1.0
        else:
            penalty_ratio = (val - full_score_val) / (max_penalty_val - full_score_val)

    # Smooth the penalty using x^1.5 for a natural curve
    curve_ratio = penalty_ratio ** 1.5
    
    # Calculate what the cap should be (interpolate between 100 and min_cap)
    new_cap = 100 - (100 - min_cap) * curve_ratio
    
    # Cap cannot exceed the absolute minimum for this factor
    new_cap = max(min_cap, new_cap)
    
    # Only apply if it lowers the ceiling
    if new_cap < score_ceiling:
        if new_cap < 85: # Only log major penalties as disqualifiers
            disqualifiers.append(f"{name} Risk [{val:.1f}]")
        return new_cap
        
    return score_ceiling
