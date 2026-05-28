from ingestion.alpaca_fetch import get_bars_batch, get_orders, SP500_SYMBOLS
from transformations.transform import normalize_bars, compute_features, compute_signals
from sf.load_bronze import load_market_data, load_orders
from sf.load_silver import load_features
from sf.load_gold import load_signals


def run():
    # ── 1. OHLCV S&P500 → Bronze ──────────────────────────────────────────────
    print("=== Ingestion OHLCV S&P500 (2 ans) ===")
    df_bars = get_bars_batch(symbols=SP500_SYMBOLS, days=1825)
    print(f"  Lignes récupérées : {len(df_bars)}")

    df_bronze = normalize_bars(df_bars)
    print(f"  Lignes après normalisation : {len(df_bronze)}")

    success, rows = load_market_data(df_bronze)
    print(f"  Snowflake BRONZE.MARKET_DATA — success={success}, rows={rows}\n")

    # ── 2. Ordres → Bronze ────────────────────────────────────────────────────
    print("=== Ingestion Ordres ===")
    df_orders = get_orders()

    if df_orders.empty:
        print("  Aucun ordre trouvé.\n")
    else:
        print(f"  Ordres récupérés : {len(df_orders)}")
        success, rows = load_orders(df_orders)
        print(f"  Snowflake BRONZE.ORDERS_RAW — success={success}, rows={rows}\n")

    # ── 3. Features → Silver ──────────────────────────────────────────────────
    print("=== Transformation Silver ===")
    df_silver = compute_features(df_bronze)
    print(f"  Lignes avec indicateurs calculés : {len(df_silver)}")

    success, rows = load_features(df_silver)
    print(f"  Snowflake SILVER.MARKET_FEATURES — success={success}, rows={rows}\n")

    # ── 4. Signaux → Gold ─────────────────────────────────────────────────────
    print("=== Génération signaux Gold ===")
    df_gold = compute_signals(df_silver)
    print(f"  Signaux générés : {len(df_gold)}")
    print(df_gold["SIGNAL"].value_counts().to_string())
    print()

    success, rows = load_signals(df_gold)
    print(f"  Snowflake GOLD.TRADING_SIGNALS — success={success}, rows={rows}\n")


if __name__ == "__main__":
    run()