"""Refresh the price database and its CSV snapshot.

Usage:
    python scripts/update_data.py          # incremental: only the newest days
    python scripts/update_data.py --full   # download the whole history again

Steps:
  1. Load data/prices.csv into the database if the CSV is newer (e.g. after a git pull).
  2. Download prices from Yahoo Finance.
  3. Write the database back to data/prices.csv, the file that is committed to git
     and that the deployed app reads.

Use --full from time to time (the daily GitHub Action always does): Yahoo's
adjusted prices are recalculated after every dividend, so an incremental update
would leave older prices out of step with the newest ones.
"""

import argparse
import logging
import os

from portfolio.config import load_settings
from portfolio.ingest import update_database
from portfolio.snapshot import export_csv, sync_from_csv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--full", action="store_true", help="download the whole history again")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = load_settings()
    db_path = settings.database_path
    csv_path = db_path.with_suffix(".csv")

    if sync_from_csv(db_path, csv_path):
        logging.info("Loaded %s into the database", csv_path.name)
    update_database(settings, full=args.full)
    rows = export_csv(db_path, csv_path)
    os.utime(db_path)  # the database now matches the CSV: don't re-import it on the next run
    logging.info("Wrote %d rows to %s", rows, csv_path.name)


if __name__ == "__main__":
    main()
