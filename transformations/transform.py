import pandas as pd


def normalize_bars(df: pd.DataFrame) -> pd.DataFrame:

    if df is None or df.empty:
        return df

    df = df.rename(columns={
        "symbol":      "SYMBOL",
        "timestamp":   "TIMESTAMP",
        "open":        "OPEN",
        "high":        "HIGH",
        "low":         "LOW",
        "close":       "CLOSE",
        "volume":      "VOLUME",
        "trade_count": "TRADE_COUNT",
        "vwap":        "VWAP",
    })

    return df[[
        "SYMBOL", "TIMESTAMP", "OPEN", "HIGH",
        "LOW", "CLOSE", "VOLUME", "TRADE_COUNT", "VWAP",
    ]]


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les indicateurs techniques à partir des données Bronze.
    Retourne un DataFrame prêt pour SILVER.MARKET_FEATURES.
    """
    if df is None or df.empty:
        return df

    out = df[["SYMBOL", "TIMESTAMP", "CLOSE"]].copy()

    # Moyennes mobiles
    out["MA_20"] = df["CLOSE"].rolling(window=20).mean()
    out["MA_50"] = df["CLOSE"].rolling(window=50).mean()

    # RSI 14
    delta = df["CLOSE"].diff()
    gain  = delta.clip(lower=0).rolling(window=14).mean()
    loss  = (-delta.clip(upper=0)).rolling(window=14).mean()
    rs    = gain / loss.replace(0, float("nan"))
    out["RSI_14"] = 100 - (100 / (1 + rs))

    # Volatilité — écart-type glissant 20 jours des rendements
    out["VOLATILITY"] = df["CLOSE"].pct_change().rolling(window=20).std()

    # Supprimer les lignes sans indicateurs calculables
    out = out.dropna(subset=["MA_20", "MA_50", "RSI_14", "VOLATILITY"])
    out = out.reset_index(drop=True)

    return out

def compute_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Génère des signaux BUY/SELL/HOLD à partir des features Silver.
    Retourne un DataFrame prêt pour GOLD.TRADING_SIGNALS.
    """
    if df is None or df.empty:
        return df

    out = df[["SYMBOL", "TIMESTAMP"]].copy()

    def signal_row(row):
        if row["MA_20"] > row["MA_50"] and row["RSI_14"] < 70:
            return "BUY"
        elif row["MA_20"] < row["MA_50"] and row["RSI_14"] > 30:
            return "SELL"
        else:
            return "HOLD"

    out["SIGNAL"]     = df.apply(signal_row, axis=1)
    out["CONFIDENCE"] = abs(df["MA_20"] - df["MA_50"]) / df["MA_50"] * 100
    out["STRATEGY"]   = "MA_RSI_COMBO"

    return out.reset_index(drop=True)