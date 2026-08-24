# Inven Tip RAG Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 지정된 메이플 인벤 팁 CSV를 검증·전처리·토큰 기반 청킹·정규화 임베딩하여 ChromaDB 적재 직전 산출물까지 재현 가능하게 생성한다.

**Architecture:** `src/inven_tip_rag` 패키지에서 입력, 전처리, 청킹, 임베딩, 오케스트레이션 책임을 분리한다. 각 단계는 JSON 또는 NumPy 파일로 경계를 만들고, CLI는 전체 실행과 단계별 재실행을 제공한다. 실제 모델 없이 빠르게 실행되는 단위·통합 테스트를 먼저 통과시킨 뒤 실제 300건과 실제 SentenceTransformer로 최종 산출물을 만든다.

**Tech Stack:** Python 3.12, 표준 라이브러리 `csv/json/glob/pathlib/hashlib`, NumPy, LangChain Text Splitters, SentenceTransformers, `unittest`

**Spec:** `docs/superpowers/specs/2026-08-24-inven-tip-rag-pipeline-design.md`

## Global Constraints

- 현재 입력은 `ㅋㅌㅊ/maple_inven_rag_원본(1~10p).csv` 한 파일이며, 같은 스키마의 추가 CSV는 반복 `--input` 또는 glob으로만 지원한다.
- 인벤 크롤러는 구현하지 않는다.
- `data/processed/stopwords_ko.json`은 읽거나 수정하지 않고 임베딩 본문에서 불용어를 제거하지 않는다.
- 임베딩 모델은 정확히 `jhgan/ko-sroberta-multitask`를 사용한다.
- 모델 최대 입력은 특수 토큰을 포함해 128토큰이며 기본 본문 청크 한도는 100토큰, 중첩은 20토큰이다.
- 임베딩은 NumPy `float32`이고 각 행을 L2 normalize한다.
- `chroma_db/`, `data/Top-k/Top_k.ipynb`, Streamlit, 기존 retriever는 변경하지 않는다.
- 기존 사용자 변경을 스테이징하거나 커밋하지 않는다.
- 모든 파일 저장은 동일 디렉터리의 임시 파일을 검증한 뒤 `os.replace`로 교체한다.

## File Map

| 파일 | 책임 |
| --- | --- |
| `src/inven_tip_rag/__init__.py` | 공개 상수와 패키지 버전 |
| `src/inven_tip_rag/input.py` | 입력 경로/glob 해석, CSV 스키마 검증, 행 로드 |
| `src/inven_tip_rag/preprocess.py` | 필드 정규화, 유효성 검사, URL 중복 제거 |
| `src/inven_tip_rag/chunking.py` | 토큰 계산, prefix 예산, 문단 우선 청킹, chunk schema |
| `src/inven_tip_rag/embedding.py` | embedding text 구성, 벡터 생성·정규화, manifest |
| `src/inven_tip_rag/pipeline.py` | 단계 연결, 원자적 저장, 리포트 생성 |
| `src/inven_tip_rag/__main__.py` | `preprocess/chunk/embed/all` CLI |
| `tests/inven_tip_rag/fakes.py` | deterministic fake tokenizer/model |
| `tests/inven_tip_rag/test_input.py` | 입력 계층 테스트 |
| `tests/inven_tip_rag/test_preprocess.py` | 전처리 테스트 |
| `tests/inven_tip_rag/test_chunking.py` | 청킹 테스트 |
| `tests/inven_tip_rag/test_embedding.py` | 임베딩·manifest 테스트 |
| `tests/inven_tip_rag/test_pipeline.py` | 파일 경계 및 CLI 통합 테스트 |
| `docs/inven-tip-rag-pipeline.md` | 데이터 규칙, 명령, 산출물, ChromaDB 인계 설명 |

---

### Task 1: 입력 파일 탐색과 CSV 계약

**Files:**
- Create: `src/inven_tip_rag/__init__.py`
- Create: `src/inven_tip_rag/input.py`
- Create: `tests/inven_tip_rag/__init__.py`
- Create: `tests/inven_tip_rag/test_input.py`

**Interfaces:**
- Consumes: CLI에서 받은 `Sequence[str | Path]`
- Produces: `discover_input_files(patterns) -> list[Path]`, `load_csv_rows(paths) -> list[dict[str, object]]`, `InputSchemaError`

- [ ] **Step 1: 입력 경로와 CSV 계약의 실패 테스트를 작성한다**

```python
# tests/inven_tip_rag/test_input.py
import csv
import tempfile
import unittest
from pathlib import Path

from src.inven_tip_rag.input import InputSchemaError, discover_input_files, load_csv_rows


class InputTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_csv(self, name, fieldnames, rows):
        path = self.root / name
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_discovers_literal_repeated_and_glob_inputs_without_duplicates(self):
        first = self.write_csv("tips_1.csv", ["url", "title", "content"], [])
        second = self.write_csv("tips_2.csv", ["url", "title", "content"], [])
        found = discover_input_files([str(first), str(self.root / "tips_*.csv")])
        self.assertEqual(found, [first.resolve(), second.resolve()])

    def test_raises_when_pattern_matches_nothing(self):
        with self.assertRaisesRegex(FileNotFoundError, "입력 CSV를 찾지 못했습니다"):
            discover_input_files([str(self.root / "missing_*.csv")])

    def test_raises_with_missing_required_columns(self):
        path = self.write_csv("bad.csv", ["url", "title"], [])
        with self.assertRaisesRegex(InputSchemaError, "content"):
            load_csv_rows([path])

    def test_loads_utf8_sig_and_records_source_location(self):
        path = self.write_csv(
            "tips.csv",
            ["url", "title", "content"],
            [{"url": "https://example.com/1", "title": "제목", "content": "본문"}],
        )
        rows = load_csv_rows([path])
        self.assertEqual(rows[0]["title"], "제목")
        self.assertEqual(rows[0]["__source_file"], str(path.resolve()))
        self.assertEqual(rows[0]["__source_row"], 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트가 모듈 부재로 실패하는지 확인한다**

Run: `uv run python -m unittest tests.inven_tip_rag.test_input -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.inven_tip_rag'`

