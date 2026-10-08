"""Operator-only recovery for an interrupted, unconfirmed run start."""
import argparse
from dotenv import load_dotenv
from pathlib import Path
from job_search import Settings, Store


def main():
    load_dotenv(Path(__file__).with_name('.env'))
    parser = argparse.ArgumentParser(description="Reset an unknown collection only after checking Apify for an accepted run. If a run exists, import it with APIFY_SEED_RUN_ID instead.")
    parser.add_argument("query_id")
    parser.add_argument("--confirmed-no-run", action="store_true", required=True)
    args = parser.parse_args()
    store = Store(Settings.from_env().db_path)
    row = store.get(args.query_id)
    if not row or row["state"]!="unknown":
        parser.error("Only an unknown collection can be reset.")
    store.state(args.query_id,"idle","Operator confirmed no accepted run. Ready for an explicit search.")
    print("Search reset. Its daily budget reservation has been retained.")


if __name__ == "__main__":
    main()
