
import yfinance as yf
from modules.yf_session import get_yf_session

tickers = ["TATAMOTORS.NS", "RECLTD.NS", "REC.NS", "RELIANCE.NS", "HBLPOWER.NS"]

print("Checking alternatives...")

for t in tickers:
    print(f"\n--- {t} ---")
    try:
        dat = yf.Ticker(t, session=get_yf_session())
        hist = dat.history(period="5d")
        if not hist.empty:
            print(f"✅ {t} Works! Last Close: {hist['Close'].iloc[-1]}")
        else:
            print(f"❌ {t} No History")
            # Try info
            try:
                info = dat.info
                if info and 'regularMarketPrice' in info:
                     print(f"✅ {t} Info Works! Price: {info['regularMarketPrice']}")
                else: 
                     print(f"❌ {t} No Info either")
            except Exception as e:
                print(f"❌ {t} Info Error: {e}")
                
    except Exception as e:
        print(f"❌ {t} Error: {e}")
