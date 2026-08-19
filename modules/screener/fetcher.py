import pandas as pd
import numpy as np
import asyncio
from modules.fundamentals import (
    calculate_piotroski_f_score, 
    check_earnings_inflection,
    calculate_current_roe,
    calculate_recent_sales_growth,
    calculate_roce,
    calculate_median_pat_growth
)
from modules.estimates import get_estimate_data
from modules.data_manager import DataManager, data_manager
from modules.sector_mapping import get_refined_sector
from modules.technicals import calculate_rsi, calculate_macd, calculate_bollinger_bands, calculate_atr, calculate_momentum_features
from modules.risk import calculate_risk_params, calculate_trade_setup
from .data_quality import _merge_info, _needs_info_backfill, TickerShim


async def get_stock_data(ticker_symbol, dm=None, allow_alpha_vantage=True, include_quarterly=True):
    """
    Fetches comprehensive fundamental and technical data for a stock.
    """
    try:
        # Initialize variables
        sales_growth = 0
        roe = 0
        peg_ratio = 100
        debt_equity = 0
        eps_growth = 0
        
        # --- Fetch data via DataManager (yfinance -> PNSEA -> nsepython fallback) ---
        _dm = dm if dm else data_manager
        raw = await _dm.async_fetch_fundamentals(ticker_symbol)
        if not isinstance(raw, dict):
            return {"Symbol": ticker_symbol, "_fetch_error": "fetch_failed", "Data_Source": "unknown"}
        info = raw.get("info", {}) if isinstance(raw.get("info", {}), dict) else {}
        data_source = str(raw.get("source", "unknown"))

        # Build a TickerShim so fundamentals.py functions keep working unchanged
        ticker = TickerShim(
            financials=raw.get("financials", pd.DataFrame()),
            balance_sheet=raw.get("balance_sheet", pd.DataFrame()),
            cashflow=raw.get("cash_flow", pd.DataFrame()),
        )

        # Quarterly financials: fetch separately (not part of fundamentals bundle)
        info_backfill = {}
        if include_quarterly or _needs_info_backfill(info):
            try:
                import yfinance as _yf
                _t = _yf.Ticker(ticker_symbol, session=get_yf_bulk_session())
                if include_quarterly:
                    ticker.quarterly_financials = _t.quarterly_financials
                else:
                    ticker.quarterly_financials = pd.DataFrame()
                if _needs_info_backfill(info):
                    candidate_info = _t.info
                    if isinstance(candidate_info, dict):
                        info_backfill = candidate_info
            except Exception as e: 
                import logging
                logging.error(f"Error: {e}", exc_info=True)
                ticker.quarterly_financials = pd.DataFrame()
        else:
            ticker.quarterly_financials = pd.DataFrame()
        info = _merge_info(info, info_backfill)

        # --- Technicals (Price & Moving Averages) ---
        hist = await _dm.fetch_history(ticker_symbol, period="1y")
        if hist.empty:
            return {
                "Symbol": ticker_symbol,
                "_fetch_error": "no_price_history",
                "Data_Source": data_source,
            }

        history_bars = int(len(hist))
        try:
            last_price_ts = pd.to_datetime(hist.index[-1]).to_pydatetime()
            last_price_date = last_price_ts.date()
            price_age_days = max((date.today() - last_price_date).days, 0)
            last_price_date_iso = last_price_date.isoformat()
        except Exception as e: 
            import logging
            logging.error(f"Error: {e}", exc_info=True)
            price_age_days = None
            last_price_date_iso = None
        
        current_price = hist['Close'].iloc[-1]
        if not _is_finite_number(current_price) or float(current_price) <= 0:
            return {
                "Symbol": ticker_symbol,
                "_fetch_error": "invalid_price",
                "Data_Source": data_source,
                "History_Bars_1Y": history_bars,
                "Last_Price_Date": last_price_date_iso,
                "Price_Age_Days": price_age_days,
            }
        
        # Relative Strength (RS)
        # Compare 6M Stock Return vs Nifty 6M Return
        rs_rating = 0
        try:
            if len(hist) > 126:
                price_6m_ago = hist['Close'].iloc[-126]
                stock_6m_ret = ((current_price - price_6m_ago) / price_6m_ago) * 100
                nifty_6m_ret = get_benchmark_return()
                
                # RS Ratio
                if nifty_6m_ret != 0 and price_6m_ago != 0:
                    rs_rating = round(stock_6m_ret / nifty_6m_ret, 2)
                else:
                    rs_rating = 1.0 if stock_6m_ret > 0 else 0.0
            else:
                rs_rating = 0
        except Exception as e: 
            import logging
            logging.error(f"Error: {e}", exc_info=True)
            rs_rating = 0
        
        dma_200 = hist['Close'].tail(200).mean() if len(hist) >= 200 else hist['Close'].mean()
        dma_50 = hist['Close'].tail(50).mean() if len(hist) >= 50 else hist['Close'].mean()
        
        rsi_series = calculate_rsi(hist['Close'])
        rsi_current = rsi_series.iloc[-1]
        
        # --- Phase 6: Advanced Technicals ---
        # --- Phase 12: Momentum Ranking Features ---
        mom_features = calculate_momentum_features(hist)
        
        # MACD
        macd, signal, macd_hist = calculate_macd(hist['Close'])
        macd_val = macd.iloc[-1]
        signal_val = signal.iloc[-1]
        macd_bullish = macd_val > signal_val
        
        # Bollinger Bands
        bb_upper, bb_mid, bb_lower = calculate_bollinger_bands(hist['Close'])
        bb_up_val = bb_upper.iloc[-1]
        bb_low_val = bb_lower.iloc[-1]
        
        # --- Phase 9: Risk Management ---
        atr_series = calculate_atr(hist['High'], hist['Low'], hist['Close'])
        atr_current = atr_series.iloc[-1]
        stop_loss, max_qty = calculate_risk_params(current_price, atr_current, capital=100000, risk_per_trade=0.02) # 2% risk standard
        
        # Technical Signal
        if macd_bullish and rsi_current > 50:
            tech_signal = "Bullish"
        elif not macd_bullish and rsi_current < 50:
            tech_signal = "Bearish"
        else:
            tech_signal = "Neutral"
        
        # --- Fundamentals ---
        roe = info.get('returnOnEquity', 0)
        roe = 0 if roe is None else roe
        
        sales_growth = info.get('revenueGrowth', 0)
        sales_growth = 0 if sales_growth is None else sales_growth
        
        profit_margin = info.get('profitMargins', 0)
        profit_margin = 0 if profit_margin is None else profit_margin
        
        eps_growth = info.get('earningsGrowth', 0)
        eps_growth = 0 if eps_growth is None else eps_growth

        # --- Phase 68: Robust Fundamental Fallbacks ---
        # If yfinance summary fails (None/0 for NSE), derive from financial statements
        if roe == 0:
            roe_derived = calculate_current_roe(ticker)
            if roe_derived > 0:
                roe = roe_derived / 100.0 # Convert back to decimal to match yf logic

        if sales_growth == 0:
            sales_growth_derived = calculate_recent_sales_growth(ticker)
            if sales_growth_derived > 0:
                sales_growth = sales_growth_derived / 100.0

        debt_equity = info.get('debtToEquity', 0) or 0
        if debt_equity > 10: debt_equity = debt_equity / 100
        
        peg_ratio = info.get('pegRatio')
        if peg_ratio is not None:
             peg_ratio = round(float(peg_ratio), 2)

        promoter_holding = (info.get('heldPercentInsiders', 0) or 0) * 100
        inst_holding = (info.get('heldPercentInstitutions', 0) or 0) * 100
        
        # Pledge Percentage (NSE specific often found in 'pledgedPercent' or similar)
        pledge_pct = info.get('pledgedPercent', 0) or 0
        if pledge_pct > 1: pledge_pct = pledge_pct # already in pct 
        else: pledge_pct = pledge_pct * 100 # convert from decimal
        
        total_smart_money = promoter_holding + inst_holding

        # Cashflow
        free_cashflow = info.get('freeCashflow', 0)
        operating_cashflow = info.get('operatingCashflow', 0)
        
        # 2. Sales Growth & ROE (5-Year) & Earnings Acceleration
        financials = ticker.financials
        revenue_cagr_5y = 0
        avg_roe_5y = 0
        earnings_accel = False
        
        if not financials.empty:
            try:
                revs = financials.loc['Total Revenue'].iloc[::-1]
                if len(revs) >= 4 and revs.iloc[0] != 0:
                    try:
                        cagr_rev = (revs.iloc[-1] / revs.iloc[0]) ** (1/(len(revs)-1)) - 1
                        revenue_cagr_5y = round(cagr_rev * 100, 2)
                    except ZeroDivisionError:
                        revenue_cagr_5y = round(sales_growth * 100, 2)
                else:
                    revenue_cagr_5y = round(sales_growth * 100, 2)
                
                # Avg ROE
                net_income_series = financials.loc['Net Income'].iloc[::-1]
                bs = ticker.balance_sheet
                if not bs.empty and 'Stockholders Equity' in bs.index:
                    equity_series = bs.loc['Stockholders Equity'].iloc[::-1]
                    roes = []
                    common_dates = net_income_series.index.intersection(equity_series.index)
                    for dt in common_dates:
                        ni = net_income_series[dt]
                        eq = equity_series[dt]
                        if eq > 0: roes.append(ni / eq)
                    if roes: avg_roe_5y = round(float(np.median(roes)) * 100, 2)
                else:
                    avg_roe_5y = round(roe * 100, 2)
            except Exception as e: 
                import logging
                logging.error(f"Error: {e}", exc_info=True)
                revenue_cagr_5y = round(sales_growth * 100, 2)
                avg_roe_5y = round(roe * 100, 2)
        
        # --- Multibagger Framework: ROCE & Median PAT Growth ---
        roce = calculate_roce(ticker)
        median_pat_growth_5y = calculate_median_pat_growth(ticker, years=5)
        
        # Earnings Acceleration is now calculated via check_earnings_inflection below

        # 3. CFO / PAT Ratio
        try:
            cfo = info.get('operatingCashflow')
            pat = info.get('netIncomeToCommon') or (info.get('trailingEps',0) * info.get('sharesOutstanding',0))
            if cfo and pat and pat > 0:
                cfo_pat_ratio = round(cfo / pat, 2)
            else:
                cfo_pat_ratio = 0
        except Exception as e: 
            import logging
            logging.error(f"Error: {e}", exc_info=True)
            cfo_pat_ratio = 0

        # --- F-Score Metrics (Full 9-Point Piotroski) ---
        f_score_method = "9pt_piotroski"
        try:
            f_score = calculate_piotroski_f_score(ticker)
        except Exception as e: 
            import logging
            logging.error(f"Error: {e}", exc_info=True)
            f_score = 0
        
        # Fallback: If 9pt F-Score returns 0 (empty financials), use inline estimate
        if f_score == 0:
            f_score_method = "5pt_inline"
            f_roa = 1 if info.get('returnOnAssets', 0) and info.get('returnOnAssets', 0) > 0 else 0
            f_cfo = 1 if info.get('operatingCashflow', 0) and info.get('operatingCashflow', 0) > 0 else 0
            net_income_f = info.get('netIncomeToCommon', 0)
            op_cash_f = info.get('operatingCashflow', 0)
            f_quality = 1 if (op_cash_f is not None and net_income_f is not None and op_cash_f > net_income_f) else 0
            f_leverage = 1 if debt_equity < 0.4 else 0
            f_margin = 1 if info.get('grossMargins', 0) and info.get('grossMargins', 0) > 0 else 0
            f_score = f_roa + f_cfo + f_quality + f_leverage + f_margin

        # --- Earnings Inflection (Rich 0-5 Score) ---
        try:
            inflection = check_earnings_inflection(ticker)
            earnings_inflection_score = inflection.get('score', 0)
            earnings_accel = inflection.get('status', False)
        except Exception as e: 
            import logging
            logging.error(f"Error: {e}", exc_info=True)
            earnings_inflection_score = 0
            earnings_accel = False

        # Sector Refinement
        sector = get_refined_sector(
            ticker_symbol, 
            info.get('longName', ''), 
            info.get('sector', 'Unknown'), 
            info.get('industry', 'Unknown')
        )
        industry = info.get('industry', 'Unknown')

        # --- 8-Point Metrics ---
        trailing_pe = info.get('trailingPE')
        if trailing_pe is not None:
            trailing_pe = round(float(trailing_pe), 2)
        market_cap_crore = info.get('marketCap', 0) / 10000000
        
        # 52W Range Extraction
        high_52w = info.get('fiftyTwoWeekHigh', current_price) or current_price
        low_52w = info.get('fiftyTwoWeekLow', current_price) or current_price
        
        down_from_high_pct = 0
        if high_52w > 0:
            down_from_high_pct = round(((high_52w - current_price) / high_52w) * 100, 2)
            
        # --- Phase 2: Valuation Rigidity Fixes & Cyclical EPS Normalization ---
        book_value = info.get('bookValue', 0)
        eps_ttm = info.get('trailingEps', 0)
        graham_num = 0
        value_gap = 0
        
        if book_value and book_value > 0:
            try:
                # 1. Cyclical PE Normalization & Growth Capping
                # Smooth boom/bust cyclical EPS by looking at baseline 5Y ROE
                if avg_roe_5y > 0:
                    # Normal cycle EPS based on historical ROE rather than just TTM
                    normalized_eps = (avg_roe_5y / 100.0) * book_value
                    # Cap abnormal TTM spikes (max 50% above normalized historical)
                    safe_eps = min(eps_ttm, normalized_eps * 1.5) if eps_ttm > 0 else normalized_eps
                else:
                    safe_eps = eps_ttm
                
                # If STILL negative after normalization, trigger Asset Floor fallback
                if safe_eps <= 0:
                    # Asset/Book Value fallback for negative EPS stocks (preventing zero-collapse)
                    # Assign liquidation/replacement value floor at 80% Book Value
                    graham_num = round(book_value * 0.8, 2)
                else:
                    # Dynamic Graham multiplier based on growth trajectory, capped at 25
                    fwd_pe = info.get('forwardPE', 15) or 15
                    base_multiplier = min(25.0, max(7.0, fwd_pe * 1.5)) 
                    
                    # Phase 5: Debt-Aware Fair Value Integration (Leverage Penalty)
                    raw_de = info.get('debtToEquity', 0)
                    debt_eq = raw_de / 100.0 if raw_de is not None else 0
                    if debt_eq > 1.0:
                        # De-rate the fair value expansion multiplier heavily for high debt
                        # Example: D/E = 3.0 -> penalty = 0.60 -> Shrinks valuation by 40%
                        leverage_penalty = max(0.5, 1.0 - (debt_eq - 1.0) * 0.2)
                        base_multiplier *= leverage_penalty

                    graham_num = round((base_multiplier * safe_eps * book_value) ** 0.5, 2)
                    
                # Value Gap %: (Intrinsic - Price) / Price
                if current_price > 0:
                    value_gap = round(((graham_num - current_price) / current_price) * 100, 2)
            except Exception as e: 
                import logging
                logging.error(f"Error: {e}", exc_info=True)
                graham_num = 0
                
        # --- Phase 7: Institutional Analyst Estimates (V7.0) ---
        est_analysis = get_estimate_data(
            ticker_symbol,
            info=info,
            allow_alpha_vantage=allow_alpha_vantage,
        )
        m_est = est_analysis.get("momentum")
        
        # Default from yfinance (kept as base if no momentum data)
        analyst_rating = info.get('recommendationKey', 'none').replace('_', ' ').title()
        target_mean = info.get('targetMeanPrice', 0)
        analyst_count = info.get('numberOfAnalystOpinions', 0)
        
        # High-Fidelity Override Logic (from manual_seed or Alpha Vantage)
        if est_analysis.get("source") == "manual_seed":
            seed = est_analysis.get("estimates", {})
            analyst_rating = seed.get("consensus", analyst_rating)
            target_mean = seed.get("target_high", target_mean) # We use High target for elite conviction
            analyst_count = seed.get("analyst_count", analyst_count)
        
        analyst_upside = 0
        if target_mean and target_mean > 0 and current_price > 0:
            analyst_upside = round(((target_mean - current_price) / current_price) * 100, 2)
            
        # Extract Momentum Signals for scoring
        momentum_signal = m_est.get("momentum_signal", "STABLE") if m_est else "STABLE"
        estimate_score_adj = m_est.get("score_adjustment", 0) if m_est else 0
            
        # Phase 22: Volume Data
        avg_vol_10d = info.get('averageVolume10days', info.get('averageVolume', 0))

        # Data-quality availability flags (presence-based, not score/value-based).
        dq_flags = {
            "PE_Ratio": trailing_pe is not None and trailing_pe > 0,
            "PEG_Ratio": peg_ratio is not None and np.isfinite(peg_ratio) and peg_ratio != 0,
            "ROE%": _is_finite_number(info.get('returnOnEquity')) or _is_present_metric(round(roe * 100, 2)),
            "Avg_ROE_5Y%": _is_present_metric(avg_roe_5y),
            "Debt_Equity": _is_finite_number(info.get('debtToEquity')),
            "EPS_Growth%": _is_finite_number(info.get('earningsGrowth')),
            "Sales_Growth_5Y%": _is_present_metric(revenue_cagr_5y) or _is_finite_number(info.get('revenueGrowth')),
            "CFO_PAT_Ratio": _is_present_metric(cfo_pat_ratio),
            "F_Score": (f_score_method == "9pt_piotroski") or (
                f_score > 0 and (
                    info.get('returnOnAssets') is not None or info.get('operatingCashflow') is not None
                )
            ),
            "Market_Cap_Cr": _is_present_metric(market_cap_crore),
        }
                
        final_data = {
            "Symbol": ticker_symbol,
            "Price": current_price,
            "Data_Source": data_source,
            "History_Bars_1Y": history_bars,
            "Last_Price_Date": last_price_date_iso,
            "Price_Age_Days": price_age_days,
            "Avg_Volume_10D": avg_vol_10d, # Added for Phase 22
            "Sector": sector,
            "Industry": industry,
            "Market_Cap_Cr": round(market_cap_crore, 2),
            "200_DMA": dma_200,
            "50_DMA": dma_50,
            "RSI": round(rsi_current, 2),
            "Sales_Growth_TTM%": round(sales_growth * 100, 2),
            "Sales_Growth_5Y%": revenue_cagr_5y,
            "ROE%": round(roe * 100, 2),
            "Avg_ROE_5Y%": avg_roe_5y,
            "Profit_Margin%": round(profit_margin * 100, 2),
            "Debt_Equity": round(debt_equity, 2) if debt_equity is not None else None,
            "PEG_Ratio": peg_ratio,
            "PE_Ratio": trailing_pe,
            "Down_From_52W_High%": down_from_high_pct,
            "Smart_Money%": round(total_smart_money * 100, 2),
            "Free_Cashflow": free_cashflow,
            "CFO_PAT_Ratio": cfo_pat_ratio,
            "EPS_Growth%": round(eps_growth * 100, 2),
            "F_Score": f_score,
            "F_Score_Method": f_score_method,
            "RS_Rating": rs_rating,
            "Earnings_Accel": earnings_accel,
            "Earnings_Inflection_Score": earnings_inflection_score,
            "Graham_Number": graham_num,
            "Value_Gap%": value_gap,
            "Technical_Signal": tech_signal,
            "MACD_Bullish": macd_bullish,
            "Analyst_Rating": analyst_rating,
            "Target_Mean_Price": target_mean,
            "Analyst_Upside%": analyst_upside,
            "Analyst_Count": analyst_count,
            "Promoter_Holding%": round(promoter_holding * 100, 2),
            "Inst_Holding%": round(inst_holding * 100, 2),
            "ATR": round(atr_current, 2),
            "Stop_Loss_ATR": stop_loss,
            "Max_Qty_1L": max_qty,
            "Estimate_Score_Adj": estimate_score_adj,
            "Momentum_Signal": momentum_signal,
            "High_52W": round(float(high_52w), 2),
            "Low_52W": round(float(low_52w), 2),
            "ROCE%": roce,
            "Median_PAT_Growth_5Y%": median_pat_growth_5y,
            "Pledge_Pct": pledge_pct,
            "Ret_1M": mom_features.get("ret_1m", 0),
            "Ret_3M": mom_features.get("ret_3m", 0),
            "Ret_6M": mom_features.get("ret_6m", 0),
            "Vol_Breakout": mom_features.get("vol_breakout", 1.0),
            "Dist_From_52W_High": mom_features.get("dist_from_52w_high", 0),
            "_dq_flags": dq_flags,
        }
        
        # --- V7.1: FUNDAMENTALS OVERRIDE LAYER ---
        # If the analyst seed provides hard fundamentals, override the dict
        f_override = m_est.get("fundamentals_override") if m_est else None
        if f_override:
            for k, v in f_override.items():
                if v is not None:
                    final_data[k] = v
        
        # --- Pydantic Validation ---
        try:
            payload = StockDataPayload(**final_data)
            return payload.model_dump(by_alias=True)
        except Exception as e:
            import logging
            logging.error(f"Pydantic Validation Error for {ticker_symbol}: {e}")
            return final_data

    except Exception as e:
        return {
            "Symbol": ticker_symbol,
            "_fetch_error": "fetch_exception",
            "_fetch_error_detail": str(e)[:180],
            "Data_Source": "unknown",
        }
