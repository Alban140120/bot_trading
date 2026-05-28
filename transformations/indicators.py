import pandas as pd


def add_sma(df, short=20, long=50):

    df["sma_short"] = df["close"].rolling(short).mean()
    df["sma_long"] = df["close"].rolling(long).mean()

    return df