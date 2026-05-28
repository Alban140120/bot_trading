from dotenv import load_dotenv
load_dotenv()

import os
import csv
import time
import pandas as pd
from datetime import datetime, timedelta
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient

# ── Chargement symboles S&P500 depuis CSV ─────────────────────────────────────

def load_sp500_symbols(filepath="data/sp500_symbols.csv"):
    """Charge les symboles S&P500 depuis un fichier CSV."""
    symbols = []
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [name.strip() for name in reader.fieldnames]
        for row in reader:
            symbol = row.get("symbol", "").strip()
            if symbol:
                symbols.append(symbol)
    return symbols

SP500_SYMBOLS = load_sp500_symbols()

# ── Clients Alpaca ────────────────────────────────────────────────────────────

_data_client = StockHistoricalDataClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
)

_trading_client = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True,
)

# ── OHLCV simple (un symbole) ─────────────────────────────────────────────────

def get_bars(symbol="AAPL", days=730):
    """Récupère les données OHLCV pour un seul symbole."""
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=days),
        adjustment="all",
    )

    bars = _data_client.get_stock_bars(request).df

    if bars.empty:
        return bars

    df = bars.loc[symbol].reset_index()
    df["symbol"] = symbol
    return df


# ── OHLCV batch (liste de symboles) ──────────────────────────────────────────

def get_bars_batch(symbols=None, days=1825, batch_size=10, pause=1.0):
    """
    Récupère les données OHLCV pour une liste de symboles.
    Envoie les requêtes par batch pour éviter les rate limits Alpaca.
    """
    if symbols is None:
        symbols = SP500_SYMBOLS

    all_dfs = []
    total = len(symbols)

    for i in range(0, total, batch_size):
        batch = symbols[i:i + batch_size]
        print(f"  Batch {i // batch_size + 1} — {batch}")

        try:
            request = StockBarsRequest(
                symbol_or_symbols=batch,
                timeframe=TimeFrame.Day,
                start=datetime.now() - timedelta(days=days),
                adjustment="all",
            )

            bars = _data_client.get_stock_bars(request).df

            if bars.empty:
                continue

            for symbol in batch:
                if symbol in bars.index.get_level_values(0):
                    df = bars.loc[symbol].reset_index()
                    df["symbol"] = symbol
                    all_dfs.append(df)

        except Exception as e:
            print(f"  Erreur batch {batch} : {e}")

        if i + batch_size < total:
            time.sleep(pause)

    if not all_dfs:
        return pd.DataFrame()

    return pd.concat(all_dfs, ignore_index=True)


# ── Ordres passés ─────────────────────────────────────────────────────────────

def get_orders():
    orders = _trading_client.get_orders()

    if not orders:
        return pd.DataFrame()

    rows = []
    for o in orders:
        rows.append({
            "order_id":          str(o.id),
            "symbol":            o.symbol,
            "side":              o.side.value,
            "qty":               float(o.qty or 0),
            "filled_qty":        float(o.filled_qty or 0),
            "filled_avg_price":  float(o.filled_avg_price or 0),
            "status":            o.status.value,
            "order_type":        o.order_type.value,
            "submitted_at":      o.submitted_at,
            "filled_at":         o.filled_at,
        })

    return pd.DataFrame(rows)