import argparse
import logging
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.aggregator import JobAggregator
from src.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def ingest_linkedin_data(
    csv_path: str,
    db: Database,
    aggregator: JobAggregator,
    limit: int = 50000,
    tech_only: bool = True
) -> int:
    logger.info(f"Loading LinkedIn dataset from: {csv_path}")
    
    # Load raw jobs from CSV (uses linkedin source name)
    raw_jobs = aggregator.load_linkedin_dataset(csv_path)
    
    if not raw_jobs:
        logger.warning("No jobs loaded from LinkedIn dataset")
        return 0
    
    logger.info(f"Loaded {len(raw_jobs):,} total jobs from dataset")
    
    # Filter to tech jobs only (Requirement 1.2)
    if tech_only:
        raw_jobs = aggregator.filter_tech_jobs(raw_jobs)
        logger.info(f"After tech filtering: {len(raw_jobs):,} tech jobs")
    
    # Limit the number of jobs
    if limit and len(raw_jobs) > limit:
        raw_jobs = raw_jobs[:limit]
        logger.info(f"Limited to {len(raw_jobs):,} jobs")
    
    # Deduplicate (Requirement 1.4)
    raw_jobs = aggregator.deduplicate(raw_jobs, cross_source=True)
    logger.info(f"After deduplication: {len(raw_jobs):,} jobs")
    
    # Normalize to structured jobs with validation (Requirement 1.5)
    structured_jobs = aggregator.normalize_all(raw_jobs, validate=True)
    logger.info(f"After validation: {len(structured_jobs):,} valid jobs")
    
    # Verify we have 2,000+ tech jobs (Requirement 1.3)
    if tech_only and len(structured_jobs) < 2000:
        logger.warning(f"Only {len(structured_jobs):,} tech jobs - below 2,000 target")
    
    # Store in database
    count = db.insert_jobs_batch(structured_jobs)
    logger.info(f"Stored {count:,} jobs in database")
    
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Ingest LinkedIn job data into the Job Recommender System"
    )
    
    parser.add_argument(
        "--kaggle",
        type=str,
        required=True,
        help="Path to LinkedIn postings.csv file from Kaggle"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50000,
        help="Maximum number of jobs to ingest (default: 50000)"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/jobs.db",
        help="Path to SQLite database (default: data/jobs.db)"
    )
    parser.add_argument(
        "--tech-only",
        action="store_true",
        default=True,
        help="Filter to tech jobs only (default: True)"
    )
    parser.add_argument(
        "--all-jobs",
        action="store_true",
        help="Include all jobs, not just tech roles"
    )
    
    args = parser.parse_args()
    
    # Validate file exists
    if not Path(args.kaggle).exists():
        logger.error(f"File not found: {args.kaggle}")
        logger.info("Download the LinkedIn dataset first:")
        logger.info("  python -m scripts.download_kaggle_data --dataset linkedin")
        sys.exit(1)
    
    # Initialize components
    logger.info("Initializing database and aggregator...")
    db = Database(db_path=args.db_path)
    aggregator = JobAggregator()
    
    try:
        # Determine if we should filter to tech jobs
        tech_only = not args.all_jobs
        
        # Ingest LinkedIn data
        count = ingest_linkedin_data(args.kaggle, db, aggregator, args.limit, tech_only=tech_only)
        
        # Print summary
        total_in_db = db.count_jobs()
        
        logger.info("=" * 50)
        logger.info("Ingestion complete!")
        logger.info(f"Jobs ingested: {count:,}")
        logger.info(f"Total jobs in database: {total_in_db:,}")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise
    finally:
        db.close()
    
    return count


if __name__ == "__main__":
    main()
