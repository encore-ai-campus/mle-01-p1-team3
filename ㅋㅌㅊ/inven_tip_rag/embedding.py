"""청크를 정규화 임베딩으로 변환하고 인계 manifest를 만든다."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .chunking import build_embedding_text


def sha256_file(path: Path) -> str:
    """큰 파일도 메모리에 모두 올리지 않고 SHA-256을 계산한다."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def embed_chunks(
    chunks: list[dict],
    model,
    batch_size: int = 32,
    max_tokens: int = 128,
) -> np.ndarray:
    """청크 순서대로 float32 벡터를 만들고 L2 normalize한다."""
    if not chunks:
        raise ValueError("임베딩할 청크가 없습니다.")
    if batch_size < 1:
        raise ValueError("batch_size는 1 이상이어야 합니다.")

    texts = [
        build_embedding_text(chunk, model.tokenizer, max_tokens=max_tokens)
        for chunk in chunks
    ]
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=False,
    ).astype(np.float32, copy=False)

    if vectors.ndim != 2 or vectors.shape[0] != len(chunks):
        raise ValueError(
            f"임베딩 shape 불일치: chunks={len(chunks)}, vectors={vectors.shape}"
        )

    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if np.any(norms <= 1e-12):
        raise ValueError("0 벡터는 정규화할 수 없습니다.")

    normalized = (vectors / norms).astype(np.float32, copy=False)
    np.testing.assert_allclose(
        np.linalg.norm(normalized, axis=1),
        1.0,
        atol=1e-5,
    )
    return normalized


def build_manifest(
    *,
    chunks: list[dict],
    vectors: np.ndarray,
    chunks_path: Path,
    vectors_path: Path,
    model_name: str,
    chunk_tokens: int,
    overlap_tokens: int,
    max_tokens: int,
) -> dict:
    """청크·벡터 연결 순서와 파일 무결성 정보를 반환한다."""
    return {
        "model_name": model_name,
        "chunk_tokens": chunk_tokens,
        "overlap_tokens": overlap_tokens,
        "model_max_tokens": max_tokens,
        "embedding_count": int(vectors.shape[0]),
        "embedding_dimension": int(vectors.shape[1]),
        "dtype": str(vectors.dtype),
        "normalized": True,
        "chunks_sha256": sha256_file(chunks_path),
        "embeddings_sha256": sha256_file(vectors_path),
        "chunk_ids": [chunk["id"] for chunk in chunks],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
