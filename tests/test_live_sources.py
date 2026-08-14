import sys
from pathlib import Path
from unittest.mock import patch
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.data_manager import data_manager
import logging

# Enable logging to see which source is processing
logging.basicConfig(level=logging.INFO)

import pytest


@pytest.mark.asyncio
async def test_live_fetch():
    symbol = "SBIN.NS"
    mock_data = {
        "symbol": symbol,
        "info": {"longName": "State Bank of India", "currentPrice": 750.0},
        "financials": pd.DataFrame({"2024": [100, 200]}),
    }
    with patch.object(data_manager, "fetch_fundamentals", return_value=mock_data), \
         patch.object(data_manager, "fetch_quarterly_results", return_value=[{"date": "2024-03-31", "revenue": 1000}]):
        data = data_manager.fetch_fundamentals(symbol)
        assert "error" not in data
        assert data.get("info", {}).get("currentPrice") == 750.0

        timeline = await data_manager.fetch_quarterly_results(symbol)
        assert len(timeline) == 1
        assert timeline[0]["revenue"] == 1000


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_live_fetch())