- [ ] **Step 3: 패키지 상수와 입력 계층을 최소 구현한다**

```python
# src/inven_tip_rag/__init__.py
MODEL_NAME = "jhgan/ko-sroberta-multitask"
MODEL_MAX_TOKENS = 128
DEFAULT_CHUNK_TOKENS = 100
DEFAULT_CHUNK_OVERLAP = 20
__version__ = "0.1.0"
```

```python
# src/inven_tip_rag/input.py
from __future__ import annotations

import csv
import glob
from pathlib import Path
from typing import Sequence

REQUIRED_COLUMNS = frozenset({"url", "title", "content"})
OPTIONAL_COLUMNS = ("category", "author", "created_at", "views", "likes")


class InputSchemaError(ValueError):
    pass


def discover_input_files(patterns: Sequence[str | Path]) -> list[Path]:
    discovered: list[Path] = []
    seen: set[Path] = set()
    for raw_pattern in patterns:
        pattern = str(raw_pattern)
        literal = Path(pattern)
        matches = [literal] if literal.is_file() else [Path(value) for value in sorted(glob.glob(pattern))]
        if not matches:
            raise FileNotFoundError(f"입력 CSV를 찾지 못했습니다: {pattern}")
        for match in matches:
            resolved = match.resolve()
            if resolved.suffix.lower() != ".csv":
                raise ValueError(f"CSV 파일만 입력할 수 있습니다: {resolved}")
            if resolved not in seen:
                seen.add(resolved)
                discovered.append(resolved)
    return discovered


def load_csv_rows(paths: Sequence[Path]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in paths:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            columns = set(reader.fieldnames or ())
            missing = sorted(REQUIRED_COLUMNS - columns)
            if missing:
                raise InputSchemaError(f"{path} 필수 컬럼 누락: {', '.join(missing)}")
            for row_number, row in enumerate(reader, start=2):
                normalized = {key: (value or "") for key, value in row.items() if key is not None}
                for name in OPTIONAL_COLUMNS:
                    normalized.setdefault(name, "")
                normalized["__source_file"] = str(path.resolve())
                normalized["__source_row"] = row_number
                rows.append(normalized)
    return rows
```

- [ ] **Step 4: 입력 테스트가 통과하는지 확인한다**

Run: `uv run python -m unittest tests.inven_tip_rag.test_input -v`

Expected: 4 tests, all PASS

- [ ] **Step 5: 입력 계층만 커밋한다**

```powershell
git add src/inven_tip_rag/__init__.py src/inven_tip_rag/input.py tests/inven_tip_rag/__init__.py tests/inven_tip_rag/test_input.py
git commit -m "feat: add inven tip CSV input layer"
```

---

### Task 2: 전처리와 데이터 품질 보고

**Files:**
- Create: `src/inven_tip_rag/preprocess.py`
- Create: `tests/inven_tip_rag/test_preprocess.py`

**Interfaces:**
- Consumes: `load_csv_rows()`가 반환한 `list[dict[str, str]]`
- Produces: `preprocess_rows(rows) -> tuple[list[dict], list[dict], dict]`, `canonicalize_url()`, `normalize_text()`

- [ ] **Step 1: 정규화·제외·중복 규칙의 실패 테스트를 작성한다**

```python
# tests/inven_tip_rag/test_preprocess.py
import unittest

from src.inven_tip_rag.preprocess import canonicalize_url, normalize_text, preprocess_rows


def raw_row(**overrides):
    row = {
        "url": "https://www.inven.co.kr/board/maple/2304/48082?query=1#part",
        "category": " 실험 ",
        "title": " 제목 &amp; 안내 ",
        "author": "",
        "created_at": "2026-08-03 12:43",
        "views": "12,988",
        "likes": "18",
        "content": "첫 문장\r\n\r\n  둘째   문장 &amp; 설명 ",
        "__source_file": "tips.csv",
        "__source_row": 2,
    }
    row.update(overrides)
    return row


class PreprocessTests(unittest.TestCase):
    def test_normalizes_url_text_numbers_and_date(self):
        processed, rejected, stats = preprocess_rows([raw_row()])
        self.assertEqual(rejected, [])
        self.assertEqual(processed[0]["url"], "https://www.inven.co.kr/board/maple/2304/48082")
        self.assertEqual(processed[0]["title"], "제목 & 안내")
        self.assertEqual(processed[0]["content"], "첫 문장\n\n둘째 문장 & 설명")
        self.assertEqual(processed[0]["created_at"], "2026-08-03T12:43:00")
        self.assertEqual(processed[0]["views"], 12988)
        self.assertEqual(processed[0]["likes"], 18)
        self.assertEqual(processed[0]["document_id"], "inven_tip_48082")
        self.assertEqual(stats["accepted_rows"], 1)

    def test_rejects_empty_content_with_source_location(self):
        processed, rejected, stats = preprocess_rows([raw_row(content="   ")])
        self.assertEqual(processed, [])
        self.assertEqual(rejected[0]["reason"], "empty_content")
        self.assertEqual(rejected[0]["source_row"], 2)
        self.assertEqual(stats["rejected_rows"], 1)

    def test_marks_short_nonempty_content_without_rejecting_it(self):
        processed, rejected, _ = preprocess_rows([raw_row(content="짧은 팁")])
        self.assertEqual(rejected, [])
        self.assertEqual(processed[0]["text_quality"], "short")

    def test_last_valid_duplicate_url_wins(self):
        first = raw_row(title="이전 제목")
        second = raw_row(title="최신 제목", __source_row=3)
        processed, rejected, stats = preprocess_rows([first, second])
        self.assertEqual([item["title"] for item in processed], ["최신 제목"])
        self.assertEqual(rejected[0]["reason"], "duplicate_url_replaced")
        self.assertEqual(stats["duplicate_rows"], 1)

    def test_helpers_are_deterministic(self):
        self.assertEqual(canonicalize_url("https://a.test/1/?x=1#y"), "https://a.test/1")
        self.assertEqual(normalize_text("Ａ  B\r\n\r\n C"), "A B\n\nC")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트가 전처리 모듈 부재로 실패하는지 확인한다**

Run: `uv run python -m unittest tests.inven_tip_rag.test_preprocess -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.inven_tip_rag.preprocess'`

