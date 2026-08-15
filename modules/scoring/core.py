import hashlib
import config
from research.conviction_engine import calculate_conviction_score
from .factors import evaluate_factors
from .disqualifiers import evaluate_disqualifiers
from .checklist import evaluate_checklist

def calculate_institutional_score(data, sector_boost=0, market_regime="Neutral", sector_medians=None, cross_sectional_stats=None):
    """
    Calculates a 'Composite Institutional Score' out of 100.
    Phase 23: Dynamic Factor Weights based on Market Regime.
    Uses Cross-Sectional Z-Scores for relative ranking when available.
    """
    mode = market_regime.lower() if market_regime else "balanced"
    if mode not in config.SCORING_WEIGHTS:
        mode = "balanced"
        
    weights = config.SCORING_WEIGHTS[mode]
    scoring_strategy = mode.capitalize()
    
    w_sales, w_roe, w_cfo, w_val, w_eps, w_fscore, w_de, w_mom = (
        weights["w_sales"], weights["w_roe"], weights["w_cfo"], weights["w_val"], 
        weights["w_eps"], weights["w_fscore"], weights["w_de"], weights["w_mom"]
    )
    
    # 1. Evaluate Core Factors
    factors_result = evaluate_factors(data, cross_sectional_stats)
    score_sales = factors_result["sales"]
    score_roe = factors_result["roe"]
    score_cfo = factors_result["cfo"]
    score_val = factors_result["val"]
    score_eps = factors_result["eps"]
    score_fscore = factors_result["fscore"]
    score_de = factors_result["de"]
    score_mom_combined = factors_result["mom"]
    
    roe_val = factors_result["raw_roe_val"]
    best_roe = factors_result["best_roe"]
    pe = factors_result["pe"]
    peg = factors_result["peg"]

    # 2. Dynamic Weight Redistribution
    available = []
    if data.get("Sales_Growth_5Y%", 0) != 0 or data.get("Sales_Growth_TTM%", 0) != 0:
        available.append(("sales", score_sales, w_sales))
    if roe_val != 0:
        available.append(("roe", score_roe, w_roe))
    if data.get("CFO_PAT_Ratio", 0) != 0:
        available.append(("cfo", score_cfo, w_cfo))
    if (pe is not None and pe > 0) or (peg is not None and peg > 0):
        available.append(("val", score_val, w_val))
    if data.get("EPS_Growth%", 0) != 0:
        available.append(("eps", score_eps, w_eps))
    available.append(("fscore", score_fscore, w_fscore))
    available.append(("de", score_de, w_de))
    available.append(("mom", score_mom_combined, w_mom))
    
    data_confidence = round((len(available) / 8) * 100, 1)
    
    if available:
        total_available_weight = sum(w for _, _, w in available)
        scale = 1.0 / total_available_weight if total_available_weight > 0 else 1.0
        base_score = sum(score * weight * scale for _, score, weight in available)
    else:
        base_score = 0
    
    factor_count = len(available)
    if factor_count < 6:
        data_multiplier = max(0.1, min(1.0, (factor_count / 6.0) ** 1.5))
        base_score *= data_multiplier
    
    est_adj = data.get("Estimate_Score_Adj", 0)
    base_score += est_adj
    
    # 3. Sector-Relative Bonus
    sg_val = data.get("Sales_Growth_5Y%", 0) or data.get("Sales_Growth_TTM%", 0) or 0
    stock_sector = data.get("Sector", "Unknown")
    if sector_medians and stock_sector in sector_medians:
        sm = sector_medians[stock_sector]
        sector_rel_bonus = 0
        if best_roe > sm["median_roe"] * 1.2:
            sector_rel_bonus += 3
        elif best_roe > 0 and best_roe < sm["median_roe"] * 0.5:
            sector_rel_bonus -= 5
        if sg_val > sm["median_growth"] * 1.2:
            sector_rel_bonus += 3
        elif sg_val > 0 and sg_val < sm["median_growth"] * 0.5:
            sector_rel_bonus -= 5
        sector_rel_bonus = max(-10, min(6, sector_rel_bonus))
        base_score += sector_rel_bonus
    
    # 4. General Bonuses
    MAX_BONUS = 15
    total_bonus = 0
    inflection_score = data.get("Earnings_Inflection_Score", 0) or 0
    if inflection_score >= 4: total_bonus += 8
    elif inflection_score >= 3: total_bonus += 5
    elif inflection_score >= 2: total_bonus += 3
    elif data.get("Earnings_Accel"): total_bonus += 2

    total_bonus += sector_boost
    
    value_gap = data.get("Value_Gap%", 0)
    if value_gap > 50: total_bonus += 10
    elif value_gap > 20: total_bonus += 5
        
    f_score_check = data.get("F_Score")
    if f_score_check is not None and f_score_check >= 8: total_bonus += 5
        
    if data.get("Technical_Signal") == "Bullish": total_bonus += 5
        
    rating = str(data.get("Analyst_Rating") or "").lower()
    upside = data.get("Analyst_Upside%", 0) or 0
    if "strong buy" in rating: total_bonus += 5
    elif "buy" in rating: total_bonus += 2
    if upside > 20: total_bonus += 5
        
    inst_hold = data.get("Inst_Holding%", 0) or 0
    prom_hold = data.get("Promoter_Holding%", 0) or 0
    if inst_hold > 20: total_bonus += 5
    elif inst_hold > 10: total_bonus += 2
    if prom_hold > 60: total_bonus += 3
        
    atr = data.get("ATR", 0) or 0
    price_val = data.get("Price", 1) or 1
    if price_val > 0:
        atr_pct = atr / price_val
        if atr_pct < 0.03: total_bonus += 2

    if pe is not None and 0 < pe < 15:
        avg_roe = data.get("Avg_ROE_5Y%", 0)
        if avg_roe > 15:
            pe_bonus = max(0, min(5, (15 - pe) * 0.5))
            roe_bonus = max(0, min(5, (avg_roe - 15) * 0.33))
            total_bonus += (pe_bonus + roe_bonus)

    # 5. Research Layer & Conviction
    stock_data_for_conviction = {
        "symbol": data.get("Symbol", ""),
        "sales_growth": data.get("Sales_Growth_5Y%", 0),
        "profit_growth": data.get("EPS_Growth%", 0),
        "roce": data.get("Avg_ROE_5Y%", 0),
        "debt_to_equity": data.get("Debt_Equity", 0),
        "promoter_holding": prom_hold,
        "pledge": 0
    }
    conviction = calculate_conviction_score(stock_data_for_conviction)
    if conviction['institutional_interest']:
        investor_count = len(conviction.get('investors', []))
        boost = min(10.0, 2.0 + (investor_count * 2.0))
        total_bonus += boost

    # 6. Evaluate Disqualifiers
    dq_best_roe = factors_result["dq_best_roe"]
    score_ceiling, disqualifiers, total_penalty, dq_bonus, factor_audit = evaluate_disqualifiers(
        data, factors_result, dq_best_roe, pe, prom_hold, inst_hold, value_gap, stock_sector
    )
    
    total_bonus += dq_bonus
    capped_bonus = min(total_bonus, MAX_BONUS)
    base_score += capped_bonus
    base_score -= total_penalty 

    # 7. Evaluate 12-Point Checklist
    checklist_result = evaluate_checklist(data, best_roe, pe, prom_hold, value_gap)
    checklist_pass = checklist_result["pass_count"]
    checklist_total = checklist_result["total"]
    
    base_score += checklist_result["bonus"]
    base_score -= checklist_result["penalty"]
    score_ceiling = min(score_ceiling, checklist_result["ceiling"])
    
    if checklist_pass < 9:
        disqualifiers.append(f"Institutional Quality Gate {checklist_pass}/{checklist_total}")

    final_score = min(base_score, score_ceiling)
    
    # 8. Deterministic Tie-Breaker
    symbol = str(data.get("Symbol", "")).strip().upper()
    sym_hash = int(hashlib.md5(symbol.encode("utf-8")).hexdigest(), 16) % 1000
    sym_epsilon = (sym_hash + 1) / 1000000.0
    
    if price_val > 0:
        atr_pct = atr / price_val
        atr_epsilon = max(0, 0.00899 - min(atr_pct, 0.00899))
    else:
        atr_epsilon = 0
    
    epsilon = atr_epsilon + sym_epsilon
    final_score += epsilon
    
    for dq in disqualifiers:
        factor_audit.append({"name": dq, "value": round(score_ceiling - 100, 1)})
    
    raw_score = round(base_score, 1)
    
    return {
        "total_score": round(max(0, min(final_score, 100.1)), 5),
        "raw_score": raw_score,
        "checklist_score": f"{checklist_pass}/{checklist_total}",
        "data_confidence": data_confidence,
        "conviction_score": conviction['conviction_score'],
        "conviction_boost": conviction['conviction_boost'],
        "institutional_interest": conviction['institutional_interest'],
        "super_investors": ", ".join(conviction['investors']),
        "scoring_strategy": scoring_strategy,
        "factor_penalties": factor_audit,
        "factor_breakdown": {
             "Fundamentals": round((score_sales*w_sales + score_roe*w_roe + score_cfo*w_cfo + score_eps*w_eps), 1),
             "Value": round((score_val*w_val), 1),
             "Risk": round((score_fscore*w_fscore + score_de*w_de), 1),
             "Momentum": round((score_mom_combined*w_mom), 1),
             "Smart_Money": 10 if conviction['institutional_interest'] else 0,
             "Sector": sector_boost
        }
    }
