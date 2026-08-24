"""모델의 토큰 입력 한도 안에서 게시글을 문단 우선으로 청킹한다."""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter


def count_tokens(tokenizer, text: str, special_tokens: bool = False) -> int:
    """실제 tokenizer 기준 토큰 수를 반환한다."""
    return len(
        tokenizer.encode(
            text,
            add_special_tokens=special_tokens,
            truncation=False,
        )
    )


def truncate_to_tokens(text: str, tokenizer, token_limit: int) -> str:
    """원문 앞부분 중 token_limit을 넘지 않는 가장 긴 문자열을 반환한다."""
    if token_limit < 1:
        return ""
    if count_tokens(tokenizer, text) <= token_limit:
        return text

    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if count_tokens(tokenizer, text[:middle]) <= token_limit:
            low = middle
        else:
            high = middle - 1
    return text[:low].rstrip()


def _embedding_prefix(metadata: dict, tokenizer, prefix_tokens: int) -> str:
    category = str(metadata.get("section_title") or "기타")
    title = str(metadata.get("name") or "제목 없음")
    raw_prefix = f"문서 제목: {title}\n카테고리: {category}"
    return truncate_to_tokens(raw_prefix, tokenizer, prefix_tokens)


def build_embedding_text(chunk: dict, tokenizer, max_tokens: int = 128) -> str:
    """청크 metadata의 prefix와 본문을 결합하고 토큰 한도를 검증한다."""
    prefix = str(chunk["metadata"]["embedding_prefix"])
    candidate = f"{prefix}\n\n{chunk['page_content']}"
    if count_tokens(tokenizer, candidate, special_tokens=True) > max_tokens:
        raise ValueError(f"임베딩 입력 토큰 제한 초과: {chunk['id']}")
    return candidate


def chunk_records(
    records: list[dict],
    tokenizer,
    chunk_tokens: int = 100,
    overlap_tokens: int = 20,
    max_tokens: int = 128,
) -> list[dict]:
    """전처리 게시글을 Chroma 인계용 청크 schema로 변환한다."""
    if chunk_tokens < 1:
        raise ValueError("chunk_tokens는 1 이상이어야 합니다.")
    if overlap_tokens < 0 or overlap_tokens >= chunk_tokens:
        raise ValueError(
            "overlap_tokens는 0 이상 chunk_tokens 미만이어야 합니다."
        )
    if max_tokens < 4:
        raise ValueError("max_tokens는 4 이상이어야 합니다.")

    chunks: list[dict] = []
    for record in records:
        prefix_budget = max(1, max_tokens - chunk_tokens - 2)
        base_metadata = {
            "name": record["title"],
            "section_title": record["category"],
        }
        prefix = _embedding_prefix(base_metadata, tokenizer, prefix_budget)
        body_budget = min(
            chunk_tokens,
            max_tokens - count_tokens(tokenizer, prefix) - 2,
        )
        if body_budget < 1:
            raise ValueError(f"본문 토큰 예산이 없습니다: {record['document_id']}")

        effective_overlap = min(overlap_tokens, max(0, body_budget - 1))
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=body_budget,
            chunk_overlap=effective_overlap,
            length_function=lambda text: count_tokens(tokenizer, text),
            separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
            is_separator_regex=False,
        )
        bodies = [
            body.strip()
            for body in splitter.split_text(str(record["content"]))
            if body.strip()
        ]

        for chunk_index, body in enumerate(bodies):
            chunk_id = f"{record['document_id']}_{chunk_index}"
            metadata = {
                "source": "guide",
                "origin": "inven_tip",
                "source_name": "메이플 인벤 팁과 노하우",
                "document_id": record["document_id"],
                "chunk_id": chunk_id,
                "chunk_index": chunk_index,
                "article_id": record["article_id"],
                "name": record["title"],
                "section_title": record["category"],
                "url": record["url"],
                "created_at": record["created_at"],
                "views": record["views"],
                "likes": record["likes"],
                "text_quality": record["text_quality"],
                "embedding_prefix": prefix,
            }
            chunk = {
                "id": chunk_id,
                "page_content": body,
                "metadata": metadata,
            }
            build_embedding_text(chunk, tokenizer, max_tokens=max_tokens)
            chunks.append(chunk)

    if len({item["id"] for item in chunks}) != len(chunks):
        raise ValueError("중복 chunk_id가 생성됐습니다.")

    return chunks