- [ ] **Step 3: 전처리 함수를 구현한다**

```python
# src/inven_tip_rag/preprocess.py
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
    text = unicodedata.normalize("NFKC", html.unescape(str(value or "")))
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    paragraphs: list[str] = []
    blank = False
    for line in lines:
        if line:
            paragraphs.append(line)
            blank = False
        elif paragraphs and not blank:
            paragraphs.append("")
            blank = True
    return "\n".join(paragraphs).strip()


def canonicalize_url(value: object) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    parsed = urlsplit(text)
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, "", ""))


def parse_nullable_int(value: object) -> int | None:
    text = normalize_text(value).replace(",", "")
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def normalize_datetime(value: object) -> str:
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
    match = ARTICLE_PATTERN.search(url)
    if match:
        return match.group(1)
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def _reject(row: dict, reason: str) -> dict:
    return {
        "source_file": row.get("__source_file", ""),
        "source_row": row.get("__source_row"),
        "url": normalize_text(row.get("url")),
        "title": normalize_text(row.get("title")),
        "reason": reason,
    }


def _normalize_row(row: dict) -> tuple[dict | None, dict | None]:
    url = canonicalize_url(row.get("url"))
    title = normalize_text(row.get("title"))
    content = normalize_text(row.get("content"))
    if not url:
        return None, _reject(row, "empty_url")
    if not title:
        return None, _reject(row, "empty_title")
    if not content:
        return None, _reject(row, "empty_content")
    article_id = article_id_from_url(url)
    record = {
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
        "text_quality": "short" if len(content) < SHORT_TEXT_LENGTH else "normal",
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "source_file": row.get("__source_file", ""),
        "source_row": row.get("__source_row"),
    }
    return record, None


def preprocess_rows(rows: list[dict]) -> tuple[list[dict], list[dict], dict]:
    accepted_by_url: dict[str, dict] = {}
    rejected: list[dict] = []
    duplicates = 0
    for row in rows:
        record, error = _normalize_row(row)
        if error:
            rejected.append(error)
            continue
        assert record is not None
        if record["url"] in accepted_by_url:
            previous = accepted_by_url[record["url"]]
            rejected.append({
                "source_file": previous["source_file"],
                "source_row": previous["source_row"],
                "url": previous["url"],
                "title": previous["title"],
                "reason": "duplicate_url_replaced",
            })
            duplicates += 1
        accepted_by_url[record["url"]] = record
    accepted = list(accepted_by_url.values())
    stats = {
        "input_rows": len(rows),
        "accepted_rows": len(accepted),
        "rejected_rows": len(rejected),
        "duplicate_rows": duplicates,
    }
    return accepted, rejected, stats
```

- [ ] **Step 4: 전처리 테스트가 통과하는지 확인한다**

Run: `uv run python -m unittest tests.inven_tip_rag.test_preprocess -v`

Expected: 5 tests, all PASS

- [ ] **Step 5: 전처리 계층을 커밋한다**

```powershell
git add src/inven_tip_rag/preprocess.py tests/inven_tip_rag/test_preprocess.py
git commit -m "feat: preprocess inven tip records"
```

---

### Task 3: 128토큰 제한을 지키는 청킹

**Files:**
- Create: `src/inven_tip_rag/chunking.py`
- Create: `tests/inven_tip_rag/fakes.py`
- Create: `tests/inven_tip_rag/test_chunking.py`

**Interfaces:**
- Consumes: 전처리 레코드 `list[dict]`, `tokenizer.encode(text, add_special_tokens)`
- Produces: `chunk_records(records, tokenizer, chunk_tokens=100, overlap_tokens=20, max_tokens=128) -> list[dict]`, `build_embedding_text(chunk, tokenizer, max_tokens=128) -> str`

- [ ] **Step 1: deterministic tokenizer와 청킹 실패 테스트를 작성한다**

```python
# tests/inven_tip_rag/fakes.py
import numpy as np


class FakeTokenizer:
    def encode(self, text, add_special_tokens=True, truncation=False):
        token_ids = [index + 10 for index, _ in enumerate(text.split())]
        return ([1] + token_ids + [2]) if add_special_tokens else token_ids


class FakeEmbeddingModel:
    def __init__(self):
        self.tokenizer = FakeTokenizer()

    def encode(self, texts, batch_size, show_progress_bar, convert_to_numpy, normalize_embeddings):
        rows = []
        for index, text in enumerate(texts, start=1):
            rows.append([float(index), float(len(text.split())), 1.0, 2.0])
        return np.asarray(rows, dtype=np.float32)
```

