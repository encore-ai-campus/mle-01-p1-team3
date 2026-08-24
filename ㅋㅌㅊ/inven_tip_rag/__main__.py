"""`python -m inven_tip_rag` 명령행 진입점."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_TOKENS,
    MODEL_MAX_TOKENS,
    MODEL_NAME,
)
from .pipeline import OutputPaths, run_all, run_chunk, run_embed, run_preprocess


def _add_output_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output-root", type=Path, default=Path("output"))


def _add_model_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model-name", default=MODEL_NAME)


def _add_chunk_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--chunk-tokens", type=int, default=DEFAULT_CHUNK_TOKENS)
    parser.add_argument(
        "--overlap-tokens",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
    )
    parser.add_argument("--max-tokens", type=int, default=MODEL_MAX_TOKENS)


def _add_input_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        help="CSV 경로 또는 glob; 반복 지정 가능",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="메이플 인벤 팁 RAG 데이터 파이프라인"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    preprocess_parser = subparsers.add_parser(
        "preprocess",
        help="CSV 입력 검증과 전처리",
    )
    _add_input_argument(preprocess_parser)
    _add_output_argument(preprocess_parser)

    chunk_parser = subparsers.add_parser("chunk", help="전처리 JSON 청킹")
    _add_output_argument(chunk_parser)
    _add_model_argument(chunk_parser)
    _add_chunk_arguments(chunk_parser)

    embed_parser = subparsers.add_parser("embed", help="청크 JSON 임베딩")
    _add_output_argument(embed_parser)
    _add_model_argument(embed_parser)
    _add_chunk_arguments(embed_parser)
    embed_parser.add_argument("--batch-size", type=int, default=32)

    all_parser = subparsers.add_parser(
        "all",
        help="전처리·청킹·임베딩 전체 실행",
    )
    _add_input_argument(all_parser)
    _add_output_argument(all_parser)
    _add_model_argument(all_parser)
    _add_chunk_arguments(all_parser)
    all_parser.add_argument("--batch-size", type=int, default=32)
    return parser


def _load_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError(
            "sentence-transformers가 설치되지 않았습니다. "
            "프로젝트 환경을 먼저 동기화하세요."
        ) from error
    return SentenceTransformer(model_name)


def main() -> int:
    args = build_parser().parse_args()
    outputs = OutputPaths.under(args.output_root)

    if args.command == "preprocess":
        stats = run_preprocess(input_patterns=args.input, outputs=outputs)
        print(
            f"전처리 완료: {stats['accepted_rows']}개 유효, "
            f"{stats['rejected_rows']}개 제외"
        )
        return 0

    model = _load_model(args.model_name)
    if args.command == "chunk":
        stats = run_chunk(
            outputs=outputs,
            tokenizer=model.tokenizer,
            chunk_tokens=args.chunk_tokens,
            overlap_tokens=args.overlap_tokens,
            max_tokens=args.max_tokens,
        )
        print(f"청킹 완료: {stats['chunk_count']}개")
        return 0

    if args.command == "embed":
        manifest = run_embed(
            outputs=outputs,
            model=model,
            model_name=args.model_name,
            chunk_tokens=args.chunk_tokens,
            overlap_tokens=args.overlap_tokens,
            max_tokens=args.max_tokens,
            batch_size=args.batch_size,
        )
        print(
            f"임베딩 완료: {manifest['embedding_count']} x "
            f"{manifest['embedding_dimension']}"
        )
        return 0

    report = run_all(
        input_patterns=args.input,
        outputs=outputs,
        model=model,
        model_name=args.model_name,
        chunk_tokens=args.chunk_tokens,
        overlap_tokens=args.overlap_tokens,
        max_tokens=args.max_tokens,
        batch_size=args.batch_size,
    )
    print(
        f"완료: {report['accepted_rows']}개 문서, "
        f"{report['chunk_count']}개 청크"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
