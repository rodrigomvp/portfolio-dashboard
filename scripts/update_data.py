"""Refresh the local price database.

Usage:
    python scripts/update_data.py
"""

import logging

from portfolio.config import load_settings
from portfolio.ingest import update_database


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = load_settings()
    update_database(settings)


if __name__ == "__main__":
    main()