```python
# tests/inven_tip_rag/test_chunking.py
import unittest

from src.inven_tip_rag.chunking import build_embedding_text, chunk_records, count_tokens
from tests.inven_tip_rag.fakes import FakeTokenizer


class ChunkingTests(unittest.TestCase):
    def setUp(self):
        self.tokenizer = FakeTokenizer()
        self.record = {
            "document_id": "inven_tip_48082",
            "article_id": "48082",
            "url": "https://www.inven.co.kr/board/maple/2304/48082",
            "category": "실험",
            "title": "쿨타임 시스템 안내",
            "created_at": "2026-08-03T12:43:00",
            "views": 12988,
            "likes": 18,
            "content": " ".join(f"단어{index}" for index in range(30)),
            "text_quality": "normal",
        }

    def test_creates_stable_unique_ids_and_metadata(self):
        chunks = chunk_records([self.record], self.tokenizer, chunk_tokens=10, overlap_tokens=2, max_tokens=18)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0]["id"], "inven_tip_48082_0")
        self.assertEqual(chunks[0]["metadata"]["source"], "guide")
        self.assertEqual(chunks[0]["metadata"]["origin"], "inven_tip")
        self.assertEqual(len({item["id"] for item in chunks}), len(chunks))

    def test_every_embedding_text_fits_model_limit(self):
        chunks = chunk_records([self.record], self.tokenizer, chunk_tokens=10, overlap_tokens=2, max_tokens=18)
        for chunk in chunks:
            text = build_embedding_text(chunk, self.tokenizer, max_tokens=18)
            self.assertLessEqual(count_tokens(self.tokenizer, text, special_tokens=True), 18)

    def test_rejects_invalid_chunk_options(self):
        with self.assertRaisesRegex(ValueError, "chunk_tokens"):
            chunk_records([self.record], self.tokenizer, chunk_tokens=0, overlap_tokens=0)
        with self.assertRaisesRegex(ValueError, "overlap_tokens"):
            chunk_records([self.record], self.tokenizer, chunk_tokens=10, overlap_tokens=10)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트가 청킹 모듈 부재로 실패하는지 확인한다**

Run: `uv run python -m unittest tests.inven_tip_rag.test_chunking -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.inven_tip_rag.chunking'`

- [ ] **Step 3: 토큰 예산 기반 청킹을 구현한다**

```python
# src/inven_tip_rag/chunking.py
from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter


def count_tokens(tokenizer, text: str, special_tokens: bool = False) -> int:
    return len(tokenizer.encode(text, add_special_tokens=special_tokens, truncation=False))


def truncate_to_tokens(text: str, tokenizer, token_limit: int) -> str:
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
    raw_prefix = f"문서 제목: {metadata.get('name') or '제목 없음'}\n카테고리: {category}"
    return truncate_to_tokens(raw_prefix, tokenizer, prefix_tokens)


def build_embedding_text(chunk: dict, tokenizer, max_tokens: int = 128) -> str:
    prefix = chunk["metadata"]["embedding_prefix"]
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
    if chunk_tokens < 1:
        raise ValueError("chunk_tokens는 1 이상이어야 합니다.")
    if overlap_tokens < 0 or overlap_tokens >= chunk_tokens:
        raise ValueError("overlap_tokens는 0 이상 chunk_tokens 미만이어야 합니다.")
    chunks: list[dict] = []
    for record in records:
        prefix_budget = max(1, max_tokens - chunk_tokens - 2)
        base_metadata = {"name": record["title"], "section_title": record["category"]}
        prefix = _embedding_prefix(base_metadata, tokenizer, prefix_budget)
        body_budget = min(chunk_tokens, max_tokens - count_tokens(tokenizer, prefix) - 2)
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
        bodies = [body.strip() for body in splitter.split_text(record["content"]) if body.strip()]
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
            chunk = {"id": chunk_id, "page_content": body, "metadata": metadata}
            embedding_text = build_embedding_text(chunk, tokenizer, max_tokens=max_tokens)
            if count_tokens(tokenizer, embedding_text, special_tokens=True) > max_tokens:
                raise ValueError(f"임베딩 입력 토큰 제한 초과: {chunk_id}")
            chunks.append(chunk)
    if len({item["id"] for item in chunks}) != len(chunks):
        raise ValueError("중복 chunk_id가 생성됐습니다.")
    return chunks
```

- [ ] **Step 4: 청킹 테스트가 통과하는지 확인한다**

Run: `uv run python -m unittest tests.inven_tip_rag.test_chunking -v`

Expected: 3 tests, all PASS

- [ ] **Step 5: 청킹 계층을 커밋한다**

```powershell
git add src/inven_tip_rag/chunking.py tests/inven_tip_rag/fakes.py tests/inven_tip_rag/test_chunking.py
git commit -m "feat: chunk inven tips within model token limit"
```

---

### Task 4: 정규화 임베딩과 manifest

**Files:**
- Create: `src/inven_tip_rag/embedding.py`
- Create: `tests/inven_tip_rag/test_embedding.py`

**Interfaces:**
- Consumes: 청크 `list[dict]`, `SentenceTransformer` 호환 model
- Produces: `embed_chunks(chunks, model, batch_size=32, max_tokens=128) -> np.ndarray`, `build_manifest(...) -> dict`, `sha256_file(path) -> str`

- [ ] **Step 1: 벡터 순서·dtype·norm·manifest 실패 테스트를 작성한다**

