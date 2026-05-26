from ingestion.alpaca_fetch import get_bars

df = get_bars("AAPL")

print(df.head())
print(df.columns)