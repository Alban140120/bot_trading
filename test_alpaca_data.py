from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, timezone

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

load_dotenv()

client = StockHistoricalDataClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY")
)

end = datetime.now(timezone.utc)
start = end - timedelta(days=30)

request = StockBarsRequest(
    symbol_or_symbols=["AAPL", "TSLA"],
    timeframe=TimeFrame.Day,
    start=start,
    end=end,
    feed="iex"
)

bars = client.get_stock_bars(request)

df = bars.df

print(df.head())
print("\nShape:", df.shape)