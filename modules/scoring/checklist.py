def evaluate_checklist(data, best_roe, pe, prom_hold, value_gap):
    """
    Evaluates the 12-point Institutional Quality Checklist.
    Returns the checklist pass count and applied bonuses.
    """
    checklist_pass = 0
    checklist_total = 12
    
    # C1: Market Cap > 1,000 Cr (liquidity & stability)
    mcap_cr = data.get("Market_Cap_Cr")
    if mcap_cr is not None and mcap_cr > 1000:
        checklist_pass += 1
    # C2: Valuation  PE < 25 (reasonable price)
    if pe is not None and 0 < pe < 25:
        checklist_pass += 1
    # C3: Profitability  ROE > 17% (institutional threshold)
    if best_roe > 17:
        checklist_pass += 1
    # C4: Leverage  Debt/Equity between 0 and 1.0 (must have data)
    de_val = data.get("Debt_Equity")
    if de_val is not None and 0 <= de_val < 1.0:
        checklist_pass += 1
    # C5: Cash Quality  CFO/PAT > 1.0 (profits backed by cash)
    if data.get("CFO_PAT_Ratio", 0) > 1.0:
        checklist_pass += 1
    # C6: Momentum  between 0 and 25% drop from 52W high (must have data)
    down_pct = data.get("Down_From_52W_High%", -1)
    if 0 <= down_pct < 25:
        checklist_pass += 1
    # C7: Revenue Growth > 15% CAGR (Aggressive Growth Gate)
    sg = data.get("Sales_Growth_5Y%", 0) or data.get("Sales_Growth_TTM%", 0)
    if sg > 15:
        checklist_pass += 1
    # C8: Earnings Growth  EPS Growth positive
    eps_g = data.get("EPS_Growth%", 0)
    if eps_g > 0:
        checklist_pass += 1
    # C9: Promoter Conviction  Holding > 50% (skin in the game)
    if prom_hold > 50:
        checklist_pass += 1
    # C10: Financial Fortress  F-Score >= 6 (Piotroski quality)
    f_val_check = data.get("F_Score")
    if f_val_check is not None and f_val_check >= 6:
        checklist_pass += 1
    # C11: Profit Uptrend (Sovrenn)  both revenue AND earnings growing > 10%
    if sg > 10 and eps_g > 10:
        checklist_pass += 1
    # C12: Valuation Comfort (Sovrenn + Workflow Step 3)
    if value_gap > 0 or (pe is not None and 0 < pe < 20):
        checklist_pass += 1
        
    checklist_bonus = 5 if checklist_pass >= 11 else 0

    # Phase 4: CONTINUOUS CHECKLIST SPLINE
    if checklist_pass >= 9:
        checklist_penalty = (12 - checklist_pass) * 0.66
        current_ceiling = 80 + (checklist_pass - 9) * (20 / 3.0)
    else:
        checklist_penalty = 2.0 + ((9 - checklist_pass) / 9.0 * 18.0)
        current_ceiling = 40 + (checklist_pass / 9.0 * 40.0)

    return {
        "pass_count": checklist_pass,
        "total": checklist_total,
        "bonus": checklist_bonus,
        "penalty": checklist_penalty,
        "ceiling": current_ceiling
    }
