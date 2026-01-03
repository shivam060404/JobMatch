import logging
import os
from typing import Dict, List, Optional, Tuple

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    OptimizersConfigDiff,
    PointStruct,
    VectorParams,
)

logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    pass


class VectorStore:

    def __init__(self, collection_name: str = "jobs", path: Optional[str] = None):
        if path is None:
            path = os.environ.get("QDRANT_PATH", "data/qdrant")
        if path:
            self.client = QdrantClient(path=path)
            logger.info(f"Initialized Qdrant with persistent storage at: {path}")
        else:
            self.client = QdrantClient(":memory:")
            logger.info("Initialized Qdrant in-memory mode")
        
        self.collection_name = collection_name
        self._id_mapping: Dict[str, int] = {}  # job_id -> point_id mapping
        self._dimension: Optional[int] = None

    def create_collection(self, dimension: int) -> None:
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if exists:
                self.client.delete_collection(self.collection_name)
                logger.info(f"Deleted existing collection: {self.collection_name}")

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE,  # Better than Euclidean for text embeddings
                ),
                optimizers_config=OptimizersConfigDiff(
                    indexing_threshold=10000,  # Start indexing after 10K vectors
                ),
            )
            self._dimension = dimension
            logger.info(f"Created collection: {self.collection_name} with dimension {dimension}")
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise VectorStoreError(f"Collection creation failed: {e}")

    def _get_point_id(self, job_id: str) -> int:
        import hashlib
        # Use MD5 for deterministic hashing across sessions
        hash_bytes = hashlib.md5(job_id.encode()).digest()
        # Convert first 8 bytes to int64
        point_id = int.from_bytes(hash_bytes[:8], byteorder='big') % (2**63)
        return point_id

    def upsert(self, job_id: str, vector: np.ndarray, metadata: dict) -> None:
        try:
            point_id = self._get_point_id(job_id)

            # Store job_id in payload for retrieval
            payload = {**metadata, "job_id": job_id}

            point = PointStruct(
                id=point_id,
                vector=vector.tolist(),
                payload=payload,
            )

            self.client.upsert(
                collection_name=self.collection_name,
                points=[point],
            )
        except Exception as e:
            logger.error(f"Failed to upsert vector for job {job_id}: {e}")
            raise VectorStoreError(f"Upsert failed: {e}")

    def upsert_batch(self, items: List[Tuple[str, np.ndarray, dict]]) -> None:
        if not items:
            return
            
        try:
            points = []
            for job_id, vector, metadata in items:
                point_id = self._get_point_id(job_id)
                payload = {**metadata, "job_id": job_id}
                points.append(PointStruct(
                    id=point_id,
                    vector=vector.tolist(),
                    payload=payload,
                ))

            # Batch in chunks of 100
            for i in range(0, len(points), 100):
                batch = points[i:i + 100]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch,
                )
            logger.info(f"Upserted {len(points)} vectors")
        except Exception as e:
            logger.error(f"Batch upsert failed: {e}")
            raise VectorStoreError(f"Batch upsert failed: {e}")

    def search(self, query_vector: np.ndarray, limit: int = 20) -> List[dict]:
        try:
            # Use query_points for qdrant-client >= 1.7.0
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector.tolist(),
                limit=limit,
            )

            return [
                {
                    "job_id": hit.payload.get("job_id"),
                    "score": hit.score,
                    "metadata": hit.payload,
                }
                for hit in results.points
            ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise VectorStoreError(f"Search failed: {e}")

    def get_by_id(self, job_id: str) -> Optional[dict]:
        try:
            point_id = self._get_point_id(job_id)
            results = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id],
                with_vectors=True,
            )
            if results:
                return {
                    "job_id": job_id,
                    "vector": results[0].vector,
                    "metadata": results[0].payload,
                }
            return None
        except Exception as e:
            logger.error(f"Get by ID failed for {job_id}: {e}")
            return None

    def delete(self, job_id: str) -> None:
        try:
            point_id = self._get_point_id(job_id)
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[point_id],
            )
        except Exception as e:
            logger.error(f"Delete failed for {job_id}: {e}")
            raise VectorStoreError(f"Delete failed: {e}")

    def count(self) -> int:
        try:
            info = self.client.get_collection(self.collection_name)
            return info.points_count
        except Exception as e:
            logger.error(f"Count failed: {e}")
            return 0

    def collection_exists(self) -> bool:
        try:
            collections = self.client.get_collections().collections
            return any(c.name == self.collection_name for c in collections)
        except Exception as e:
            logger.error(f"Collection exists check failed: {e}")
            return False

    def get_dimension(self) -> Optional[int]:
        if self._dimension:
            return self._dimension
        try:
            info = self.client.get_collection(self.collection_name)
            if hasattr(info.config.params, 'vectors'):
                # Handle named vectors config
                return info.config.params.vectors.size
            return info.config.params.size
        except Exception as e:
            logger.error(f"Get dimension failed: {e}")
            return None
