from snowflake.connector.pandas_tools import write_pandas
from sf.snowflake_connection import get_conn


def load_features(df, table="MARKET_FEATURES"):
    conn = get_conn("SILVER")

    success, _, rows, _ = write_pandas(
        conn,
        df,
        table_name=table,
        auto_create_table=False,
        overwrite=False,
        quote_identifiers=False,
        use_logical_type=True,
    )

    conn.close()
    return success, rows