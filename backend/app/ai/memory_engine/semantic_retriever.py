"""
CogniCompanion — PME Semantic Retriever
=======================================
Executes patient-scoped vector similarity search over MemoryEmbedding records.

Features:
  - Database-side pgvector cosine similarity search in PostgreSQL production
  - In-memory cosine similarity fallback for SQLite (tests & lightweight environments)
  - Configurable similarity threshold
  - Capped, secondary significance weighting that never overpowers semantic relevance
  - Strict database-query-level patient isolation
"""

import json
import logging
import math
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.providers.embeddings import get_embedding_provider
from app.core.config import get_settings
from app.domains.memories.models import Memory
from app.domains.voice.models import MemoryEmbedding, _PGVECTOR_AVAILABLE

logger = logging.getLogger(__name__)
settings = get_settings()


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


class SemanticRetriever:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def search(
        self,
        patient_id: uuid.UUID,
        query: str,
        limit: int = 5,
        threshold: float | None = None,
        query_vector: list[float] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Performs semantic vector search strictly scoped to the patient.
        Returns ranked list of dicts:
          [{"memory": Memory, "similarity": float, "score": float}, ...]
        """
        effective_threshold = (
            threshold if threshold is not None else settings.SEMANTIC_SIMILARITY_THRESHOLD
        )
        significance_boost = getattr(settings, "SEMANTIC_SIGNIFICANCE_BOOST", 0.05)

        # 1. Generate query embedding if not pre-computed
        if query_vector is None:
            try:
                provider = get_embedding_provider()
                query_vector = await provider.embed(query)
            except Exception as e:
                logger.warning("Embedding generation failed for query '%s' (%s)", query, e)
                return []

        if not query_vector:
            return []

        # 2. Check dialect for database-side vector search vs SQLite fallback
        is_postgres = False
        try:
            bind = self._db.bind
            if bind and hasattr(bind, "dialect"):
                is_postgres = bind.dialect.name == "postgresql"
        except Exception:
            is_postgres = False

        scored_results: list[dict[str, Any]] = []

        if is_postgres and _PGVECTOR_AVAILABLE:
            try:
                # Production PostgreSQL: Vector similarity in SQL via pgvector <=> operator
                dist_expr = MemoryEmbedding.embedding.cosine_distance(query_vector)
                sim_expr = 1.0 - dist_expr

                stmt = (
                    select(MemoryEmbedding, Memory, sim_expr.label("similarity"))
                    .join(Memory, MemoryEmbedding.memory_id == Memory.id)
                    .options(selectinload(Memory.people), selectinload(Memory.media))
                    .where(
                        Memory.patient_id == patient_id,
                        MemoryEmbedding.embedding.isnot(None),
                        sim_expr >= effective_threshold,
                    )
                    .order_by(dist_expr.asc())
                    .limit(limit * 2)
                )
                result = await self._db.execute(stmt)
                rows = result.all()

                for emb_row, mem, sim_val in rows:
                    similarity = float(sim_val)
                    # Capped secondary boost (e.g. max +0.05, only if primary similarity is already relevant)
                    boost = significance_boost if (mem.is_significant and similarity >= effective_threshold) else 0.0
                    composite_score = round(min(1.0, similarity + boost), 4)

                    scored_results.append({
                        "memory": mem,
                        "similarity": round(similarity, 4),
                        "score": composite_score,
                    })

                scored_results.sort(key=lambda x: x["score"], reverse=True)
                return scored_results[:limit]
            except Exception as e:
                logger.warning("pgvector SQL similarity search failed (%s), falling back to Python similarity", e)

        # 3. SQLite / Fallback: patient-scoped query with Python cosine similarity
        stmt = (
            select(MemoryEmbedding, Memory)
            .join(Memory, MemoryEmbedding.memory_id == Memory.id)
            .options(selectinload(Memory.people), selectinload(Memory.media))
            .where(
                Memory.patient_id == patient_id,
                MemoryEmbedding.embedding.isnot(None),
            )
        )
        result = await self._db.execute(stmt)
        rows = result.all()

        for emb_row, mem in rows:
            raw_emb = emb_row.embedding
            if raw_emb is None:
                continue

            if isinstance(raw_emb, list):
                vector = [float(x) for x in raw_emb]
            elif isinstance(raw_emb, str):
                try:
                    vector = [float(x) for x in json.loads(raw_emb)]
                except Exception:
                    continue
            else:
                try:
                    vector = [float(x) for x in raw_emb]
                except Exception:
                    continue

            similarity = _cosine_similarity(query_vector, vector)

            # Strict relevance gating: only consider results passing the threshold
            if similarity >= effective_threshold:
                # Capped secondary significance boost, breaking ties and giving secondary priority
                boost = significance_boost if mem.is_significant else 0.0
                composite_score = round(similarity + boost, 4)

                scored_results.append({
                    "memory": mem,
                    "similarity": round(similarity, 4),
                    "score": composite_score,
                })

        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:limit]
