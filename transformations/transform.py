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
    Calcule tous les indicateurs techniques par symbole.
    Retourne un DataFrame prêt pour SILVER.MARKET_FEATURES.
    """
    if df is None or df.empty:
        return df

    results = []

    for symbol, group in df.groupby("SYMBOL"):
        g = group.sort_values("TIMESTAMP").copy()

        # ── TrendFollowing ────────────────────────────────────────────────────
        g["MA_20"] = g["CLOSE"].rolling(20).mean()
        g["MA_50"] = g["CLOSE"].rolling(50).mean()

        # ── MeanReversion — RSI 14 ────────────────────────────────────────────
        delta = g["CLOSE"].diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, float("nan"))
        g["RSI_14"] = 100 - (100 / (1 + rs))

        # ── MeanReversion — Bollinger Bands ───────────────────────────────────
        g["BB_MIDDLE"] = g["CLOSE"].rolling(20).mean()
        bb_std         = g["CLOSE"].rolling(20).std()
        g["BB_UPPER"]  = g["BB_MIDDLE"] + 2 * bb_std
        g["BB_LOWER"]  = g["BB_MIDDLE"] - 2 * bb_std

        # ── Momentum — MACD ───────────────────────────────────────────────────
        ema12            = g["CLOSE"].ewm(span=12, adjust=False).mean()
        ema26            = g["CLOSE"].ewm(span=26, adjust=False).mean()
        g["MACD"]        = ema12 - ema26
        g["MACD_SIGNAL"] = g["MACD"].ewm(span=9, adjust=False).mean()
        g["MACD_HIST"]   = g["MACD"] - g["MACD_SIGNAL"]

        # ── Momentum — ROC 10 jours ───────────────────────────────────────────
        g["ROC_10"] = g["CLOSE"].pct_change(10) * 100

        # ── Volatilité ────────────────────────────────────────────────────────
        g["VOLATILITY"] = g["CLOSE"].pct_change().rolling(20).std()

        results.append(g)

    out = pd.concat(results, ignore_index=True)

    out = out.dropna(subset=["MA_50", "RSI_14", "BB_LOWER", "MACD_SIGNAL", "ROC_10"])
    out = out.reset_index(drop=True)

    return out[[
        "SYMBOL", "TIMESTAMP", "CLOSE",
        "MA_20", "MA_50",
        "RSI_14",
        "BB_UPPER", "BB_MIDDLE", "BB_LOWER",
        "MACD", "MACD_SIGNAL", "MACD_HIST",
        "ROC_10",
        "VOLATILITY",
    ]]


def _trend_following(row) -> str:
    if row["MA_20"] > row["MA_50"]:
        return "BUY"
    elif row["MA_20"] < row["MA_50"]:
        return "SELL"
    return "HOLD"


def _mean_reversion(row) -> str:
    if row["CLOSE"] <= row["BB_LOWER"] and row["RSI_14"] < 35:
        return "BUY"
    elif row["CLOSE"] >= row["BB_UPPER"] and row["RSI_14"] > 65:
        return "SELL"
    return "HOLD"


def _momentum(row) -> str:
    if row["MACD"] > row["MACD_SIGNAL"] and row["ROC_10"] > 0:
        return "BUY"
    elif row["MACD"] < row["MACD_SIGNAL"] and row["ROC_10"] < 0:
        return "SELL"
    return "HOLD"


def compute_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Système de vote 3 stratégies — seuil : 2/3 pour valider un signal.
    Retourne un DataFrame prêt pour GOLD.TRADING_SIGNALS.
    """
    if df is None or df.empty:
        return df

    out = df[["SYMBOL", "TIMESTAMP"]].copy()

    out["SIG_TREND"]    = df.apply(_trend_following, axis=1)
    out["SIG_MEAN"]     = df.apply(_mean_reversion,  axis=1)
    out["SIG_MOMENTUM"] = df.apply(_momentum,         axis=1)

    def vote(row):
        signals    = [row["SIG_TREND"], row["SIG_MEAN"], row["SIG_MOMENTUM"]]
        buy_count  = signals.count("BUY")
        sell_count = signals.count("SELL")

        if buy_count >= 2:
            return "BUY"
        elif sell_count >= 2:
            return "SELL"
        return "HOLD"

    def confidence(row):
        signals = [row["SIG_TREND"], row["SIG_MEAN"], row["SIG_MOMENTUM"]]
        final   = vote(row)
        if final == "HOLD":
            return 0.0
        return round(signals.count(final) / 3 * 100, 2)

    out["SIGNAL"]     = out.apply(vote, axis=1)
    out["CONFIDENCE"] = out.apply(confidence, axis=1)
    out["STRATEGY"]   = "VOTE_3S"

    return out[["SYMBOL", "TIMESTAMP", "SIGNAL", "CONFIDENCE", "STRATEGY"]].reset_index(drop=True)