import math
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from sf.snowflake_connection import get_conn
from bot.logger import setup_logger

logger = setup_logger()

TRADE_SIZE = 1_000  # $ par position


def get_trading_client():
    import os
    from dotenv import load_dotenv
    load_dotenv()
    return TradingClient(
        os.getenv("ALPACA_API_KEY"),
        os.getenv("ALPACA_SECRET_KEY"),
        paper=True,
    )


# ── 1. Récupérer les derniers signaux Gold ────────────────────────────────────

def get_latest_signals():
    """
    Récupère le dernier signal en date pour chaque symbole depuis Gold.
    Retourne uniquement les signaux BUY et SELL (ignore HOLD).
    """
    conn = get_conn("GOLD")
    cur  = conn.cursor()

    query = """
        WITH latest AS (
            SELECT
                SYMBOL,
                SIGNAL,
                CONFIDENCE,
                TIMESTAMP,
                ROW_NUMBER() OVER (PARTITION BY SYMBOL ORDER BY TIMESTAMP DESC) AS rn
            FROM GOLD.TRADING_SIGNALS
        )
        SELECT SYMBOL, SIGNAL, CONFIDENCE, TIMESTAMP
        FROM latest
        WHERE rn = 1
          AND SIGNAL IN ('BUY', 'SELL')
    """

    cur.execute(query)
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]

    cur.close()
    conn.close()

    return {row[0]: {"signal": row[1], "confidence": row[2], "timestamp": row[3]}
            for row in rows}


# ── 2. Récupérer les positions ouvertes sur Alpaca ────────────────────────────

def get_open_positions(client):
    """Retourne un dict {symbol: position} des positions ouvertes."""
    positions = client.get_all_positions()
    return {p.symbol: p for p in positions}


# ── 3. Récupérer le prix actuel ───────────────────────────────────────────────

def get_current_price(client, symbol):
    """Récupère le dernier prix connu via les positions ou l'API."""
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestQuoteRequest
        import os

        data_client = StockHistoricalDataClient(
            os.getenv("ALPACA_API_KEY"),
            os.getenv("ALPACA_SECRET_KEY"),
        )
        quote = data_client.get_stock_latest_quote(
            StockLatestQuoteRequest(symbol_or_symbols=symbol)
        )
        return float(quote[symbol].ask_price)
    except Exception as e:
        logger.warning(f"Impossible de récupérer le prix de {symbol} : {e}")
        return None


# ── 4. Passer un ordre ────────────────────────────────────────────────────────

def place_order(client, symbol, side, qty):
    """Passe un market order sur Alpaca."""
    try:
        order = client.submit_order(
            MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side,
                time_in_force=TimeInForce.DAY,
            )
        )
        logger.info(f"ORDRE PASSÉ | {side.value} {qty:.4f} {symbol} | id={order.id}")
        return order
    except Exception as e:
        logger.error(f"ERREUR ORDRE | {symbol} {side.value} | {e}")
        return None


# ── 5. Logique principale du bot ──────────────────────────────────────────────

def run_bot():
    logger.info("=" * 60)
    logger.info("Démarrage du bot de trading")
    logger.info("=" * 60)

    client    = get_trading_client()
    signals   = get_latest_signals()
    positions = get_open_positions(client)

    logger.info(f"Signaux récupérés : {len(signals)}")
    logger.info(f"Positions ouvertes : {len(positions)}")

    orders_placed = 0
    orders_skipped = 0

    for symbol, data in signals.items():
        signal     = data["signal"]
        confidence = data["confidence"]
        timestamp  = data["timestamp"]

        # ── BUY ───────────────────────────────────────────────────────────────
        if signal == "BUY" and symbol not in positions:
            price = get_current_price(client, symbol)

            if price and price > 0:
                qty = math.floor((TRADE_SIZE / price) * 10000) / 10000  # 4 décimales
                if qty > 0:
                    logger.info(f"BUY  | {symbol} | prix={price:.2f} | qty={qty:.4f} | conf={confidence:.1f}%")
                    place_order(client, symbol, OrderSide.BUY, qty)
                    orders_placed += 1
                else:
                    logger.warning(f"SKIP | {symbol} | qty trop faible (prix={price:.2f})")
                    orders_skipped += 1
            else:
                logger.warning(f"SKIP | {symbol} | prix indisponible")
                orders_skipped += 1

        # ── SELL ──────────────────────────────────────────────────────────────
        elif signal == "SELL" and symbol in positions:
            pos = positions[symbol]
            qty = float(pos.qty)
            logger.info(f"SELL | {symbol} | qty={qty:.4f} | conf={confidence:.1f}%")
            place_order(client, symbol, OrderSide.SELL, qty)
            orders_placed += 1

        # ── HOLD / pas d'action ───────────────────────────────────────────────
        else:
            reason = "déjà en position" if signal == "BUY" and symbol in positions else "pas de position"
            logger.debug(f"SKIP | {symbol} | signal={signal} | {reason}")

    logger.info("-" * 60)
    logger.info(f"Ordres passés  : {orders_placed}")
    logger.info(f"Ordres skippés : {orders_skipped}")
    logger.info("Bot terminé.")
    logger.info("=" * 60)