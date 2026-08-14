from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from api.dependencies import (
    manager, _run_blocking
)
from database import get_connection
from modules.retry_utils import run_with_exponential_backoff

router = APIRouter()

@router.websocket("/ws/signals")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection open and handle potential pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

@router.get("/")
def read_root():
    return FileResponse("web-ui/index.html")

@router.get("/api/news/{symbol}")
async def get_news(symbol: str):
    """Fetch Narrative Intelligence (News) with Sentiment Analysis"""
    try:
        from modules.news import get_stock_news
        from modules.alpha_vantage import AlphaVantageProvider
        
        # 1. Fetch primary news from yfinance (Fast)
        news = await get_stock_news(symbol)


        
        # 2. Fetch Sentiment scores from Alpha Vantage (High Fidelity)
        try:
            av = AlphaVantageProvider()
            # Run synchronous and rate-limited call in a separate thread
            sentiment_map = await run_with_exponential_backoff(
                lambda: _run_blocking(av.get_stock_sentiment, symbol),
                context=f"alpha vantage sentiment for {symbol}",
            )
             
            # Merge Sentiment into News

            if sentiment_map:
                symbol_sentiment = sentiment_map.get("__symbol__")
                normalized_symbol = symbol.split(".")[0].upper()
                for item in news:
                    title = item.get("title")
                    if title in sentiment_map:
                        item["sentiment"] = sentiment_map[title]
                        continue

                    related_tickers = [
                        str(t).upper() for t in (item.get("related_tickers") or [])
                    ]
                    if symbol_sentiment and normalized_symbol in related_tickers:
                        item["sentiment"] = symbol_sentiment
                    elif symbol_sentiment and not related_tickers:
                        item["sentiment"] = symbol_sentiment
        except Exception as av_err:
            print(f"Alpha Vantage sentiment fetch failed: {av_err}")

        return news
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/swarm/{symbol}")
async def get_swarm_report(symbol: str):
    """Fetch Swarm Intelligence Validation Report from MiroFish."""
    try:
        from modules.mirofish_client import MiroFishClient
        from modules.symbol_utils import normalize_symbol
        import pandas as pd
        
        symbol = normalize_symbol(symbol)
        client = MiroFishClient()
        
        # 1. Fetch context from DB for the swarm debate
        def _fetch_context():
            conn = get_connection()
            try:
                row = pd.read_sql("SELECT * FROM multibaggers WHERE symbol = ?", conn, params=(symbol,))
                if row.empty: return None
                data = row.iloc[0].to_dict()
                return f"Stock {symbol} in {data.get('sector')} sector. Score: {data.get('score')}. PE: {data.get('pe')}. ROE: {data.get('avg_roe_5y')}. Growth: {data.get('sales_cagr_5y')}."
            finally:
                conn.close()
        
        context = await _run_blocking(_fetch_context)
        if not context:
            return {"error": "Stock not found in database."}
            
        # 2. Trigger/Retrieve Swarm Simulation
        report = await _run_blocking(client.simulate_ticker, symbol, context)
        
        return {
            "symbol": symbol,
            "report": report,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

