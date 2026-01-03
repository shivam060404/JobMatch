import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database
from src.embedding import EmbeddingService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_embeddings(
    db_path: str = "data/jobs.db",
    output_path: str = "data/embeddings.npz",
    batch_size: int = 100,
) -> dict:
    stats = {
        "total_jobs": 0,
        "embeddings_generated": 0,
        "dimension": 0,
        "total_time_seconds": 0,
        "avg_time_per_100": 0,
    }
    
    # Initialize services
    logger.info("Initializing database and embedding service...")
    db = Database(db_path)
    embedding_service = EmbeddingService()
    
    stats["dimension"] = embedding_service.get_dimension()
    logger.info(f"Embedding dimension: {stats['dimension']}")
    
    # Load all jobs
    logger.info("Loading jobs from database...")
    jobs = db.get_all_jobs()
    stats["total_jobs"] = len(jobs)
    logger.info(f"Loaded {stats['total_jobs']} jobs")
    
    if not jobs:
        logger.warning("No jobs found in database!")
        return stats
    
    # Generate embeddings in batches
    all_embeddings = []
    job_ids = []
    
    start_time = time.time()
    
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i + batch_size]
        batch_start = time.time()
        
        # Generate embeddings for batch
        embeddings = embedding_service.embed_jobs_batch(batch)
        
        all_embeddings.append(embeddings)
        job_ids.extend([job.id for job in batch])
        
        batch_time = time.time() - batch_start
        
        # Log progress
        processed = min(i + batch_size, len(jobs))
        logger.info(
            f"Processed {processed}/{len(jobs)} jobs "
            f"({processed/len(jobs)*100:.1f}%) - "
            f"Batch time: {batch_time:.2f}s"
        )
    
    total_time = time.time() - start_time
    stats["total_time_seconds"] = round(total_time, 2)
    stats["avg_time_per_100"] = round(total_time / (len(jobs) / 100), 2)
    
    # Combine all embeddings
    embeddings_array = np.vstack(all_embeddings)
    stats["embeddings_generated"] = len(embeddings_array)
    
    # Verify dimensions
    assert embeddings_array.shape[0] == len(jobs), \
        f"Embedding count mismatch: {embeddings_array.shape[0]} != {len(jobs)}"
    assert embeddings_array.shape[1] == stats["dimension"], \
        f"Dimension mismatch: {embeddings_array.shape[1]} != {stats['dimension']}"
    
    logger.info(f"Generated {len(embeddings_array)} embeddings with shape {embeddings_array.shape}")
    
    # Save embeddings
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    np.savez_compressed(
        output_path,
        embeddings=embeddings_array,
        job_ids=np.array(job_ids, dtype=object),
        dimension=stats["dimension"],
    )
    
    logger.info(f"Saved embeddings to {output_path}")
    
    # Print summary
    logger.info("=" * 50)
    logger.info("Embedding Generation Summary")
    logger.info("=" * 50)
    logger.info(f"Total jobs: {stats['total_jobs']}")
    logger.info(f"Embeddings generated: {stats['embeddings_generated']}")
    logger.info(f"Embedding dimension: {stats['dimension']}")
    logger.info(f"Total time: {stats['total_time_seconds']:.2f}s")
    logger.info(f"Average time per 100 jobs: {stats['avg_time_per_100']:.2f}s")
    logger.info("=" * 50)
    
    return stats


def verify_embeddings(output_path: str = "data/embeddings.npz") -> bool:
    logger.info(f"Verifying embeddings at {output_path}...")
    
    try:
        data = np.load(output_path, allow_pickle=True)
        embeddings = data['embeddings']
        job_ids = data['job_ids']
        dimension = int(data['dimension'])
        
        logger.info(f"Embeddings shape: {embeddings.shape}")
        logger.info(f"Job IDs count: {len(job_ids)}")
        logger.info(f"Dimension: {dimension}")
        
        # Verify consistency
        assert embeddings.shape[0] == len(job_ids), "Embedding count != job ID count"
        assert embeddings.shape[1] == dimension, f"Dimension mismatch: {embeddings.shape[1]} != {dimension}"
        assert dimension == 384, f"Expected 384 dimensions, got {dimension}"
        
        # Verify no NaN or Inf values
        assert not np.isnan(embeddings).any(), "Found NaN values in embeddings"
        assert not np.isinf(embeddings).any(), "Found Inf values in embeddings"
        
        logger.info("✓ Verification passed!")
        return True
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate embeddings for all tech jobs"
    )
    parser.add_argument(
        "--db-path",
        default="data/jobs.db",
        help="Path to SQLite database (default: data/jobs.db)"
    )
    parser.add_argument(
        "--output",
        default="data/embeddings.npz",
        help="Output path for embeddings (default: data/embeddings.npz)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for embedding generation (default: 100)"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing embeddings file"
    )
    
    args = parser.parse_args()
    
    if args.verify_only:
        success = verify_embeddings(args.output)
        sys.exit(0 if success else 1)
    
    stats = generate_embeddings(
        db_path=args.db_path,
        output_path=args.output,
        batch_size=args.batch_size,
    )
    
    # Verify after generation
    verify_embeddings(args.output)
    
    # Check performance target: <1s per 100 embeddings
    if stats["avg_time_per_100"] > 1.0:
        logger.warning(
            f"Performance target missed: {stats['avg_time_per_100']:.2f}s per 100 "
            f"(target: <1s)"
        )
    else:
        logger.info(
            f"✓ Performance target met: {stats['avg_time_per_100']:.2f}s per 100 "
            f"(target: <1s)"
        )


if __name__ == "__main__":
    main()
