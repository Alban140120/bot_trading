from ingestion.alpaca_fetch import get_bars


def test():
    df = get_bars("AAPL", limit=5)

    print(df)

    print("\nShape:", df.shape)
    print("\nColumns:", df.columns)


if __name__ == "__main__":
    test()