from __future__ import annotations

import argparse
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import pandas as pd

ALLOWED_CATEGORIES = ["아이템", "퀘스트", "몬스터", "직업", "시세", "기타"]
CATEGORY_QUOTA = {
    "아이템": 70,
    "직업": 35,
    "몬스터": 30,
    "퀘스트": 20,
    "시세": 20,
    "기타": 25,
}
REQUIRED_COLUMNS = {"category_clean", "title_clean", "content_clean"}

DEFAULT_STOPWORDS = {
    "질문",
    "문의",
    "궁금",
    "궁금합니다",
    "궁금해요",
    "어떻게",
    "어떤",
    "무슨",
    "추천",
    "해주세요",
    "해주세여",
    "알려주세요",
    "알려주세여",
    "부탁",
    "도와주세요",
    "정도",
    "사람",
    "생각",
    "가능",
    "가능한",
    "이번",
    "지금",
    "현재",
    "오늘",
    "내일",
    "관련",
    "경우",
    "이거",
    "저거",
    "그거",
    "뭔가",
    "뭐가",
    "뭐를",
    "뭐부터",
    "뭐",
    "제가",
    "저는",
    "나는",
    "님들",
    "혹시",
    "그냥",
    "정말",
    "진짜",
    "너무",
    "조금",
    "하면",
    "하려고",
    "하는데",
    "하나요",
    "할까요",
    "인가요",
    "일까요",
    "될까요",
    "있나요",
    "있을까요",
    "같아요",
    "같은데",
    "같습니다",
    "입니다",
    "합니다",
    "그리고",
    "근데",
    "그래서",
    "아니면",
    "또는",
    "대해서",
    "대한",
    "에서",
    "으로",
    "으로는",
    "이랑",
    "랑",
    "하고",
    "해서",
    "되나요",
    "됩니다",
    "때문에",
    "메린이",
    "복귀",
    "복귀유저",
    "뉴비",
    "초보",
    "고수님",
    "선생님",
    "형님들",
    "좋을까요",
    "부탁드립니다",
    "있습니다",
    "질문드립니다",
    "질문입니다",
    "안녕하세요",
    "감사합니다",
    "조언",
    "어디에",
    "vs",
}

DEFAULT_STOPWORDS.update(
    {
        "방법",
        "왼쪽",
        "오른쪽",
        "그래",
        "저번",
        "지난주",
        "제발",
        "답변",
        "방향",
        "생성",
        "기능",
        "마감",
        "종료",
        "싶은데",
        "있어요",
        "드립니다",
        "이번주",
        "맞나요",
        "얼마나",
        "떴는데",
        "모르겠어요",
        "팔릴까요",
        "질문있습니다",
        "질문드려요",
        "질문좀요",
        "고민",
        "선택",
        "계속",
        "원래",
        "보통",
    }
)

TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z0-9]+(?:[.+#-][가-힣A-Za-z0-9]+)*")


def _safe_text(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value)


PARTICLE_SUFFIXES = (
    "에서",
    "으로",
    "이랑",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "의",
    "에",
    "로",
    "와",
    "과",
    "도",
    "만",
    "랑",
)


def _strip_particle(token: str) -> str:
    if token in DEFAULT_STOPWORDS or token.lower() in DEFAULT_STOPWORDS:
        return token
    if not re.fullmatch(r"[가-힣]+", token):
        return token
    for suffix in PARTICLE_SUFFIXES:
        if token.endswith(suffix):
            stem = token[: -len(suffix)]
            if len(stem) >= 2:
                return stem
    return token


def tokenize(text: object) -> list[str]:
    """원문 표현을 보존하되 흔한 한국어 조사는 보수적으로 제거한다."""
    return [_strip_particle(token) for token in TOKEN_PATTERN.findall(_safe_text(text))]


def _is_valid_token(token: str, stopwords: set[str]) -> bool:
    if len(token) < 2:
        return False
    if token in stopwords:
        return False
    if token.isdigit():
        return False
    if token.lower() in {"http", "https", "www", "com"}:
        return False
    return True


def generate_ngrams(
    tokens: Iterable[str],
    max_n: int = 3,
    stopwords: set[str] | None = None,
) -> list[str]:
    """유효 토큰으로 1~max_n 연속 n-gram을 생성한다."""
    if max_n < 1:
        raise ValueError("max_n must be >= 1")
    stopwords = DEFAULT_STOPWORDS if stopwords is None else stopwords
    tokens = list(tokens)
    terms: list[str] = []

    for n in range(1, max_n + 1):
        for start in range(0, len(tokens) - n + 1):
            chunk = tokens[start : start + n]
            if not all(_is_valid_token(token, stopwords) for token in chunk):
                continue
            terms.append(" ".join(chunk))
    return terms


def validate_input(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    categories = set(df["category_clean"].dropna().astype(str).unique())
    invalid = categories - set(ALLOWED_CATEGORIES)
    if invalid:
        raise ValueError(f"Unexpected categories: {sorted(invalid)}")


def build_term_stats(
    df: pd.DataFrame,
    min_document_frequency: int = 3,
    max_ngram: int = 3,
    title_weight: int = 2,
    content_weight: int = 1,
    stopwords: set[str] | None = None,
) -> pd.DataFrame:
    """용어별 문서 빈도, 카테고리 빈도, 제목 가중 빈도와 점수를 계산한다."""
    validate_input(df)
    if min_document_frequency < 1:
        raise ValueError("min_document_frequency must be >= 1")

    stopwords = DEFAULT_STOPWORDS if stopwords is None else stopwords
    category_doc_totals = df["category_clean"].value_counts().to_dict()
    category_balance_alpha = 0.70

    document_frequency: Counter[str] = Counter()
    title_document_frequency: Counter[str] = Counter()
    weighted_frequency: Counter[str] = Counter()
    category_frequency: dict[str, Counter[str]] = defaultdict(Counter)
    examples: dict[str, list[str]] = defaultdict(list)

    for row in df.itertuples(index=False):
        category = str(getattr(row, "category_clean"))
        title = _safe_text(getattr(row, "title_clean"))
        content = _safe_text(getattr(row, "content_clean"))

        title_terms = generate_ngrams(
            tokenize(title), max_n=max_ngram, stopwords=stopwords
        )
        content_terms = generate_ngrams(
            tokenize(content), max_n=max_ngram, stopwords=stopwords
        )
        title_counts = Counter(title_terms)
        content_counts = Counter(content_terms)
        doc_terms = set(title_counts) | set(content_counts)

        for term in doc_terms:
            document_frequency[term] += 1
            category_frequency[term][category] += 1
            if len(examples[term]) < 3:
                example = title.strip() or content.strip()
                if example and example not in examples[term]:
                    examples[term].append(example[:300])

        for term in title_counts:
            title_document_frequency[term] += 1

        for term, count in title_counts.items():
            weighted_frequency[term] += count * title_weight
        for term, count in content_counts.items():
            weighted_frequency[term] += count * content_weight

    rows: list[dict[str, object]] = []
    for term, doc_freq in document_frequency.items():
        if doc_freq < min_document_frequency:
            continue

        per_category = category_frequency[term]
        association_scores = {
            category: (
                per_category[category]
                / (category_doc_totals.get(category, 1) ** category_balance_alpha)
                if category_doc_totals.get(category, 0) > 0
                else 0.0
            )
            for category in ALLOWED_CATEGORIES
        }
        dominant_category = max(
            ALLOWED_CATEGORIES,
            key=lambda category: (
                association_scores[category],
                -ALLOWED_CATEGORIES.index(category),
            ),
        )
        dominant_count = per_category[dominant_category]
        purity = dominant_count / doc_freq if doc_freq else 0.0
        association_total = sum(association_scores.values())
        category_confidence = (
            association_scores[dominant_category] / association_total
            if association_total
            else 0.0
        )
        title_df = title_document_frequency[term]

        # 정렬용 설명 가능한 휴리스틱: 문서 빈도 + 제목 출현 + 클래스 불균형 보정 후 카테고리 신뢰도.
        score = (
            math.log1p(doc_freq)
            * (1.0 + 0.30 * math.log1p(title_df))
            * (0.50 + 0.50 * category_confidence)
        )

        term_examples = examples[term]
        row: dict[str, object] = {
            "term": term,
            "ngram_n": term.count(" ") + 1,
            "document_frequency": doc_freq,
            "title_document_frequency": title_df,
            "weighted_frequency": weighted_frequency[term],
        }
        for category in ALLOWED_CATEGORIES:
            row[category] = per_category[category]
        row.update(
            {
                "dominant_category": dominant_category,
                "category_purity": purity,
                "category_confidence": category_confidence,
                "score": score,
                "example_1": term_examples[0] if len(term_examples) > 0 else "",
                "example_2": term_examples[1] if len(term_examples) > 1 else "",
                "example_3": term_examples[2] if len(term_examples) > 2 else "",
            }
        )
        rows.append(row)

    columns = [
        "term",
        "ngram_n",
        "document_frequency",
        "title_document_frequency",
        "weighted_frequency",
        *ALLOWED_CATEGORIES,
        "dominant_category",
        "category_purity",
        "category_confidence",
        "score",
        "example_1",
        "example_2",
        "example_3",
    ]
    result = pd.DataFrame(rows, columns=columns)
    if result.empty:
        return result

    return result.sort_values(
        ["score", "document_frequency", "title_document_frequency", "term"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)


def _alias_candidates(stats: pd.DataFrame) -> dict[str, str]:
    groups: dict[str, list[str]] = defaultdict(list)
    for term in stats["term"].astype(str):
        groups[term.replace(" ", "").lower()].append(term)

    aliases: dict[str, str] = {}
    for values in groups.values():
        unique = sorted(set(values), key=lambda x: (len(x), x))
        if len(unique) < 2:
            continue
        for term in unique:
            aliases[term] = " | ".join(value for value in unique if value != term)
    return aliases


def save_outputs(
    stats: pd.DataFrame,
    output_dir: str | Path,
) -> dict[str, Path]:
    """분석용/후보용/검수용 CSV 3개를 UTF-8-SIG로 저장한다."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stats_path = output_dir / "term_category_stats.csv"
    candidates_path = output_dir / "domain_term_candidates.csv"
    review_path = output_dir / "domain_dictionary_review.csv"

    if not stats.empty and "category_confidence" not in stats.columns:
        stats = stats.copy()
        stats["category_confidence"] = stats["category_purity"]

    aliases = _alias_candidates(stats) if not stats.empty else {}

    if stats.empty:
        candidates = pd.DataFrame(
            columns=[
                "canonical_term_candidate",
                "aliases_candidate",
                "category_candidate",
                "document_frequency",
                "title_document_frequency",
                "weighted_frequency",
                "category_purity",
                "category_confidence",
                "score",
                "example_1",
                "example_2",
                "example_3",
                "review_status",
            ]
        )
    else:
        candidates = stats[
            [
                "term",
                "dominant_category",
                "document_frequency",
                "title_document_frequency",
                "weighted_frequency",
                "category_purity",
                "category_confidence",
                "score",
                "example_1",
                "example_2",
                "example_3",
            ]
        ].copy()
        candidates = candidates.rename(
            columns={
                "term": "canonical_term_candidate",
                "dominant_category": "category_candidate",
            }
        )
        candidates.insert(
            1,
            "aliases_candidate",
            candidates["canonical_term_candidate"].map(aliases).fillna(""),
        )
        candidates["review_status"] = candidates.apply(
            lambda row: (
                "후보"
                if row["document_frequency"] >= 5 and row["category_confidence"] >= 0.60
                else "검수필요"
            ),
            axis=1,
        )

    if not candidates.empty:
        selected = []

        for category, quota in CATEGORY_QUOTA.items():
            category_df = candidates[candidates["category_candidate"] == category]

            confirmed = category_df[category_df["review_status"] == "후보"]

            needs_review = category_df[category_df["review_status"] == "검수필요"]

            # 신뢰도 높은 후보 우선
            selected_category = confirmed.head(quota)

            # quota가 부족하면 검수필요에서 보충
            remaining = quota - len(selected_category)

            if remaining > 0:
                selected_category = pd.concat(
                    [
                        selected_category,
                        needs_review.head(remaining),
                    ],
                    ignore_index=True,
                )

            selected.append(selected_category)

        candidates = pd.concat(selected, ignore_index=True)

    review = candidates.copy()
    review["keep"] = ""
    review["final_term"] = ""
    review["final_category"] = ""
    review["aliases"] = ""
    review["review_note"] = ""

    stats.to_csv(stats_path, index=False, encoding="utf-8-sig")
    candidates.to_csv(candidates_path, index=False, encoding="utf-8-sig")
    review.to_csv(review_path, index=False, encoding="utf-8-sig")

    return {"candidates": candidates_path, "stats": stats_path, "review": review_path}


def run(
    input_csv: str | Path,
    output_dir: str | Path,
    min_document_frequency: int = 3,
    max_ngram: int = 3,
) -> dict[str, Path]:
    df = pd.read_csv(input_csv)
    stats = build_term_stats(
        df,
        min_document_frequency=min_document_frequency,
        max_ngram=max_ngram,
    )
    return save_outputs(stats, output_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build MapleStory domain-term candidates from cleaned Inven data."
    )
    parser.add_argument("input_csv", help="Path to inven_merged_sample.csv")
    parser.add_argument(
        "--output-dir",
        default="domain_dictionary_output",
        help="Directory for output CSV files",
    )
    parser.add_argument(
        "--min-df", type=int, default=3, help="Minimum document frequency (default: 3)"
    )
    parser.add_argument(
        "--max-ngram",
        type=int,
        default=3,
        choices=[1, 2, 3],
        help="Maximum n-gram size",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = run(
        input_csv=args.input_csv,
        output_dir=args.output_dir,
        min_document_frequency=args.min_df,
        max_ngram=args.max_ngram,
    )
    print("Generated files:")
    for key, path in paths.items():
        print(f"- {key}: {path}")


if __name__ == "__main__":
    main()
