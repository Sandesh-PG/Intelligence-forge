import hashlib
import math
import time
import httpx
from app.core.config import settings

_ollama_embed_available: bool = False
_last_embed_check_ts: float = 0.0


def _fallback_hash_embedding(text: str, dim: int = 128) -> list[float]:
    if not text:
        return [0.0] * dim
    vec = [0.0] * dim
    tokens = text.lower().split()
    for tok in tokens:
        idx = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16) % dim
        vec[idx] += 1.0
    for n in (3, 4):
        for i in range(max(0, len(text) - n + 1)):
            ngram = text[i : i + n].lower()
            idx = int(hashlib.sha256(ngram.encode("utf-8")).hexdigest(), 16) % dim
            vec[idx] += 0.5
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0.0:
        vec = [round(x / norm, 6) for x in vec]
    return vec


class EmbeddingService:
    @staticmethod
    def reset_circuit_breaker() -> None:
        global _ollama_embed_available, _last_embed_check_ts
        _ollama_embed_available = None
        _last_embed_check_ts = 0.0

    @staticmethod
    async def embed_text(text: str) -> list[float]:
        global _ollama_embed_available, _last_embed_check_ts
        clean_text = (text or "").strip()[:2000]
        if not clean_text:
            return [0.0] * 128
        if not settings.ollama_base_url:
            return _fallback_hash_embedding(clean_text, dim=128)

        if not _ollama_embed_available:
            return _fallback_hash_embedding(clean_text, dim=128)

        try:
            timeout_cfg = httpx.Timeout(2.0, connect=0.2)
            async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                res = await client.post(
                    f"{settings.ollama_base_url.rstrip('/')}/api/embeddings",
                    json={"model": settings.embedding_model, "prompt": clean_text},
                )
                if res.status_code == 200:
                    data = res.json()
                    emb = data.get("embedding")
                    if isinstance(emb, list) and len(emb) > 0:
                        _ollama_embed_available = True
                        return emb
        except Exception:
            pass

        _ollama_embed_available = False
        _last_embed_check_ts = now
        return _fallback_hash_embedding(clean_text, dim=128)

    @staticmethod
    def embed_text_sync(text: str) -> list[float]:
        global _ollama_embed_available, _last_embed_check_ts
        clean_text = (text or "").strip()[:2000]
        if not clean_text:
            return [0.0] * 128
        if not settings.ollama_base_url:
            return _fallback_hash_embedding(clean_text, dim=128)

        if not _ollama_embed_available:
            return _fallback_hash_embedding(clean_text, dim=128)

        try:
            timeout_cfg = httpx.Timeout(2.0, connect=0.2)
            with httpx.Client(timeout=timeout_cfg) as client:
                res = client.post(
                    f"{settings.ollama_base_url.rstrip('/')}/api/embeddings",
                    json={"model": settings.embedding_model, "prompt": clean_text},
                )
                if res.status_code == 200:
                    data = res.json()
                    emb = data.get("embedding")
                    if isinstance(emb, list) and len(emb) > 0:
                        _ollama_embed_available = True
                        return emb
        except Exception:
            pass

        _ollama_embed_available = False
        _last_embed_check_ts = now
        return _fallback_hash_embedding(clean_text, dim=128)

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return max(-1.0, min(1.0, dot / (norm_a * norm_b)))

