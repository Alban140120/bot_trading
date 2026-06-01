import logging
import os
from datetime import datetime

def setup_logger():
    """Configure le logger du bot."""
    os.makedirs("logs", exist_ok=True)

    log_filename = f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_filename, encoding="utf-8"),
            logging.StreamHandler(),  # affiche aussi dans le terminal
        ]
    )

    return logging.getLogger("bot")