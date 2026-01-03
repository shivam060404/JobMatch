import logging
from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from src.models import CandidateProfile, StructuredJob

logger = logging.getLogger(__name__)


class EmbeddingService:

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        # Get dimension dynamically from model (not hardcoded!)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.model.to('cpu')  # Explicit device for consistency
        logger.info(f"Loaded embedding model: {model_name}, dimension: {self.dimension}")

    def embed_job(self, job: StructuredJob) -> np.ndarray:
        text_parts = [
            job.title,
            job.company,
            " ".join(job.requirements.skills) if job.requirements.skills else "",
            job.requirements.seniority.value if job.requirements.seniority else "",
            job.description[:500] if job.description else "",  # Truncate long descriptions
        ]
        text = " ".join(filter(None, text_parts))
        return self.embed_text(text)

    def embed_candidate(self, profile: CandidateProfile) -> np.ndarray:
        text_parts = [
            " ".join(profile.skills),
            profile.seniority.value if profile.seniority else "",
            profile.location_preference or "",
            f"{profile.experience_years} years experience",
        ]
        text = " ".join(filter(None, text_parts))
        return self.embed_text(text)

    def embed_text(self, text: str) -> np.ndarray:
        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        assert embedding.shape[0] == self.dimension, \
            f"Dimension mismatch: {embedding.shape[0]} != {self.dimension}"
        return embedding

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.array([])

        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=len(texts) > 100,
            convert_to_numpy=True,
        )

        # Validate dimensions
        assert embeddings.shape[1] == self.dimension, \
            f"Dimension mismatch: {embeddings.shape[1]} != {self.dimension}"

        return embeddings

    def embed_jobs_batch(self, jobs: List[StructuredJob]) -> np.ndarray:
        if not jobs:
            return np.array([])

        texts = []
        for job in jobs:
            text_parts = [
                job.title,
                job.company,
                " ".join(job.requirements.skills) if job.requirements.skills else "",
                job.requirements.seniority.value if job.requirements.seniority else "",
                job.description[:500] if job.description else "",
            ]
            texts.append(" ".join(filter(None, text_parts)))

        return self.embed_batch(texts)

    def get_dimension(self) -> int:
        return self.dimension