```python
# tests/inven_tip_rag/test_embedding.py
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.inven_tip_rag.embedding import build_manifest, embed_chunks, sha256_file
from tests.inven_tip_rag.fakes import FakeEmbeddingModel


class EmbeddingTests(unittest.TestCase):
    def setUp(self):
        self.chunks = [
            {
                "id": f"inven_tip_1_{index}",
                "page_content": f"본문 {index}",
                "metadata": {"name": "제목", "section_title": "실험", "chunk_id": f"inven_tip_1_{index}"},
            }
            for index in range(2)
        ]

    def test_returns_float32_unit_vectors_in_chunk_order(self):
        vectors = embed_chunks(self.chunks, FakeEmbeddingModel(), batch_size=2, max_tokens=128)
        self.assertEqual(vectors.shape, (2, 4))
        self.assertEqual(vectors.dtype, np.float32)
        np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), np.ones(2), atol=1e-6)
        self.assertFalse(np.array_equal(vectors[0], vectors[1]))

    def test_builds_manifest_with_checksums_and_chunk_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            chunks_path = root / "chunks.json"
            vectors_path = root / "vectors.npy"
            chunks_path.write_text("[]", encoding="utf-8")
            np.save(vectors_path, np.ones((2, 4), dtype=np.float32))
            manifest = build_manifest(
                chunks=self.chunks,
                vectors=np.ones((2, 4), dtype=np.float32),
                chunks_path=chunks_path,
                vectors_path=vectors_path,
                model_name="fake-model",
                chunk_tokens=100,
                overlap_tokens=20,
                max_tokens=128,
            )
            self.assertEqual(manifest["chunk_ids"], ["inven_tip_1_0", "inven_tip_1_1"])
            self.assertEqual(manifest["embedding_dimension"], 4)
            self.assertEqual(manifest["chunks_sha256"], sha256_file(chunks_path))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트가 임베딩 모듈 부재로 실패하는지 확인한다**

Run: `uv run python -m unittest tests.inven_tip_rag.test_embedding -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.inven_tip_rag.embedding'`

- [ ] **Step 3: 임베딩 생성과 manifest 함수를 구현한다**

```python
# src/inven_tip_rag/embedding.py
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .chunking import build_embedding_text


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def embed_chunks(chunks: list[dict], model, batch_size: int = 32, max_tokens: int = 128) -> np.ndarray:
    if not chunks:
        raise ValueError("임베딩할 청크가 없습니다.")
    if batch_size < 1:
        raise ValueError("batch_size는 1 이상이어야 합니다.")
    texts = [build_embedding_text(chunk, model.tokenizer, max_tokens=max_tokens) for chunk in chunks]
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=False,
    ).astype(np.float32, copy=False)
    if vectors.ndim != 2 or vectors.shape[0] != len(chunks):
        raise ValueError(f"임베딩 shape 불일치: chunks={len(chunks)}, vectors={vectors.shape}")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if np.any(norms <= 1e-12):
        raise ValueError("0 벡터는 정규화할 수 없습니다.")
    normalized = (vectors / norms).astype(np.float32, copy=False)
    np.testing.assert_allclose(np.linalg.norm(normalized, axis=1), 1.0, atol=1e-5)
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
```

- [ ] **Step 4: 임베딩 테스트가 통과하는지 확인한다**

Run: `uv run python -m unittest tests.inven_tip_rag.test_embedding -v`

Expected: 2 tests, all PASS

- [ ] **Step 5: 임베딩 계층을 커밋한다**

```powershell
git add src/inven_tip_rag/embedding.py tests/inven_tip_rag/test_embedding.py
git commit -m "feat: generate normalized inven tip embeddings"
```

---

### Task 5: 원자적 산출물 저장과 단계별 CLI

**Files:**
- Create: `src/inven_tip_rag/pipeline.py`
- Create: `src/inven_tip_rag/__main__.py`
- Create: `tests/inven_tip_rag/test_pipeline.py`

**Interfaces:**
- Consumes: 입력 패턴, 출력 경로, tokenizer/model, 청킹·배치 옵션
- Produces: `run_preprocess()`, `run_chunk()`, `run_embed()`, `run_all()`, CLI 종료 코드 0 또는 오류 메시지

- [ ] **Step 1: fake model로 전체 파일 경계를 확인하는 실패 테스트를 작성한다**

```python
# tests/inven_tip_rag/test_pipeline.py
import csv
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.inven_tip_rag.pipeline import OutputPaths, run_all
from tests.inven_tip_rag.fakes import FakeEmbeddingModel


class PipelineTests(unittest.TestCase):
    def test_runs_all_stages_and_writes_consistent_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_path = root / "raw.csv"
            with raw_path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["url", "category", "title", "content"])
                writer.writeheader()
                writer.writerow({
                    "url": "https://www.inven.co.kr/board/maple/2304/1",
                    "category": "실험",
                    "title": "테스트 팁",
                    "content": " ".join(f"본문{index}" for index in range(30)),
                })
                writer.writerow({
                    "url": "https://www.inven.co.kr/board/maple/2304/2",
                    "category": "기타",
                    "title": "빈 글",
                    "content": "",
                })
            outputs = OutputPaths.under(root / "out")
            report = run_all(
                input_patterns=[str(raw_path)],
                outputs=outputs,
                model=FakeEmbeddingModel(),
                model_name="fake-model",
                chunk_tokens=10,
                overlap_tokens=2,
                max_tokens=18,
                batch_size=2,
            )
            processed = json.loads(outputs.processed.read_text(encoding="utf-8"))
            rejected = json.loads(outputs.rejected.read_text(encoding="utf-8"))
            chunks = json.loads(outputs.chunks.read_text(encoding="utf-8"))
            vectors = np.load(outputs.embeddings, allow_pickle=False)
            manifest = json.loads(outputs.manifest.read_text(encoding="utf-8"))
            self.assertEqual(len(processed), 1)
            self.assertEqual(rejected[0]["reason"], "empty_content")
            self.assertEqual(len(chunks), vectors.shape[0])
            self.assertEqual(manifest["embedding_count"], len(chunks))
            self.assertEqual(report["input_rows"], 2)
            self.assertTrue(outputs.report.is_file())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트가 파이프라인 모듈 부재로 실패하는지 확인한다**

Run: `uv run python -m unittest tests.inven_tip_rag.test_pipeline -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.inven_tip_rag.pipeline'`

- [ ] **Step 3: 원자적 JSON/NumPy 저장과 전체 파이프라인을 구현한다**

