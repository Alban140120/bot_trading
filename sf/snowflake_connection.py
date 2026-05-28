from snowflake.connector import connect
from config.settings import SNOWFLAKE_CONFIG


def get_conn(schema: str):
    """
    Retourne une connexion Snowflake sur le schéma demandé.
    schema : 'BRONZE', 'SILVER' ou 'GOLD'
    """
    return connect(
        user=SNOWFLAKE_CONFIG["user"],
        password=SNOWFLAKE_CONFIG["password"],
        account=SNOWFLAKE_CONFIG["account"],
        warehouse=SNOWFLAKE_CONFIG["warehouse"],
        database=SNOWFLAKE_CONFIG["database"],
        schema=schema,
    )