from __future__ import annotations

from typing import Iterable


JOB_KEYWORDS = (
    "직업",
    "전직",
    "스킬트리",
    "하이퍼 스킬",
    "링크 스킬",
    "유니온",
    "보우마스터",
    "히어로",
    "아크메이지",
    "추천",
)

ITEM_KEYWORDS = (
    "아이템",
    "장비",
    "잠재",
    "에디셔널",
    "옵션",
    "큐브",
    "스타포스",
    "강화",
    "추옵",
)

GUIDE_KEYWORDS = (
    "가이드",
    "콘텐츠",
    "퀘스트",
    "이벤트",
    "사냥터",
    "레벨업",
    "보스",
    "레이드",
    "입장",
    "메소",
)


def classify_question(question: str) -> str:
    lowered = question.lower()
    hits = {
        "jobs": _contains_any(lowered, JOB_KEYWORDS),
        "items": _contains_any(lowered, ITEM_KEYWORDS),
        "guide": _contains_any(lowered, GUIDE_KEYWORDS),
    }
    matched = [route for route, present in hits.items() if present]

    if len(matched) >= 2:
        return "mixed"
    if matched:
        return matched[0]
    return "mixed"


def make_search_kwargs(route: str) -> dict:
    if route == "jobs":
        return {"k": 6, "filter": {"source": "jobs"}}
    if route == "items":
        return {"k": 6, "filter": {"source": "items"}}
    if route == "guide":
        return {"k": 5, "filter": {"source": "guide"}}
    return {"k": 8}


def build_context(docs: Iterable, max_chars: int = 1800) -> str:
    docs = list(docs)
    if not docs:
        return "검색된 문서가 없습니다."

    sections: list[str] = []
    seen_keys: set[tuple[str, str]] = set()
    total_length = 0

    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        title = doc.metadata.get("title") or doc.metadata.get("name") or doc.metadata.get("job_name") or "제목 없음"
        dedupe_key = (source, title)
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)

        url = doc.metadata.get("url", "")
        body = " ".join(str(doc.page_content).split())
        excerpt = body[:220].rstrip()
        if len(body) > len(excerpt):
            excerpt += "..."

        section = (
            f"source: {source}\n"
            f"title: {title}\n"
            f"url: {url}\n"
            f"excerpt: {excerpt}"
        )

        candidate = f"[문서 {len(sections) + 1}]\n{section}"
        extra = len(candidate) + (2 if sections else 0)
        if sections and total_length + extra > max_chars:
            break

        sections.append(candidate)
        total_length += extra

    return "\n\n".join(sections)


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)
