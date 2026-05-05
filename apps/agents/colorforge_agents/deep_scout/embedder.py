"""Qdrant embedding with sentence-transformers."""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

from colorforge_agents.contracts.niche_brief import NicheBrief
from colorforge_agents.exceptions import EmbeddingError

_COLLECTION = "niches"
_MODEL_NAME = "all-MiniLM-L6-v2"
_VECTOR_SIZE = 384


class NicheEmbedder:
    """Embeds NicheBrief text and upserts into Qdrant collection 'niches'."""

    def __init__(self, qdrant_client: Any) -> None:  # qdrant_client.AsyncQdrantClient
        self._qdrant = qdrant_client
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(_MODEL_NAME)
        return self._model

    async def ensure_collection(self) -> None:
        """Create the 'niches' collection if it doesn't exist."""
        try:
            from qdrant_client.models import Distance, VectorParams

            collections = await self._qdrant.get_collections()
            existing = {c.name for c in collections.collections}
            if _COLLECTION not in existing:
                await self._qdrant.create_collection(
                    collection_name=_COLLECTION,
                    vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
                )
                logger.info("Created Qdrant collection '{}'", _COLLECTION)
        except Exception as exc:
            raise EmbeddingError(f"Failed to ensure collection: {exc}") from exc

    async def embed_and_store(self, brief: NicheBrief) -> str:
        """Embed brief text, upsert to Qdrant, return the vector point ID."""
        text = self._build_embedding_text(brief)
        try:
            import asyncio

            vector: list[float] = await asyncio.get_event_loop().run_in_executor(
                None, self._encode, text
            )
        except Exception as exc:
            raise EmbeddingError(f"Embedding failed: {exc}") from exc

        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, brief.niche_id))

        try:
            from qdrant_client.models import PointStruct

            await self._qdrant.upsert(
                collection_name=_COLLECTION,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "niche_id": brief.niche_id,
                            "primary_keyword": brief.primary_keyword,
                            "profitability_score": brief.profitability_score,
                            "category_path": brief.category_path,
                        },
                    )
                ],
            )
            logger.info("Upserted niche vector {} for '{}'", point_id, brief.primary_keyword)
        except Exception as exc:
            raise EmbeddingError(f"Qdrant upsert failed: {exc}") from exc

        return point_id

    @staticmethod
    def _build_embedding_text(brief: NicheBrief) -> str:
        pain_summary = " ".join(p.text for p in brief.pain_points[:5])
        return f"{brief.primary_keyword} {' '.join(brief.category_path)} {pain_summary}"

    def _encode(self, text: str) -> list[float]:
        model = self._get_model()
        vector = model.encode(text, normalize_embeddings=True)
        return [float(v) for v in vector]
