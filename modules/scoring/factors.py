from .utils import normalize_metric, normalize_zscore, get_stats

def evaluate_factors(data, cross_sectional_stats):
    """
    Evaluates individual fundamental factors and returns their scores.
    """
    # 1. Sales Growth
    sg_val = data.get("Sales_Growth_5Y%", 0) or data.get("Sales_Growth_TTM%", 0) or 0
    sales_stats = get_stats("Sales_Growth_5Y%", 0, 40, cross_sectional_stats)
    if sales_stats:
        score_sales = normalize_zscore(sg_val, sales_stats["mean"], sales_stats["std"])
    else:
        score_sales = normalize_metric(sg_val, 0, 40)

    # 2. ROE
    roe_5y = data.get("Avg_ROE_5Y%", 0)
    roe_current = data.get("ROE%", 0)
    profit_margin = data.get("Profit_Margin%", 0)
    if roe_5y > 0:
        roe_val = roe_5y
        best_roe = roe_5y
        roe_confidence = 1.0
    elif roe_current > 0:
        roe_val = roe_current
        best_roe = roe_current
        roe_confidence = 0.85
    elif profit_margin > 0:
        roe_val = profit_margin
        best_roe = profit_margin
        roe_confidence = 0.70
    else:
        roe_val = 0
        best_roe = 0
        roe_confidence = 0.0
    
    roe_stats = get_stats("Avg_ROE_5Y%", 10, 30, cross_sectional_stats)
    if roe_stats:
        score_roe = normalize_zscore(roe_val, roe_stats["mean"], roe_stats["std"]) * roe_confidence
    else:
        score_roe = normalize_metric(roe_val, 10, 30) * roe_confidence
    
    # 3. CFO / PAT
    cfo_stats = get_stats("CFO_PAT_Ratio", 0.5, 1.5, cross_sectional_stats)
    cfo_val = data.get("CFO_PAT_Ratio", 0)
    if cfo_stats:
        score_cfo = normalize_zscore(cfo_val, cfo_stats["mean"], cfo_stats["std"])
    else:
        score_cfo = normalize_metric(cfo_val, 0.5, 1.5)
    
    # 4. Valuation
    pe = data.get("PE_Ratio")
    peg = data.get("PEG_Ratio")
    pe_stats = get_stats("PE_Ratio", 15, 60, cross_sectional_stats)
    peg_stats = get_stats("PEG_Ratio", 0.8, 2.5, cross_sectional_stats)
    
    if pe_stats and pe is not None and pe > 0:
        score_pe = normalize_zscore(pe, pe_stats["mean"], pe_stats["std"], invert=True)
    else:
        score_pe = normalize_metric(pe, 15, 60, invert=True) if (pe is not None and pe > 0) else 0
        
    if peg_stats and peg is not None and peg > 0:
        score_peg = normalize_zscore(peg, peg_stats["mean"], peg_stats["std"], invert=True)
    else:
        score_peg = normalize_metric(peg, 0.8, 2.5, invert=True) if (peg is not None and peg > 0) else 0

    if score_pe > 0 and score_peg > 0:
        score_val = (score_pe * 0.5) + (score_peg * 0.5)
    elif score_pe > 0:
        score_val = score_pe 
    else:
        score_val = score_peg
    
    # 5. EPS Growth
    eps_stats = get_stats("EPS_Growth%", 5, 30, cross_sectional_stats)
    eps_val = data.get("EPS_Growth%", 0)
    if eps_stats:
        score_eps = normalize_zscore(eps_val, eps_stats["mean"], eps_stats["std"])
    else:
        score_eps = normalize_metric(eps_val, 5, 30)
    
    # 6. F-Score
    f_score_val = data.get("F_Score")
    if f_score_val is None: f_score_val = 0
    score_fscore = (f_score_val / 9.0) * 100
    
    # 7. Debt / Equity
    de_val = data.get("Debt_Equity", 0)
    de_stats = get_stats("Debt_Equity", 0, 1.0, cross_sectional_stats)
    if "Bank" in data.get("Sector", "") or "Financial" in data.get("Sector", ""):
        score_de = 80 
    else:
        if de_stats:
            score_de = normalize_zscore(de_val, de_stats["mean"], de_stats["std"], invert=True)
        else:
            score_de = normalize_metric(de_val, 0, 1.0, invert=True)
        
    # 8. Momentum
    down_from_high = data.get("Down_From_52W_High%", 0)
    price = data.get("Price", 0) or 0
    mom_stats = get_stats("Down_From_52W_High%", 0, 40, cross_sectional_stats)
    if mom_stats and price > 0:
        score_mom_tech = normalize_zscore(down_from_high, mom_stats["mean"], mom_stats["std"], invert=True)
    else:
        score_mom_tech = normalize_metric(down_from_high, 0, 40, invert=True) if price > 0 else 0
    
    rs_rating = data.get("RS_Rating")
    if rs_rating is None: rs_rating = 0
    if rs_rating > 1.2: score_rs = 100
    elif rs_rating > 1.0: score_rs = 75
    elif rs_rating > 0.8: score_rs = 50
    else: score_rs = 25
    
    score_mom_combined = (score_mom_tech * 0.5) + (score_rs * 0.5)
    
    # Calculate best_roe for disqualifiers (can be negative)
    roe_5y_raw = data.get("Avg_ROE_5Y%", 0)
    roe_curr_raw = data.get("ROE%", 0)
    dq_best_roe = roe_5y_raw if roe_5y_raw != 0 else roe_curr_raw

    return {
        "sales": score_sales,
        "roe": score_roe,
        "cfo": score_cfo,
        "val": score_val,
        "eps": score_eps,
        "fscore": score_fscore,
        "de": score_de,
        "mom": score_mom_combined,
        "raw_roe_val": roe_val,
        "best_roe": best_roe,
        "dq_best_roe": dq_best_roe,
        "pe": pe,
        "peg": peg
    }
