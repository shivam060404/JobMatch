import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database
from src.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_embeddings(embeddings_path: str) -> tuple:
    logger.info(f"Loading embeddings from {embeddings_path}")
    data = np.load(embeddings_path, allow_pickle=True)
    
    embeddings = data["embeddings"]
    job_ids = data["job_ids"]
    dimension = int(data["dimension"])
    
    logger.info(f"Loaded {len(job_ids)} embeddings with dimension {dimension}")
    return embeddings, job_ids, dimension


def index_embeddings(
    vector_store: VectorStore,
    database: Database,
    embeddings: np.ndarray,
    job_ids: np.ndarray,
    batch_size: int = 100,
) -> int:
    logger.info(f"Indexing {len(job_ids)} embeddings...")
    
    # Prepare batch items
    items = []
    skipped = 0
    
    for i, (job_id, embedding) in enumerate(zip(job_ids, embeddings)):
        job_id_str = str(job_id)
        
        # Get job metadata from database
        job = database.get_job(job_id_str)
        
        if job:
            metadata = {
                "title": job.title,
                "company": job.company,
                "seniority": job.requirements.seniority.value if job.requirements.seniority else None,
                "remote": job.requirements.remote,
                "location": job.requirements.location,
                "skills": job.requirements.skills[:10] if job.requirements.skills else [],  # Limit skills in metadata
            }
        else:
            # Job not found in database, use minimal metadata
            metadata = {"title": "Unknown", "company": "Unknown"}
            skipped += 1
        
        items.append((job_id_str, embedding, metadata))
        
        # Upsert in batches
        if len(items) >= batch_size:
            vector_store.upsert_batch(items)
            items = []
            
            if (i + 1) % 500 == 0:
                logger.info(f"Indexed {i + 1}/{len(job_ids)} vectors...")
    
    # Upsert remaining items
    if items:
        vector_store.upsert_batch(items)
    
    if skipped > 0:
        logger.warning(f"Skipped metadata for {skipped} jobs (not found in database)")
    
    return len(job_ids)


def verify_search(vector_store: VectorStore, embeddings: np.ndarray, job_ids: np.ndarray) -> bool:
    logger.info("Verifying search functionality...")
    
    # Test with first embedding
    query_vector = embeddings[0]
    expected_job_id = str(job_ids[0])
    
    # Measure search latency
    start_time = time.time()
    results = vector_store.search(query_vector, limit=10)
    latency_ms = (time.time() - start_time) * 1000
    
    logger.info(f"Search latency: {latency_ms:.2f}ms")
    
    # Verify results
    if not results:
        logger.error("Search returned no results!")
        return False
    
    # The first result should be the query itself (highest similarity)
    top_result = results[0]
    if top_result["job_id"] != expected_job_id:
        logger.warning(f"Top result job_id mismatch: expected {expected_job_id}, got {top_result['job_id']}")
    
    # Check latency requirement (<500ms)
    if latency_ms > 500:
        logger.warning(f"Search latency {latency_ms:.2f}ms exceeds 500ms requirement")
    else:
        logger.info(f"Search latency {latency_ms:.2f}ms meets <500ms requirement ✓")
    
    # Log sample results
    logger.info("Sample search results:")
    for i, result in enumerate(results[:5]):
        logger.info(f"  {i+1}. {result['metadata'].get('title', 'N/A')} @ {result['metadata'].get('company', 'N/A')} (score: {result['score']:.4f})")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Index job embeddings in Qdrant")
    parser.add_argument(
        "--embeddings-path",
        default="data/embeddings.npz",
        help="Path to embeddings NPZ file",
    )
    parser.add_argument(
        "--db-path",
        default="data/jobs.db",
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--vector-store-path",
        default="data/qdrant",
        help="Path for persistent Qdrant storage (use 'memory' for in-memory)",
    )
    parser.add_argument(
        "--collection-name",
        default="jobs",
        help="Name of the Qdrant collection",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for upserting vectors",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=True,
        help="Verify search after indexing",
    )
    
    args = parser.parse_args()
    
    # Load embeddings
    embeddings, job_ids, dimension = load_embeddings(args.embeddings_path)
    
    # Initialize database
    database = Database(args.db_path)
    logger.info(f"Connected to database: {args.db_path}")
    logger.info(f"Database contains {database.count_jobs()} jobs")
    
    # Initialize vector store
    vector_store_path = None if args.vector_store_path == "memory" else args.vector_store_path
    vector_store = VectorStore(
        collection_name=args.collection_name,
        path=vector_store_path,
    )
    
    # Create collection
    vector_store.create_collection(dimension)
    
    # Index embeddings
    start_time = time.time()
    indexed_count = index_embeddings(
        vector_store=vector_store,
        database=database,
        embeddings=embeddings,
        job_ids=job_ids,
        batch_size=args.batch_size,
    )
    indexing_time = time.time() - start_time
    
    logger.info(f"Indexed {indexed_count} vectors in {indexing_time:.2f}s")
    logger.info(f"Vector store count: {vector_store.count()}")
    
    # Verify search
    if args.verify:
        verify_search(vector_store, embeddings, job_ids)
    
    logger.info("Indexing complete!")
    
    # Close database connection
    database.close()


if __name__ == "__main__":
    main()
