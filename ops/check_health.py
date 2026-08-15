
import yfinance as yf
from modules.yf_session import get_yf_session

symbols = ["INDIGOPNTS.NS", "RELIANCE.NS", "TATAMOTORS.NS", "TATAMOTORS.BO", "ITDCEM.NS"]

print("Health Check:")
for s in symbols:
    print(f"--- {s} ---")
    try:
        t = yf.Ticker(s, session=get_yf_session())
        hist = t.history(period="1d")
        if not hist.empty:
            print(f"✅ History Check: PASS ({hist['Close'].iloc[-1]})")
        else:
            print("❌ History Check: FAIL (Empty)")
            
        info = t.info
        if info and 'currentPrice' in info:
             print(f"✅ Info Check: PASS ({info['currentPrice']})")
        else:
             print("❌ Info Check: FAIL")
             
    except Exception as e:
        print(f"❌ Exception: {e}")
