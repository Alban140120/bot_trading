from snowflake.connector.pandas_tools import write_pandas
from sf.snowflake_connection import get_conn


def load_market_data(df, table="MARKET_DATA"):
    conn = get_conn("BRONZE")

    success, _, rows, _ = write_pandas(
        conn,
        df,
        table_name=table,
        auto_create_table=False,   # la table doit exister (créée via setup_tables.py)
        overwrite=False,
        quote_identifiers=False,
        use_logical_type=True,
    )

    conn.close()
    return success, rows


def load_orders(df, table="ORDERS_RAW"):
    conn = get_conn("BRONZE")

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