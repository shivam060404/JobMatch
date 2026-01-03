import argparse
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import Database
from src.extractor import ExtractionError, RequirementExtractor
from src.models import RawJobPosting

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def extract_requirements_for_jobs(
    db: Database,
    extractor: RequirementExtractor,
    limit: int = None,
    needs_review_only: bool = False,
    batch_size: int = 50,
    delay: float = 0.5,
) -> dict:
    all_jobs = db.get_all_jobs()
    
    if needs_review_only:
        jobs_to_process = [j for j in all_jobs if j.requirements.needs_review]
        logger.info(f"Found {len(jobs_to_process)} jobs needing review")
    else:
        # Process jobs that have no skills extracted yet
        jobs_to_process = [
            j for j in all_jobs 
            if not j.requirements.skills or j.requirements.needs_review
        ]
        logger.info(f"Found {len(jobs_to_process)} jobs needing extraction")
    
    if limit:
        jobs_to_process = jobs_to_process[:limit]
        logger.info(f"Limited to {len(jobs_to_process)} jobs")
    
    if not jobs_to_process:
        logger.info("No jobs to process")
        return {"processed": 0, "success": 0, "failed": 0, "needs_review": 0}
    
    # Track statistics
    stats = {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "needs_review": 0,
        "total_latency": 0.0,
    }
    
    start_time = time.time()
    
    for i, job in enumerate(jobs_to_process):
        try:
            # Convert StructuredJob to RawJobPosting for extraction
            raw_posting = RawJobPosting(
                source=job.source,
                external_id=job.external_id,
                title=job.title,
                company=job.company,
                description=job.description,
                location=job.requirements.location,
                url=job.url,
            )
            
            # Extract requirements
            extraction_start = time.time()
            extracted = extractor.extract(raw_posting)
            extraction_latency = time.time() - extraction_start
            stats["total_latency"] += extraction_latency
            
            # Update job with extracted requirements
            job.requirements = extracted
            db.insert_job(job)
            
            stats["processed"] += 1
            if extracted.needs_review:
                stats["needs_review"] += 1
            else:
                stats["success"] += 1
            
            # Log progress every 50 jobs
            if (i + 1) % 50 == 0:
                avg_latency = stats["total_latency"] / stats["processed"]
                logger.info(
                    f"Progress: {i + 1}/{len(jobs_to_process)} jobs "
                    f"({stats['success']} success, {stats['needs_review']} needs review, "
                    f"{stats['failed']} failed, avg latency: {avg_latency:.2f}s)"
                )
                
        except ExtractionError as e:
            logger.error(f"Extraction failed for job {job.id}: {e}")
            stats["failed"] += 1
            stats["processed"] += 1
            
            # Mark job as needing review
            job.requirements.needs_review = True
            db.insert_job(job)
            
        except Exception as e:
            logger.error(f"Unexpected error for job {job.id}: {e}")
            stats["failed"] += 1
            stats["processed"] += 1
        
        # Add delay between requests to avoid rate limits
        if delay > 0 and i < len(jobs_to_process) - 1:
            time.sleep(delay)
    
    total_time = time.time() - start_time
    
    # Calculate final statistics
    if stats["processed"] > 0:
        stats["avg_latency"] = stats["total_latency"] / stats["processed"]
    else:
        stats["avg_latency"] = 0.0
    
    stats["total_time"] = total_time
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Extract structured requirements from job postings using LLM"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of jobs to process (default: all)"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/jobs.db",
        help="Path to SQLite database (default: data/jobs.db)"
    )
    parser.add_argument(
        "--needs-review-only",
        action="store_true",
        help="Only process jobs marked as needing review"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Groq API key (default: from GROQ_API_KEY env var)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="llama-3.1-8b-instant",
        help="Groq model to use (default: llama-3.1-8b-instant)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between API calls in seconds to avoid rate limits (default: 0.5)"
    )
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.error("Groq API key not provided")
        logger.info("Set GROQ_API_KEY environment variable or use --api-key flag")
        sys.exit(1)
    
    # Validate database exists
    if not Path(args.db_path).exists():
        logger.error(f"Database not found: {args.db_path}")
        logger.info("Run data ingestion first:")
        logger.info("  python -m scripts.ingest_data --kaggle data/kaggle/linkedin/postings.csv")
        sys.exit(1)
    
    # Initialize components
    logger.info("Initializing database and extractor...")
    db = Database(db_path=args.db_path)
    extractor = RequirementExtractor(groq_api_key=api_key, model=args.model)
    
    try:
        # Get initial job count
        total_jobs = db.count_jobs()
        logger.info(f"Total jobs in database: {total_jobs:,}")
        
        # Run extraction
        stats = extract_requirements_for_jobs(
            db=db,
            extractor=extractor,
            limit=args.limit,
            needs_review_only=args.needs_review_only,
            delay=args.delay,
        )
        
        # Print summary
        logger.info("=" * 60)
        logger.info("Extraction complete!")
        logger.info(f"Jobs processed: {stats['processed']:,}")
        logger.info(f"Successful extractions: {stats['success']:,}")
        logger.info(f"Needs manual review: {stats['needs_review']:,}")
        logger.info(f"Failed extractions: {stats['failed']:,}")
        logger.info(f"Average latency: {stats.get('avg_latency', 0):.3f}s")
        logger.info(f"Total time: {stats.get('total_time', 0):.1f}s")
        
        # Check latency requirement (< 500ms)
        avg_latency_ms = stats.get('avg_latency', 0) * 1000
        if avg_latency_ms < 500:
            logger.info(f"✓ Latency requirement met: {avg_latency_ms:.0f}ms < 500ms")
        else:
            logger.warning(f"✗ Latency requirement not met: {avg_latency_ms:.0f}ms >= 500ms")
        
        logger.info("=" * 60)
        
        # Print extractor stats
        extractor_stats = extractor.get_stats()
        logger.info(f"Extractor stats: {extractor_stats}")
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
