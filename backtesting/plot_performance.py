import pandas as pd
import plotly.graph_objects as go
from backtesting.backtest import load_signals_from_snowflake, run_backtest
from ingestion.alpaca_fetch import get_bars


def get_spy_performance(start_date, end_date, capital=100_000):
    """Récupère les performances du SPY (benchmark S&P500)."""
    df_spy = get_bars("SPY", days=1825)

    if df_spy.empty:
        return pd.Series()

    df_spy["timestamp"] = pd.to_datetime(df_spy["timestamp"]).dt.tz_localize(None)

    # Normaliser start_date et end_date sans timezone
    start_date = pd.Timestamp(start_date).tz_localize(None)
    end_date   = pd.Timestamp(end_date).tz_localize(None)

    df_spy = df_spy[(df_spy["timestamp"] >= start_date) &
                    (df_spy["timestamp"] <= end_date)]
    df_spy = df_spy.sort_values("timestamp")

    initial_price = df_spy["close"].iloc[0]
    df_spy["equity"] = (df_spy["close"] / initial_price) * capital

    return df_spy.set_index("timestamp")["equity"]


def build_equity_curve(df, capital=100_000, trade_size=1_000,
                        stop_loss_pct=0.15, take_profit_pct=0.50):
    """Reconstruit l'equity curve journalière depuis le backtest."""
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

        if symbol in positions:
            entry    = positions[symbol]
            gain_pct = (price - entry["entry_price"]) / entry["entry_price"]

            if gain_pct <= -stop_loss_pct or gain_pct >= take_profit_pct:
                entry      = positions.pop(symbol)
                exit_value = entry["shares"] * price
                cash      += exit_value
                continue

        if signal == "BUY" and symbol not in positions:
            if cash >= trade_size:
                shares = trade_size / price
                positions[symbol] = {
                    "entry_price": price,
                    "shares":      shares,
                    "entry_date":  timestamp,
                }
                cash -= trade_size

        elif signal == "SELL" and symbol in positions:
            entry      = positions.pop(symbol)
            exit_value = entry["shares"] * price
            cash      += exit_value

        open_value = sum(pos["shares"] * price for pos in positions.values())
        equity_curve.append({
            "timestamp": timestamp,
            "equity":    cash + open_value,
        })

    df_equity = (pd.DataFrame(equity_curve)
                   .groupby("timestamp")["equity"]
                   .last()
                   .reset_index())

    return df_equity


def plot_performance():
    print("Chargement des données...")
    df = load_signals_from_snowflake()

    print("Construction de l'equity curve...")
    df_equity = build_equity_curve(df)
    df_equity["timestamp"] = pd.to_datetime(df_equity["timestamp"])

    start_date = df_equity["timestamp"].min()
    end_date   = df_equity["timestamp"].max()

    print("Récupération du benchmark SPY...")
    spy_equity = get_spy_performance(start_date, end_date)

    # ── Aligner sur la même date de départ ────────────────────────────────────
    if not spy_equity.empty:
        # Prendre la date de départ commune
        common_start = max(df_equity["timestamp"].min(),
                          spy_equity.index.min())

        df_equity  = df_equity[df_equity["timestamp"] >= common_start]
        spy_equity = spy_equity[spy_equity.index >= common_start]

    # ── Rendements en % ───────────────────────────────────────────────────────
    initial       = df_equity["equity"].iloc[0]
    df_equity["return_pct"] = (df_equity["equity"] / initial - 1) * 100

    if not spy_equity.empty:
        spy_return_pct = (spy_equity / spy_equity.iloc[0] - 1) * 100

    # ── Graphique ─────────────────────────────────────────────────────────────
    fig = go.Figure()

    # Courbe du bot
    fig.add_trace(go.Scatter(
        x=df_equity["timestamp"],
        y=df_equity["return_pct"],
        mode="lines",
        name="Bot (Vote 3 stratégies)",
        line=dict(color="#00C896", width=2),
        hovertemplate="%{x|%d/%m/%Y}<br>Rendement: %{y:.2f}%<extra></extra>",
    ))

    # Courbe SPY
    if not spy_equity.empty:
        fig.add_trace(go.Scatter(
            x=spy_equity.index,
            y=spy_return_pct,
            mode="lines",
            name="S&P500 (SPY)",
            line=dict(color="#4A90D9", width=2, dash="dash"),
            hovertemplate="%{x|%d/%m/%Y}<br>S&P500: %{y:.2f}%<extra></extra>",
        ))

    # Ligne zéro
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)

    fig.update_layout(
        title=dict(
            text="Performance du bot vs S&P500",
            font=dict(size=20),
        ),
        xaxis=dict(title="Date", showgrid=True, gridcolor="#2a2a2a"),
        yaxis=dict(title="Rendement (%)", showgrid=True, gridcolor="#2a2a2a"),
        legend=dict(x=0.02, y=0.98),
        hovermode="x unified",
        plot_bgcolor="#1a1a1a",
        paper_bgcolor="#1a1a1a",
        font=dict(color="white"),
        height=600,
    )

    fig.write_html("backtesting/performance.html")
    print("Graphique sauvegardé : backtesting/performance.html")
    fig.show()


if __name__ == "__main__":
    plot_performance()