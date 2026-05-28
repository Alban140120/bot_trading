from sf.snowflake_connection import get_conn


# ── DDL des tables ────────────────────────────────────────────────────────────

BRONZE_MARKET_DATA = """
CREATE TABLE IF NOT EXISTS BRONZE.MARKET_DATA (
    SYMBOL        VARCHAR(10)    NOT NULL,
    TIMESTAMP     TIMESTAMP_NTZ  NOT NULL,
    OPEN          FLOAT,
    HIGH          FLOAT,
    LOW           FLOAT,
    CLOSE         FLOAT,
    VOLUME        FLOAT,
    TRADE_COUNT   FLOAT,
    VWAP          FLOAT,
    INGESTED_AT   TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP
);
"""

BRONZE_ORDERS = """
CREATE TABLE IF NOT EXISTS BRONZE.ORDERS_RAW (
    ORDER_ID        VARCHAR(50)    NOT NULL,
    SYMBOL          VARCHAR(10),
    SIDE            VARCHAR(5),
    QTY             FLOAT,
    FILLED_QTY      FLOAT,
    FILLED_AVG_PRICE FLOAT,
    STATUS          VARCHAR(20),
    ORDER_TYPE      VARCHAR(20),
    SUBMITTED_AT    TIMESTAMP_NTZ,
    FILLED_AT       TIMESTAMP_NTZ,
    INGESTED_AT     TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP
);
"""

SILVER_MARKET_FEATURES = """
CREATE OR REPLACE TABLE SILVER.MARKET_FEATURES (
    SYMBOL        VARCHAR(10)    NOT NULL,
    TIMESTAMP     TIMESTAMP_NTZ  NOT NULL,
    CLOSE         FLOAT,
    MA_20         FLOAT,
    MA_50         FLOAT,
    RSI_14        FLOAT,
    BB_UPPER      FLOAT,
    BB_MIDDLE     FLOAT,
    BB_LOWER      FLOAT,
    MACD          FLOAT,
    MACD_SIGNAL   FLOAT,
    MACD_HIST     FLOAT,
    ROC_10        FLOAT,
    VOLATILITY    FLOAT,
    PROCESSED_AT  TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP
);
"""

GOLD_TRADING_SIGNALS = """
CREATE TABLE IF NOT EXISTS GOLD.TRADING_SIGNALS (
    SYMBOL        VARCHAR(10)    NOT NULL,
    TIMESTAMP     TIMESTAMP_NTZ  NOT NULL,
    SIGNAL        VARCHAR(10),   -- 'BUY', 'SELL', 'HOLD'
    CONFIDENCE    FLOAT,
    STRATEGY      VARCHAR(50),
    CREATED_AT    TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP
);
"""


# ── Création ──────────────────────────────────────────────────────────────────

def setup_all_tables():
    conn = get_conn("BRONZE")  # la connexion initiale, on switche via SQL
    cur = conn.cursor()

    tables = [
        ("BRONZE.MARKET_DATA",        BRONZE_MARKET_DATA),
        ("BRONZE.ORDERS_RAW",         BRONZE_ORDERS),
        ("SILVER.MARKET_FEATURES",    SILVER_MARKET_FEATURES),
        ("GOLD.TRADING_SIGNALS",      GOLD_TRADING_SIGNALS),
    ]

    for name, ddl in tables:
        try:
            cur.execute(ddl)
            print(f"  ✓ {name}")
        except Exception as e:
            print(f"  ✗ {name} — {e}")

    cur.close()
    conn.close()
    print("\nSetup terminé.")


if __name__ == "__main__":
    print("Création des tables Snowflake...\n")
    setup_all_tables()