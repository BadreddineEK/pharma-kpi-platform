"""APScheduler-based pipeline runner.

Usage:
    python -m pipeline.scheduler           # runs indefinitely
    python -m pipeline.scheduler --run-once  # single run then exit
"""

import argparse
import logging
import sys
import time

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

from pipeline.extract import generate_synthetic_data
from pipeline.load import load
from pipeline.transform import transform

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_pipeline() -> None:
    logger.info("▶ Starting pipeline run...")
    try:
        raw_df = generate_synthetic_data(days=365)
        transformed_df = transform(raw_df)
        inserted = load(transformed_df)
        logger.info(f"✅ Pipeline complete — {inserted} records inserted")
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}", exc_info=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-once", action="store_true", help="Run pipeline once and exit")
    args = parser.parse_args()

    if args.run_once:
        run_pipeline()
        sys.exit(0)

    scheduler = BlockingScheduler()
    scheduler.add_job(run_pipeline, "interval", minutes=60, id="kpi_pipeline")
    logger.info("🕐 Scheduler started — pipeline runs every 60 minutes")
    run_pipeline()  # run immediately on start
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
