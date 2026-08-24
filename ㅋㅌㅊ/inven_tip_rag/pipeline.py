"""전처리·청킹·임베딩 단계를 연결하고 산출물을 안전하게 저장한다."""

from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .chunking import chunk_records
from .embedding import build_manifest, embed_chunks
from .input import discover_input_files, load_csv_rows
from .preprocess import preprocess_rows


@dataclass(frozen=True)
class OutputPaths:
    """한 번의 실행에서 생성하는 파일 경로 묶음."""

    processed: Path
    rejected: Path
    chunks: Path
    embeddings: Path
    manifest: Path
    report: Path

    @classmethod
    def under(cls, root: Path) -> "OutputPaths":
        root = root.resolve()
        return cls(
            processed=root / "processed" / "maple_inven_tips_processed.json",
            rejected=root / "processed" / "maple_inven_tips_rejected.json",
            chunks=root / "RAG" / "maple_inven_tips_documents_chunked.json",
            embeddings=root / "RAG" / "maple_inven_tips_embeddings.npy",
            manifest=root / "RAG" / "maple_inven_tips_embeddings_manifest.json",
            report=root / "RAG" / "maple_inven_tips_pipeline_report.json",
        )


def atomic_write_json(path: Path, value: object) -> None:
    """같은 디렉터리의 임시 파일을 완성한 뒤 JSON을 교체한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            delete=False,
        ) as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            temporary = Path(stream.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def atomic_save_numpy(path: Path, vectors: np.ndarray) -> None:
    """allow_pickle이 필요 없는 NPY를 임시 파일에서 완성한 뒤 교체한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb",
            dir=path.parent,
            suffix=".npy",
            delete=False,
        ) as stream:
            np.save(stream, vectors, allow_pickle=False)
            temporary = Path(stream.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def run_preprocess(*, input_patterns, outputs: OutputPaths) -> dict:
    """CSV를 전처리 JSON과 제외 JSON으로 변환한다."""
    paths = discover_input_files(input_patterns)
    rows = load_csv_rows(paths)
    processed, rejected, stats = preprocess_rows(rows)
    atomic_write_json(outputs.processed, processed)
    atomic_write_json(outputs.rejected, rejected)
    return {**stats, "input_files": [str(path) for path in paths]}


def run_chunk(
    *,
    outputs: OutputPaths,
    tokenizer,
    chunk_tokens: int,
    overlap_tokens: int,
    max_tokens: int,
) -> dict:
    """전처리 JSON을 토큰 제한에 맞춘 청크 JSON으로 변환한다."""
    processed = read_json(outputs.processed)
    chunks = chunk_records(
        processed,
        tokenizer,
        chunk_tokens,
        overlap_tokens,
        max_tokens,
    )
    atomic_write_json(outputs.chunks, chunks)
    return {"chunk_count": len(chunks)}


def run_embed(
    *,
    outputs: OutputPaths,
    model,
    model_name: str,
    chunk_tokens: int,
    overlap_tokens: int,
    max_tokens: int,
    batch_size: int,
) -> dict:
    """청크 JSON과 같은 순서의 NPY 및 manifest를 만든다."""
    chunks = read_json(outputs.chunks)
    vectors = embed_chunks(
        chunks,
        model,
        batch_size=batch_size,
        max_tokens=max_tokens,
    )
    atomic_save_numpy(outputs.embeddings, vectors)
    manifest = build_manifest(
        chunks=chunks,
        vectors=vectors,
        chunks_path=outputs.chunks,
        vectors_path=outputs.embeddings,
        model_name=model_name,
        chunk_tokens=chunk_tokens,
        overlap_tokens=overlap_tokens,
        max_tokens=max_tokens,
    )
    atomic_write_json(outputs.manifest, manifest)
    return manifest


def run_all(
    *,
    input_patterns,
    outputs: OutputPaths,
    model,
    model_name: str,
    chunk_tokens: int,
    overlap_tokens: int,
    max_tokens: int,
    batch_size: int,
) -> dict:
    """전체 단계를 실행하고 데이터 품질·shape 리포트를 저장한다."""
    preprocess_stats = run_preprocess(
        input_patterns=input_patterns,
        outputs=outputs,
    )
    chunk_stats = run_chunk(
        outputs=outputs,
        tokenizer=model.tokenizer,
        chunk_tokens=chunk_tokens,
        overlap_tokens=overlap_tokens,
        max_tokens=max_tokens,
    )
    manifest = run_embed(
        outputs=outputs,
        model=model,
        model_name=model_name,
        chunk_tokens=chunk_tokens,
        overlap_tokens=overlap_tokens,
        max_tokens=max_tokens,
        batch_size=batch_size,
    )
    processed = read_json(outputs.processed)
    report = {
        **preprocess_stats,
        **chunk_stats,
        "embedding_count": manifest["embedding_count"],
        "embedding_dimension": manifest["embedding_dimension"],
        "categories": dict(
            sorted(Counter(item["category"] for item in processed).items())
        ),
        "short_text_rows": sum(
            item["text_quality"] == "short" for item in processed
        ),
    }
    atomic_write_json(outputs.report, report)
    return report