```python
# src/inven_tip_rag/pipeline.py
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


def atomic_write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, delete=False) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temporary = Path(stream.name)
    os.replace(temporary, path)


def atomic_save_numpy(path: Path, vectors: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, suffix=".npy", delete=False) as stream:
        np.save(stream, vectors, allow_pickle=False)
        temporary = Path(stream.name)
    os.replace(temporary, path)


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
    paths = discover_input_files(input_patterns)
    rows = load_csv_rows(paths)
    processed, rejected, preprocess_stats = preprocess_rows(rows)
    chunks = chunk_records(processed, model.tokenizer, chunk_tokens, overlap_tokens, max_tokens)
    vectors = embed_chunks(chunks, model, batch_size=batch_size, max_tokens=max_tokens)
    atomic_write_json(outputs.processed, processed)
    atomic_write_json(outputs.rejected, rejected)
    atomic_write_json(outputs.chunks, chunks)
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
    report = {
        **preprocess_stats,
        "input_files": [str(path) for path in paths],
        "chunk_count": len(chunks),
        "embedding_count": int(vectors.shape[0]),
        "embedding_dimension": int(vectors.shape[1]),
        "categories": dict(sorted(Counter(item["category"] for item in processed).items())),
        "short_text_rows": sum(item["text_quality"] == "short" for item in processed),
    }
    atomic_write_json(outputs.report, report)
    return report
```

- [ ] **Step 4: 단계별 함수로 `run_all()`을 분해한다**

Step 3의 `run_all()`을 다음 함수들로 교체한다. 이 구조는 전체 실행과 단계별 CLI가 같은 구현을 사용하게 한다.

```python
# src/inven_tip_rag/pipeline.py에 추가하고 기존 run_all을 교체
def read_json(path: Path):
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def run_preprocess(*, input_patterns, outputs: OutputPaths) -> dict:
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
    processed = read_json(outputs.processed)
    chunks = chunk_records(processed, tokenizer, chunk_tokens, overlap_tokens, max_tokens)
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
    chunks = read_json(outputs.chunks)
    vectors = embed_chunks(chunks, model, batch_size=batch_size, max_tokens=max_tokens)
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
    preprocess_stats = run_preprocess(input_patterns=input_patterns, outputs=outputs)
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
        "categories": dict(sorted(Counter(item["category"] for item in processed).items())),
        "short_text_rows": sum(item["text_quality"] == "short" for item in processed),
    }
    atomic_write_json(outputs.report, report)
    return report
```

- [ ] **Step 5: 네 가지 명령을 제공하는 argparse CLI를 구현한다**

```python
# src/inven_tip_rag/__main__.py
from __future__ import annotations

import argparse
from pathlib import Path

from sentence_transformers import SentenceTransformer

from . import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_TOKENS, MODEL_MAX_TOKENS, MODEL_NAME
from .pipeline import OutputPaths, run_all, run_chunk, run_embed, run_preprocess


def _add_output_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output-root", type=Path, default=Path("data"))


def _add_model_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model-name", default=MODEL_NAME)


def _add_chunk_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--chunk-tokens", type=int, default=DEFAULT_CHUNK_TOKENS)
    parser.add_argument("--overlap-tokens", type=int, default=DEFAULT_CHUNK_OVERLAP)
    parser.add_argument("--max-tokens", type=int, default=MODEL_MAX_TOKENS)


def _add_input_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", action="append", required=True, help="CSV 경로 또는 glob; 반복 지정 가능")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="메이플 인벤 팁 RAG 데이터 파이프라인")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preprocess_parser = subparsers.add_parser("preprocess", help="CSV 입력 검증과 전처리")
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

    all_parser = subparsers.add_parser("all", help="전처리·청킹·임베딩 전체 실행")
    _add_input_argument(all_parser)
    _add_output_argument(all_parser)
    _add_model_argument(all_parser)
    _add_chunk_arguments(all_parser)
    all_parser.add_argument("--batch-size", type=int, default=32)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    outputs = OutputPaths.under(args.output_root)
    if args.command == "preprocess":
        stats = run_preprocess(input_patterns=args.input, outputs=outputs)
        print(f"전처리 완료: {stats['accepted_rows']}개 유효, {stats['rejected_rows']}개 제외")
        return 0

    model = SentenceTransformer(args.model_name)
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
        print(f"임베딩 완료: {manifest['embedding_count']} x {manifest['embedding_dimension']}")
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
    print(f"완료: {report['accepted_rows']}개 문서, {report['chunk_count']}개 청크")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: 파이프라인 테스트와 CLI 도움말을 검증한다**

Run: `uv run python -m unittest tests.inven_tip_rag.test_pipeline -v`

Expected: 1 test, PASS

Run: `uv run python -m src.inven_tip_rag --help`

Expected: 도움말에 `preprocess`, `chunk`, `embed`, `all`이 모두 표시됨

- [ ] **Step 7: 전체 빠른 테스트를 실행한다**

Run: `uv run python -m unittest discover -s tests -p "test_*.py" -v`

Expected: Task 1~5에서 작성한 15개 테스트가 모두 PASS

- [ ] **Step 8: 파이프라인과 CLI를 커밋한다**

```powershell
git add src/inven_tip_rag/pipeline.py src/inven_tip_rag/__main__.py tests/inven_tip_rag/test_pipeline.py
git commit -m "feat: add inven tip RAG pipeline CLI"
```

---

### Task 6: 상세 사용 및 인계 문서

**Files:**
- Create: `docs/inven-tip-rag-pipeline.md`

**Interfaces:**
- Consumes: Task 1~5의 실제 CLI와 산출물 이름
- Produces: 팀원에게 전달 가능한 실행·검증·ChromaDB 인계 문서

- [ ] **Step 1: CLI와 코드의 실제 공개 인터페이스를 수집한다**

Run: `uv run python -m src.inven_tip_rag --help`

Run: `uv run python -m src.inven_tip_rag all --help`

Expected: 문서에 복사할 인자 이름과 기본값이 코드와 일치함

- [ ] **Step 2: 다음 내용으로 사용·인계 문서를 작성한다**

````markdown
# 메이플 인벤 팁 RAG 데이터 파이프라인

## 왜 이 파이프라인이 필요한가

메이플 인벤 팁과 노하우 게시글 CSV를 검색 가능한 RAG 자료로 변환한다. 원본을 바로 벡터 DB에 넣지 않고 입력 검증, 정규화, 토큰 청킹, 임베딩을 분리해 어느 단계에서 데이터가 제외되거나 변형됐는지 재현할 수 있게 한다. 이 저장소에서는 ChromaDB 적재 직전까지만 수행한다.

## 입력 데이터

현재 입력은 `ㅋㅌㅊ/maple_inven_rag_원본(1~10p).csv`다. `url`, `title`, `content`는 필수이고 `category`, `author`, `created_at`, `views`, `likes`는 선택이다. 추가 CSV가 생기면 `--input`을 반복하거나 `--input "data/raw/tips_*.csv"`처럼 glob을 사용한다. 모든 파일은 합친 뒤 URL 기준으로 중복 제거한다.

## 전체 실행

```powershell
uv run python -m src.inven_tip_rag all `
  --input "ㅋㅌㅊ/maple_inven_rag_원본(1~10p).csv" `
  --output-root data `
  --model-name jhgan/ko-sroberta-multitask `
  --chunk-tokens 100 `
  --overlap-tokens 20 `
  --max-tokens 128 `
  --batch-size 32
```

