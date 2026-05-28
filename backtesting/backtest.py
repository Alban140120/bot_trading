import pandas as pd
from sf.snowflake_connection import get_conn


def load_signals_from_snowflake():
    """Charge les données Gold + Bronze depuis Snowflake pour le backtest."""
    conn = get_conn("GOLD")
    cur = conn.cursor()

    query = """
        SELECT
            g.SYMBOL,
            g.TIMESTAMP,
            g.SIGNAL,
            g.CONFIDENCE,
            b.CLOSE
        FROM GOLD.TRADING_SIGNALS g
        JOIN BRONZE.MARKET_DATA b
            ON g.SYMBOL = b.SYMBOL
            AND g.TIMESTAMP = b.TIMESTAMP
        ORDER BY g.SYMBOL, g.TIMESTAMP
    """

    cur.execute(query)
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]

    cur.close()
    conn.close()

    return pd.DataFrame(rows, columns=cols)


def run_backtest(df, capital=100_000, trade_size=1_000, stop_loss_pct=0.15, take_profit_pct=0.50):
    """
    Simule la stratégie avec système de vote + stop-loss.
    - capital       : capital de départ en $
    - trade_size    : montant fixe par trade en $
    - stop_loss_pct : perte maximale tolérée par trade (défaut 15%)
    """

    results = []
    positions = {}
    equity_curve = []

    df = df.sort_values(["TIMESTAMP", "SYMBOL"]).reset_index(drop=True)

    cash = capital

    for _, row in df.iterrows():
        symbol    = row["SYMBOL"]
        signal    = row["SIGNAL"]
        price     = row["CLOSE"]
        timestamp = row["TIMESTAMP"]

        if price is None or price <= 0:
            continue

        # ── Stop-loss ─────────────────────────────────────────────────────────
        if symbol in positions:
            entry    = positions[symbol]
            gain_pct = (price - entry["entry_price"]) / entry["entry_price"]

            if gain_pct <= -stop_loss_pct or gain_pct >= take_profit_pct:
                reason     = "STOP_LOSS" if gain_pct <= -stop_loss_pct else "TAKE_PROFIT"
                entry      = positions.pop(symbol)
                exit_value = entry["shares"] * price
                pnl        = exit_value - trade_size

                results.append({
                    "SYMBOL":      symbol,
                    "ENTRY_DATE":  entry["entry_date"],
                    "EXIT_DATE":   timestamp,
                    "ENTRY_PRICE": entry["entry_price"],
                    "EXIT_PRICE":  price,
                    "SHARES":      entry["shares"],
                    "PNL":         pnl,
                    "RETURN_PCT":  (pnl / trade_size) * 100,
                    "EXIT_REASON": reason,
                })

                cash += exit_value
                continue

        # ── BUY ───────────────────────────────────────────────────────────────
        if signal == "BUY" and symbol not in positions:
            if cash >= trade_size:
                shares = trade_size / price
                positions[symbol] = {
                    "entry_price": price,
                    "shares":      shares,
                    "entry_date":  timestamp,
                }
                cash -= trade_size

        # ── SELL ──────────────────────────────────────────────────────────────
        elif signal == "SELL" and symbol in positions:
            entry      = positions.pop(symbol)
            exit_value = entry["shares"] * price
            pnl        = exit_value - trade_size

            results.append({
                "SYMBOL":      symbol,
                "ENTRY_DATE":  entry["entry_date"],
                "EXIT_DATE":   timestamp,
                "ENTRY_PRICE": entry["entry_price"],
                "EXIT_PRICE":  price,
                "SHARES":      entry["shares"],
                "PNL":         pnl,
                "RETURN_PCT":  (pnl / trade_size) * 100,
                "EXIT_REASON": "SIGNAL",
            })

            cash += exit_value

        # ── Snapshot equity ───────────────────────────────────────────────────
        open_positions_value = sum(
            pos["shares"] * price
            for pos in positions.values()
        )
        equity_curve.append({
            "TIMESTAMP": timestamp,
            "EQUITY":    cash + open_positions_value,
        })

    # ── Positions encore ouvertes à la fin ────────────────────────────────────
    last_prices = df.groupby("SYMBOL")["CLOSE"].last()

    for symbol, entry in positions.items():
        if symbol in last_prices:
            price      = last_prices[symbol]
            exit_value = entry["shares"] * price
            pnl        = exit_value - trade_size

            results.append({
                "SYMBOL":      symbol,
                "ENTRY_DATE":  entry["entry_date"],
                "EXIT_DATE":   None,
                "ENTRY_PRICE": entry["entry_price"],
                "EXIT_PRICE":  price,
                "SHARES":      entry["shares"],
                "PNL":         pnl,
                "RETURN_PCT":  (pnl / trade_size) * 100,
                "EXIT_REASON": "OPEN",
            })

            cash += exit_value

    df_results = pd.DataFrame(results)

    # ── Métriques globales ────────────────────────────────────────────────────
    total_trades  = len(df_results)
    winning       = df_results[df_results["PNL"] > 0]
    losing        = df_results[df_results["PNL"] <= 0]
    total_pnl     = df_results["PNL"].sum()
    final_capital = capital + total_pnl
    total_return  = (total_pnl / capital) * 100
    win_rate      = (len(winning) / total_trades * 100) if total_trades > 0 else 0
    avg_win       = winning["PNL"].mean() if len(winning) > 0 else 0
    avg_loss      = losing["PNL"].mean() if len(losing) > 0 else 0

    # ── Stop-loss stats ───────────────────────────────────────────────────────
    sl_trades = df_results[df_results["EXIT_REASON"] == "STOP_LOSS"]
    tp_trades = df_results[df_results["EXIT_REASON"] == "TAKE_PROFIT"]

    # ── Maximum Drawdown ──────────────────────────────────────────────────────
    df_equity    = pd.DataFrame(equity_curve).groupby("TIMESTAMP")["EQUITY"].last()
    rolling_max  = df_equity.cummax()
    drawdown     = (df_equity - rolling_max) / rolling_max * 100
    max_drawdown = drawdown.min()

    # ── Ratio de Sortino ──────────────────────────────────────────────────────
    returns          = df_equity.pct_change().dropna()
    negative_returns = returns[returns < 0]
    downside_std     = negative_returns.std()
    avg_return       = returns.mean()
    risk_free        = 0.05 / 252

    if downside_std > 0:
        sortino = (avg_return - risk_free) / downside_std * (252 ** 0.5)
    else:
        sortino = float("inf")

    metrics = {
        "capital_initial":   capital,
        "capital_final":     round(final_capital, 2),
        "total_pnl":         round(total_pnl, 2),
        "total_return_pct":  round(total_return, 2),
        "total_trades":      total_trades,
        "winning_trades":    len(winning),
        "losing_trades":     len(losing),
        "win_rate_pct":      round(win_rate, 2),
        "avg_win":           round(avg_win, 2),
        "avg_loss":          round(avg_loss, 2),
        "stop_loss_triggers": len(sl_trades),
        "take_profit_triggers": len(tp_trades),
        "max_drawdown_pct":  round(max_drawdown, 2),
        "sortino_ratio":     round(sortino, 2),
    }

    return df_results, metrics