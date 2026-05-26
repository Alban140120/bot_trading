from snowflake.connector import connect
from config.settings import SNOWFLAKE_CONFIG


def test_connection():
    conn = connect(
        user=SNOWFLAKE_CONFIG["user"],
        password=SNOWFLAKE_CONFIG["password"],
        account=SNOWFLAKE_CONFIG["account"],
        warehouse=SNOWFLAKE_CONFIG["warehouse"],
        database=SNOWFLAKE_CONFIG["database"],
        schema=SNOWFLAKE_CONFIG["schema"],
    )

    cur = conn.cursor()
    cur.execute("SELECT 1")
    print("Snowflake OK:", cur.fetchone())

    conn.close()


if __name__ == "__main__":
    test_connection()