## 단계별 실행

```powershell
uv run python -m src.inven_tip_rag preprocess --input "ㅋㅌㅊ/maple_inven_rag_원본(1~10p).csv" --output-root data
uv run python -m src.inven_tip_rag chunk --output-root data --model-name jhgan/ko-sroberta-multitask --chunk-tokens 100 --overlap-tokens 20 --max-tokens 128
uv run python -m src.inven_tip_rag embed --output-root data --model-name jhgan/ko-sroberta-multitask --chunk-tokens 100 --overlap-tokens 20 --max-tokens 128 --batch-size 32
```

## 전처리 규칙

- HTML entity를 복원하고 Unicode NFKC를 적용한다.
- 줄바꿈은 `\n`으로 통일하고 문단은 유지하며 줄 내부 연속 공백만 줄인다.
- URL query와 fragment를 제거해 같은 게시글을 같은 키로 인식한다.
- 조회수와 추천수는 nullable integer, 파싱 가능한 날짜는 ISO 8601로 저장한다.
- URL·제목·본문이 비면 제외 사유 JSON에 기록한다.
- 100자 미만 본문은 버리지 않고 `text_quality=short`로 표시한다.
- 중복 URL에서는 입력 순서상 마지막 유효 레코드를 사용한다.

## 왜 불용어를 제거하지 않는가

`stopwords_ko.json`은 단어 빈도 분석에서 조사나 상투어를 제외하기 위한 사전이다. 문장 임베딩은 단어 사이의 문맥까지 사용하므로 불용어를 삭제하면 문장 의미가 달라질 수 있다. 이번 파이프라인은 원문 의미를 보존하고 불용어 사전을 읽지 않는다.

## 128토큰과 청킹

토큰은 글자 수나 띄어쓰기 단어 수와 동일하지 않다. 모델 tokenizer가 문장을 subword 단위로 나눈 결과가 토큰이며, `jhgan/ko-sroberta-multitask`의 SentenceTransformer 입력 한도는 128토큰이다. 한도를 넘는 뒷부분이 조용히 잘리는 일을 막기 위해 제목·카테고리 prefix와 특수 토큰의 길이를 먼저 빼고 남은 예산 안에서 본문을 청킹한다. 기본 본문 한도는 100토큰이고 인접 청크는 20토큰을 겹친다.

## 산출물

| 파일 | 내용 |
| --- | --- |
| `data/processed/maple_inven_tips_processed.json` | 유효 게시글과 정규화 필드 |
| `data/processed/maple_inven_tips_rejected.json` | 제외 위치·URL·제목·사유 |
| `data/RAG/maple_inven_tips_documents_chunked.json` | `id/page_content/metadata` 청크 |
| `data/RAG/maple_inven_tips_embeddings.npy` | 청크 순서와 같은 `float32` 정규화 벡터 |
| `data/RAG/maple_inven_tips_embeddings_manifest.json` | 모델, shape, checksum, chunk ID 순서 |
| `data/RAG/maple_inven_tips_pipeline_report.json` | 입력·유효·제외·청크 통계 |

manifest의 SHA-256으로 chunks JSON과 embeddings NPY가 같은 실행에서 나온 파일인지 검사한다.

## ChromaDB 담당자 인계

`documents_chunked.json[i]`와 `embeddings.npy[i]`는 반드시 같은 청크다. `id`를 Chroma ID, `page_content`를 document, `metadata`를 metadata, 같은 행의 벡터를 embedding으로 사용한다. 기존 가이드 라우팅에 포함되도록 `source=guide`를 사용하며 실제 출처는 `origin=inven_tip`과 URL로 구분한다. 이 파이프라인은 ChromaDB를 열거나 변경하지 않는다.

## 검증과 문제 해결

```powershell
uv run python -m unittest discover -s tests -p "test_*.py" -v
```

- 필수 컬럼 오류: CSV 헤더에 `url`, `title`, `content`가 있는지 확인한다.
- 모델 다운로드 오류: 네트워크 연결과 Hugging Face 캐시 권한을 확인한다.
- 메모리 부족: `--batch-size 16` 또는 `--batch-size 8`로 줄인다.
- 입력 파일 없음: 괄호와 `~`가 포함된 경로 전체를 따옴표로 감싼다.
````

