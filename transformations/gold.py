import pandas as pd


def generate_signal(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df["signal"] = "hold"

    # stratégie SMA simple
    df.loc[
        df["sma_short"] > df["sma_long"],
        "signal"
    ] = "buy"

    df.loc[
        df["sma_short"] < df["sma_long"],
        "signal"
    ] = "sell"

    return df