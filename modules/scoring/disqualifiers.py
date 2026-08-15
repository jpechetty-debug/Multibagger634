from .utils import apply_spline_cap
import config

def evaluate_disqualifiers(data, factor_scores, best_roe, pe, prom_hold, inst_hold, value_gap, stock_sector):
    """
    Evaluates Disqualifiers (D1-D16) and returns the resulting score ceiling and audit factors.
    """
    score_ceiling = 100.0
    disqualifiers = []
    factor_audit = []
    total_penalty = 0
    total_bonus = 0

    # Helper wrapper
    def _spline(val, full, max_pen, min_cap, name, invert=False):
        nonlocal score_ceiling
        score_ceiling = apply_spline_cap(val, full, max_pen, min_cap, name, disqualifiers, score_ceiling, invert=invert)

    # D1 & D10: ROE Spline
    _spline(best_roe, 15.0, 0.0, 60, "ROE Decay Spline")
    if best_roe < 0:
        _spline(best_roe, 0.0, -15.0, 50, "Value Destruction Spline")
        
    # D2 & D11: Revenue Growth Spline
    sg_check = data.get("Sales_Growth_5Y%", 0) or data.get("Sales_Growth_TTM%", 0)
    if sg_check is not None:
        _spline(sg_check, 10.0, -5.0, 60, "Growth Decay Spline")
        if sg_check < -5:
            _spline(sg_check, -5.0, -25.0, 50, "Declining Revenue Spline")

    # D3: Extreme ROE anomaly
    if best_roe is not None and best_roe > 100:
        _spline(best_roe, 100.0, 250.0, 45, "Anomalous ROE Risk", invert=True)
    
    # D4: Profit margin spline
    pm = data.get("Profit_Margin%", 0)
    if pm is not None:
        _spline(pm, 10.0, -5.0, 60, "Margin Decay Spline")
    
    # D5: F-Score quality mismatch
    f_score_val = data.get("F_Score", 0) or 0
    if f_score_val <= 4:
        cap = 70 + (f_score_val * 5.9)
        if cap < score_ceiling:
            score_ceiling = cap
            disqualifiers.append(f"Quality Floor Spline (F:{f_score_val})")
    
    # D6: Overvaluation Spline
    if value_gap < 0:
        _spline(value_gap, 0.0, -70.0, 65, "Overvaluation Spline")
        
    # D8: Cash Flow conversion
    cfo_pat = data.get("CFO_PAT_Ratio", 0)
    if cfo_pat is not None:
        _spline(cfo_pat, 0.8, 0.0, 60, "Cash Quality Spline")
    
    # D9: Governance Risk
    if prom_hold > 0 and inst_hold is not None:
        if prom_hold < 30 and inst_hold < 10:
            _spline(prom_hold, 30.0, 10.0, 65, "Anchor Investor Spline")
            
    # D12: EPS Growth Spline
    eps_check = data.get("EPS_Growth%", 0)
    if eps_check is not None:
        _spline(eps_check, 10.0, -10.0, 65, "EPS Decay Spline")

    # D13: Multi-Dimension Quality Gate
    factor_keys = ["sales", "roe", "cfo", "val", "eps", "fscore", "de", "mom"]
    avg_quality = sum(factor_scores[k] for k in factor_keys) / len(factor_keys)
    _spline(avg_quality, 50.0, 30.0, 55, "Lopsided Profile Spline")
    
    # D14: Cyclicality Guard
    CYCLICAL_SECTORS = {"Energy", "Basic Materials", "Utilities"}
    if stock_sector in CYCLICAL_SECTORS:
        if best_roe > 0 and pe is not None and pe > 0:
            cycle_risk = best_roe / pe
            _spline(cycle_risk, 2.0, 5.0, 65, "Cyclical Peak Spline", invert=True)
    
    # D15: Promoter Behaviour Intelligence
    try:
        from modules.promoter_intel import calculate_promoter_score
        _prom_result = calculate_promoter_score(data.get("Symbol", ""))
        if _prom_result and _prom_result.get("is_disqualified"):
            score_ceiling = min(score_ceiling, 60)
            disqualifiers.append("D15: Heavy Insider Sell-Off")
            factor_audit.append({"name": "D15: Heavy Insider Sell-Off", "value": -40})
        _prom_adj = _prom_result.get("score_adjustment", 0)
        if _prom_adj > 0:
            total_bonus += _prom_adj
            factor_audit.append({"name": "Promoter Buying Boost", "value": _prom_adj})
        elif _prom_adj < 0:
            total_penalty += abs(_prom_adj)
            factor_audit.append({"name": "Promoter Selling Penalty", "value": _prom_adj})
    except Exception:
        pass
    
    # D16: Estimate Momentum
    try:
        from modules.estimates import get_estimate_data
        disable_av = getattr(config, 'FULL_SCAN_DISABLE_ALPHA_VANTAGE', True)
        _est_result = get_estimate_data(data.get("Symbol", ""), allow_alpha_vantage=not disable_av)
        _est_mom = _est_result.get("momentum", {})
        if _est_mom.get("is_disqualified"):
            score_ceiling = min(score_ceiling, 55)
            disqualifiers.append("D16: Estimate Collapse (3Q consecutive downgrades)")
            factor_audit.append({"name": "D16: Estimate Collapse", "value": -45})
        _est_cap = _est_mom.get("score_cap")
        if _est_cap is not None:
            score_ceiling = min(score_ceiling, _est_cap)
            disqualifiers.append(f"Earnings Miss Streak (cap {_est_cap})")
            factor_audit.append({"name": "Earnings Miss Streak", "value": -(100-_est_cap)})
        _est_adj = _est_mom.get("score_adjustment", 0)
        if _est_adj > 0:
            total_bonus += _est_adj
            factor_audit.append({"name": "Estimate Momentum Bonus", "value": _est_adj})
        elif _est_adj < 0:
            total_penalty += abs(_est_adj)
            factor_audit.append({"name": "Estimate Downgrade Penalty", "value": _est_adj})
    except Exception:
        pass

    # Basic Penalties (P1-P3 & Volatility)
    price = data.get("Price", 1) or 1
    atr = data.get("ATR", 0) or 0
    if price > 0:
        atr_pct = atr / price
        if atr_pct > 0.07:
            total_penalty += 2
            factor_audit.append({"name": "High Volatility", "value": -2})
        if atr_pct > 0.10:
            total_penalty += 5
            factor_audit.append({"name": "Extreme Volatility", "value": -5})

    sales_5y = data.get("Sales_Growth_5Y%", 0)
    sales_ttm = data.get("Sales_Growth_TTM%", 0)
    if sales_5y < 0 and sales_ttm < 0:
        total_penalty += 5
        factor_audit.append({"name": "Declining Revenue (Long & Short)", "value": -5})
    elif sales_5y < 0 or sales_ttm < 0:
        total_penalty += 3
        factor_audit.append({"name": "Declining Revenue (Partial)", "value": -3})

    if pe is not None and pe > 80:
        total_penalty += 5
        factor_audit.append({"name": "Extreme Overvaluation", "value": -5})
    elif pe is not None and pe > 60:
        total_penalty += 3
        factor_audit.append({"name": "High Overvaluation", "value": -3})

    if prom_hold > 0 and prom_hold < 20:
        total_penalty += 5
        factor_audit.append({"name": "Low Promoter Holding (<20%)", "value": -5})
    elif prom_hold > 0 and prom_hold < 30:
        total_penalty += 2
        factor_audit.append({"name": "Low Promoter Holding (<30%)", "value": -2})

    return score_ceiling, disqualifiers, total_penalty, total_bonus, factor_audit
