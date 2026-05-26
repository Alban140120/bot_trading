from snowflake.connector import connect
from snowflake.connector.pandas_tools import write_pandas
from config.settings import SNOWFLAKE_CONFIG


def get_conn():
    return connect(
        user=SNOWFLAKE_CONFIG["user"],
        password=SNOWFLAKE_CONFIG["password"],
        account=SNOWFLAKE_CONFIG["account"],
        warehouse=SNOWFLAKE_CONFIG["warehouse"],
        database=SNOWFLAKE_CONFIG["database"],
        schema="BRONZE"
    )


def load_market_data(df, table="market_data"):
    conn = get_conn()

    success, chunks, rows, _ = write_pandas(
        conn,
        df,
        table_name=table,
        auto_create_table=True
    )

    conn.close()

    return success, rows