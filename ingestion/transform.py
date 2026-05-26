import pandas as pd

def normalize_bars(df: pd.DataFrame):

    if df is None or df.empty:
        return df

    df = df.reset_index()

    # standardisation safe Alpaca
    df = df.rename(columns={
        "timestamp": "timestamp",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "symbol": "symbol"
    })

    return df