from backtesting.backtest import load_signals_from_snowflake, run_backtest


def main():
    print("=== Chargement des données depuis Snowflake ===")
    df = load_signals_from_snowflake()
    print(f"  Lignes chargées : {len(df)}\n")

    print("=== Lancement du backtest ===")
    df_results, metrics = run_backtest(df, capital=100_000, trade_size=1_000)

    print("\n=== Résultats ===")
    print(f"  Capital initial   : ${metrics['capital_initial']:,.2f}")
    print(f"  Capital final     : ${metrics['capital_final']:,.2f}")
    print(f"  PnL total         : ${metrics['total_pnl']:,.2f}")
    print(f"  Rendement total   : {metrics['total_return_pct']}%")
    print(f"  Nombre de trades  : {metrics['total_trades']}")
    print(f"  Trades gagnants   : {metrics['winning_trades']}")
    print(f"  Trades perdants   : {metrics['losing_trades']}")
    print(f"  Win rate          : {metrics['win_rate_pct']}%")
    print(f"  Gain moyen        : ${metrics['avg_win']:,.2f}")
    print(f"  Perte moyenne     : ${metrics['avg_loss']:,.2f}")
    print(f"  Stop-loss déclenchés  : {metrics['stop_loss_triggers']}")
    print(f"  Take-profit déclenchés: {metrics['take_profit_triggers']}")
    print(f"  Max Drawdown      : {metrics['max_drawdown_pct']}%")
    print(f"  Ratio Sortino     : {metrics['sortino_ratio']}")

    print("\n=== Top 10 meilleurs trades ===")
    print(df_results.nlargest(10, "PNL")[
        ["SYMBOL", "ENTRY_DATE", "EXIT_DATE", "ENTRY_PRICE", "EXIT_PRICE", "PNL", "RETURN_PCT"]
    ].to_string(index=False))

    print("\n=== Top 10 pires trades ===")
    print(df_results.nsmallest(10, "PNL")[
        ["SYMBOL", "ENTRY_DATE", "EXIT_DATE", "ENTRY_PRICE", "EXIT_PRICE", "PNL", "RETURN_PCT"]
    ].to_string(index=False))


if __name__ == "__main__":
    main()