- [ ] **Step 3: 문서 명령이 실제 CLI에서 파싱되는지 확인한다**

Run: `rg -n "python -m src.inven_tip_rag|stopwords|128토큰|ChromaDB" docs/inven-tip-rag-pipeline.md`

Expected: 전체 실행, 단계별 실행, 불용어, 128토큰, ChromaDB 인계 설명이 각각 검색됨

- [ ] **Step 4: 문서를 커밋한다**

```powershell
git add docs/inven-tip-rag-pipeline.md
git commit -m "docs: explain inven tip RAG pipeline"
```

---

### Task 7: 실제 300건 처리와 최종 무결성 검증

**Files:**
- Create: `data/processed/maple_inven_tips_processed.json`
- Create: `data/processed/maple_inven_tips_rejected.json`
- Create: `data/RAG/maple_inven_tips_documents_chunked.json`
- Create: `data/RAG/maple_inven_tips_embeddings.npy`
- Create: `data/RAG/maple_inven_tips_embeddings_manifest.json`
- Create: `data/RAG/maple_inven_tips_pipeline_report.json`
- Modify: `docs/inven-tip-rag-pipeline.md`

**Interfaces:**
- Consumes: `ㅋㅌㅊ/maple_inven_rag_원본(1~10p).csv`, 실제 `jhgan/ko-sroberta-multitask`
- Produces: ChromaDB 적재 직전의 검증된 실제 산출물 6개와 실행 결과 문서

- [ ] **Step 1: 전체 테스트를 새로 실행한다**

Run: `uv run python -m unittest discover -s tests -p "test_*.py" -v`

Expected: 모든 테스트 PASS

- [ ] **Step 2: 실제 데이터 전체 파이프라인을 실행한다**

Run:

```powershell
uv run python -m src.inven_tip_rag all `
  --input "ㅋㅌㅊ/maple_inven_rag_원본(1~10p).csv" `
  --output-root data `
  --model-name jhgan/ko-sroberta-multitask `
  --chunk-tokens 100 `
  --overlap-tokens 20 `
  --max-tokens 128 `
  --batch-size 32
```

Expected: 입력 300건을 읽고, 본문이 빈 1건을 제외 보고서에 기록하며, 299개 유효 문서와 1개 이상의 청크를 생성하고 종료 코드 0

- [ ] **Step 3: 산출물 무결성을 독립적으로 검증한다**

Run:

```powershell
uv run python -c "import json,numpy as np; from pathlib import Path; c=json.loads(Path('data/RAG/maple_inven_tips_documents_chunked.json').read_text(encoding='utf-8')); v=np.load('data/RAG/maple_inven_tips_embeddings.npy',allow_pickle=False); m=json.loads(Path('data/RAG/maple_inven_tips_embeddings_manifest.json').read_text(encoding='utf-8')); assert len(c)==v.shape[0]==m['embedding_count']; assert v.dtype==np.float32; assert len({x['id'] for x in c})==len(c); np.testing.assert_allclose(np.linalg.norm(v,axis=1),1.0,atol=1e-5); assert [x['id'] for x in c]==m['chunk_ids']; print({'chunks':len(c),'shape':v.shape,'dtype':str(v.dtype)})"
```

Expected: assertion failure 없이 실제 chunk 수, `(chunk_count, embedding_dimension)`, `float32` 출력

- [ ] **Step 4: 입력·출력 수량과 제외 사유를 확인한다**

Run:

```powershell
uv run python -c "import json; from pathlib import Path; p=json.loads(Path('data/processed/maple_inven_tips_processed.json').read_text(encoding='utf-8')); r=json.loads(Path('data/processed/maple_inven_tips_rejected.json').read_text(encoding='utf-8')); q=json.loads(Path('data/RAG/maple_inven_tips_pipeline_report.json').read_text(encoding='utf-8')); assert len(p)==299; assert any(x['reason']=='empty_content' for x in r); assert q['input_rows']==300 and q['accepted_rows']==299; print(q)"
```

Expected: `input_rows=300`, `accepted_rows=299`, `empty_content` 제외 확인

- [ ] **Step 5: 실제 결과를 사용 문서에 기록한다**

`docs/inven-tip-rag-pipeline.md`의 `실제 실행 결과` 절에 report의 입력 문서 수, 유효 문서 수, 제외 수, 청크 수, 임베딩 shape, dtype, 모델명을 그대로 기록한다. 측정값을 반올림하거나 예상치로 쓰지 않는다.

- [ ] **Step 6: 전체 변경 범위를 확인한다**

Run: `git status --short`

Expected: 기존 사용자 변경인 `chroma_db/chroma.sqlite3`, `data/Top-k/Top_k.ipynb`, `ㅋㅌㅊ/`와 이번 작업 파일이 구분되어 보임

Run: `git diff --check`

Expected: whitespace error 없음

- [ ] **Step 7: 실제 산출물과 결과 문서를 커밋한다**

```powershell
git add data/processed/maple_inven_tips_processed.json data/processed/maple_inven_tips_rejected.json data/RAG/maple_inven_tips_documents_chunked.json data/RAG/maple_inven_tips_embeddings.npy data/RAG/maple_inven_tips_embeddings_manifest.json data/RAG/maple_inven_tips_pipeline_report.json docs/inven-tip-rag-pipeline.md
git commit -m "data: build inven tip RAG embedding artifacts"
```

- [ ] **Step 8: 커밋 후 최종 검증을 반복한다**

Run: `uv run python -m unittest discover -s tests -p "test_*.py" -v`

Expected: 모든 테스트 PASS

Run: Task 7 Step 3의 무결성 명령

Expected: assertion failure 없이 동일한 chunk 수와 embedding shape 출력
