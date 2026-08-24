"""인벤 게시글 텍스트와 메타데이터를 RAG 입력에 맞게 정규화한다."""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

ARTICLE_PATTERN = re.compile(r"/board/maple/2304/(\d+)$")
DATE_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d")
SHORT_TEXT_LENGTH = 100


def normalize_text(value: object) -> str:
    """HTML entity와 Unicode·공백을 정리하되 문단은 보존한다."""
    text = unicodedata.normalize("NFKC", html.unescape(str(value or "")))
    text = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\xa0", " ")
    )
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]

    normalized_lines: list[str] = []
    previous_was_blank = False
    for line in lines:
        if line:
            normalized_lines.append(line)
            previous_was_blank = False
        elif normalized_lines and not previous_was_blank:
            normalized_lines.append("")
            previous_was_blank = True

    return "\n".join(normalized_lines).strip()


def canonicalize_url(value: object) -> str:
    """동일 게시글을 같은 키로 인식하도록 query와 fragment를 제거한다."""
    text = normalize_text(value)
    if not text:
        return ""

    parsed = urlsplit(text)
    path = parsed.path.rstrip("/")
    return urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), path, "", "")
    )


def parse_nullable_int(value: object) -> int | None:
    """쉼표가 포함된 숫자를 정수로 바꾸고 빈 값·오류는 None으로 둔다."""
    text = normalize_text(value).replace(",", "")
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def normalize_datetime(value: object) -> str:
    """알려진 날짜 형식은 ISO 8601로 바꾸고 알 수 없는 값은 보존한다."""
    text = normalize_text(value)
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format).isoformat()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text).isoformat()
    except ValueError:
        return text


def article_id_from_url(url: str) -> str:
    """인벤 게시글 번호 또는 URL hash로 안정적인 문서 ID 재료를 만든다."""
    match = ARTICLE_PATTERN.search(url)
    if match:
        return match.group(1)
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def _rejection(row: dict[str, object], reason: str) -> dict[str, object]:
    return {
        "source_file": row.get("__source_file", ""),
        "source_row": row.get("__source_row"),
        "url": normalize_text(row.get("url")),
        "title": normalize_text(row.get("title")),
        "reason": reason,
    }


def _normalize_row(
    row: dict[str, object],
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    url = canonicalize_url(row.get("url"))
    title = normalize_text(row.get("title"))
    content = normalize_text(row.get("content"))

    if not url:
        return None, _rejection(row, "empty_url")
    if not title:
        return None, _rejection(row, "empty_title")
    if not content:
        return None, _rejection(row, "empty_content")

    article_id = article_id_from_url(url)
    record: dict[str, object] = {
        "document_id": f"inven_tip_{article_id}",
        "article_id": article_id,
        "url": url,
        "category": normalize_text(row.get("category")) or "기타",
        "title": title,
        "author": normalize_text(row.get("author")),
        "created_at": normalize_datetime(row.get("created_at")),
        "views": parse_nullable_int(row.get("views")),
        "likes": parse_nullable_int(row.get("likes")),
        "content": content,
        "text_quality": (
            "short" if len(content) < SHORT_TEXT_LENGTH else "normal"
        ),
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "source_file": row.get("__source_file", ""),
        "source_row": row.get("__source_row"),
    }
    return record, None


def preprocess_rows(
    rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, int]]:
    """행을 정규화하고 URL 기준으로 병합하며 품질 통계를 반환한다."""
    accepted_by_url: dict[str, dict[str, object]] = {}
    rejected: list[dict[str, object]] = []
    duplicate_count = 0

    for row in rows:
        record, error = _normalize_row(row)
        if error is not None:
            rejected.append(error)
            continue

        assert record is not None
        url = str(record["url"])
        if url in accepted_by_url:
            previous = accepted_by_url[url]
            rejected.append(
                {
                    "source_file": previous["source_file"],
                    "source_row": previous["source_row"],
                    "url": previous["url"],
                    "title": previous["title"],
                    "reason": "duplicate_url_replaced",
                }
            )
            duplicate_count += 1
        accepted_by_url[url] = record

    accepted = list(accepted_by_url.values())
    stats = {
        "input_rows": len(rows),
        "accepted_rows": len(accepted),
        "rejected_rows": len(rejected),
        "duplicate_rows": duplicate_count,
    }
    return accepted, rejected, stats
