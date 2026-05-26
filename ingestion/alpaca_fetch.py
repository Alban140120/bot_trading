from dotenv import load_dotenv
load_dotenv()

import os
from datetime import datetime, timedelta
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# ── Client Alpaca ───────────────────────────────────────
client = StockHistoricalDataClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
)

# ── Function principale ────────────────────────────────
def get_bars(symbol="AAPL", days=200):

    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=days),
    )

    bars = client.get_stock_bars(request).df

    if bars.empty:
        return bars

    return bars.loc[symbol].reset_index()