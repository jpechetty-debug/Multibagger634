import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta


def get_benchmark_return():
    """Fetches Nifty 50 6M Return once per run."""
    global BENCHMARK_6M_RETURN
    if BENCHMARK_6M_RETURN is not None:
        return BENCHMARK_6M_RETURN
    
    try:
        nifty = yf.Ticker("^NSEI", session=get_yf_bulk_session())
        hist = nifty.history(period="1y") # Get 1y to be safe
        
        # --- MARKET CLOSED FIX (Dynamic) ---
        today = datetime.now().date()
        from modules.data_manager import data_manager
        is_valid_trading_day = today in data_manager.valid_trading_days
        is_holiday_or_weekend = not is_valid_trading_day
        
        if not hist.empty and 'Close' in hist.columns:
            hist = hist.dropna(subset=['Close'])
            if len(hist) >= 2 and 'Volume' in hist.columns and (pd.isna(hist['Volume'].iloc[-1]) or hist['Volume'].iloc[-1] == 0 or is_holiday_or_weekend):
                hist = hist.iloc[:-1]

        if len(hist) > 126: # Approx 6 months trading days
            price_6m_ago = hist['Close'].iloc[-126]
            price_now = hist['Close'].iloc[-1]
            BENCHMARK_6M_RETURN = ((price_now - price_6m_ago) / price_6m_ago) * 100
            print(f"Benchmark (Nifty) 6M Return: {BENCHMARK_6M_RETURN:.2f}%")
        else:
            BENCHMARK_6M_RETURN = 10.0 # Default fallback
    except Exception as e: 
        import logging
        logging.error(f"Error: {e}", exc_info=True)
        BENCHMARK_6M_RETURN = 10.0
    return BENCHMARK_6M_RETURN

def analyze_sector_rotation(stock_list):
    """
    Analyzes sector performance based on 3M returns of stocks in the list.
    Returns a dict of Sector -> Avg Return.
    """
    sector_returns = {}
    sector_counts = {}
    
    print("\nCalculating Sector Rotation...")
    for stock in stock_list:
        sec = stock.get("Sector", "Unknown")
        rs = stock.get("RS_Rating", 0)
        
        if sec not in sector_returns:
            sector_returns[sec] = 0.0
            sector_counts[sec] = 0
        
        sector_returns[sec] += rs
        sector_counts[sec] += 1
        
    # Average
    avg_sector_rs = {}
    for sec, total_rs in sector_returns.items():
        if sector_counts[sec] > 0:
            avg_sector_rs[sec] = total_rs / sector_counts[sec]
            
    # Sort
    sorted_sectors = sorted(avg_sector_rs.items(), key=lambda x: x[1], reverse=True)
    
    print("Top 3 Leading Sectors (by RS):")
    top_3 = []
    for i, (sec, rs) in enumerate(sorted_sectors[:3]):
        print(f"{i+1}. {sec}: Avg RS {rs:.2f}")
        top_3.append(sec)
        
    return top_3

def analyze_market_regime(symbol="^NSEI"):
    """
    Determines Market Regime: Bull, Bear, Correction, Sideways.
    Also calculates the 200DMA of VIX to return a Regime-Relative VIX limit.
    Returns: (regime_string, vix_relative_limit)
    """
    try:
        ticker = yf.Ticker(symbol, session=get_yf_bulk_session())
        hist = ticker.history(period="2y") # Need 200 DMA
        
        # Also fetch VIX
        try:
            vix_ticker = yf.Ticker("^INDIAVIX", session=get_yf_bulk_session())
            vix_hist = vix_ticker.history(period="2y")
            vix_sma_200 = vix_hist['Close'].tail(200).mean()
            vix_std_200 = vix_hist['Close'].tail(200).std()
            vix_relative_limit = vix_sma_200 + (1.5 * vix_std_200)
            if not np.isfinite(vix_relative_limit):
                vix_relative_limit = 25.0
        except Exception as e: 
            import logging
            logging.error(f"Error: {e}", exc_info=True)
            vix_relative_limit = 25.0
        
        if len(hist) < 200:
            return "Unknown", vix_relative_limit
            
        sma_50 = hist['Close'].tail(50).mean()
        sma_200 = hist['Close'].tail(200).mean()
        current_price = hist['Close'].iloc[-1]
        
        if current_price > sma_50 and sma_50 > sma_200:
            return "Bull Market", vix_relative_limit
        elif current_price < sma_50 and sma_50 < sma_200:
            return "Bear Market", vix_relative_limit
        elif current_price < sma_50 and current_price > sma_200:
            return "Correction", vix_relative_limit
        elif current_price > sma_50 and current_price < sma_200:
            return "Recovery", vix_relative_limit
        else:
            return "Sideways", vix_relative_limit
    except Exception as e: 
        import logging
        logging.error(f"Error: {e}", exc_info=True)
        return "Unknown", 25.0
