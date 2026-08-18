from pathlib import Path
import re

import pandas as pd

# ============================================================
# 1. 경로 설정
# ============================================================

INVEN_PATH = "../data/processed/inven_merged_sample.csv"
DICTIONARY_PATH = "../data/processed/doamain_dictionary/domain_dictionary_v1.csv"

OUTPUT_DIR = Path("../data/processed/doamain_dictionary")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. 기본 설정
# ============================================================

REQUIRED_INVEN_COLUMNS = {
    "category_clean",
    "title_clean",
    "content_clean",
}

REQUIRED_DICTIONARY_COLUMNS = {
    "term_id",
    "canonical_term",
    "aliases",
    "category",
}


# ============================================================
# 3. 텍스트 정리 함수
# ============================================================


def safe_text(value):
    """NaN을 빈 문자열로 처리"""
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_text(text):
    """
    매칭용 텍스트 정규화

    - 소문자 변환
    - 여러 공백을 하나로 통일
    """
    text = safe_text(text).lower()
    text = re.sub(r"\s+", " ", text)

    return text


# ============================================================
# 4. aliases 파싱
# ============================================================


def parse_aliases(value):
    """
    aliases 컬럼:
    잠재 | 윗잠 | 잠재옵션

    형태를 리스트로 변환
    """

    value = safe_text(value)

    if not value:
        return []

    aliases = []

    for alias in value.split("|"):
        alias = alias.strip()

        if alias:
            aliases.append(alias)

    return aliases


# ============================================================
# 5. 사전 데이터 검증
# ============================================================


def validate_dictionary(df):
    missing = REQUIRED_DICTIONARY_COLUMNS - set(df.columns)

    if missing:
        raise ValueError(
            f"domain_dictionary_v1.csv에 필요한 컬럼이 없습니다: {sorted(missing)}"
        )


def validate_inven(df):
    missing = REQUIRED_INVEN_COLUMNS - set(df.columns)

    if missing:
        raise ValueError(
            f"inven_merged_sample.csv에 필요한 컬럼이 없습니다: {sorted(missing)}"
        )


# ============================================================
# 6. 검색용 사전 구조 생성
# ============================================================


def build_dictionary_entries(dictionary_df):
    """
    각 표준어에 대해

    canonical_term
    +
    aliases

    를 검색 후보로 생성
    """

    entries = []

    for _, row in dictionary_df.iterrows():

        canonical_term = safe_text(row["canonical_term"])
        category = safe_text(row["category"])
        term_id = safe_text(row["term_id"])

        if not canonical_term:
            continue

        aliases = parse_aliases(row["aliases"])

        search_terms = [
            canonical_term,
            *aliases,
        ]

        # 빈 값 / 중복 제거
        search_terms = list(
            dict.fromkeys(term.strip() for term in search_terms if term.strip())
        )

        # 긴 표현부터 검사
        # 예: "제네시스 무기"를 "무기"보다 먼저
        search_terms.sort(
            key=len,
            reverse=True,
        )

        entries.append(
            {
                "term_id": term_id,
                "canonical_term": canonical_term,
                "category": category,
                "search_terms": search_terms,
            }
        )

    return entries


# ============================================================
# 7. 문서 하나에서 도메인 용어 찾기
# ============================================================


def match_document(text, dictionary_entries):

    normalized_text = normalize_text(text)

    matched_terms = []
    matched_term_ids = []
    matched_categories = []
    matched_expressions = []

    for entry in dictionary_entries:

        found_expression = None

        for expression in entry["search_terms"]:

            expression_normalized = normalize_text(expression)

            if expression_normalized in normalized_text:
                found_expression = expression
                break

        if found_expression is None:
            continue

        matched_terms.append(entry["canonical_term"])

        matched_term_ids.append(entry["term_id"])

        matched_categories.append(entry["category"])

        matched_expressions.append(found_expression)

    # 중복 제거
    matched_terms = list(dict.fromkeys(matched_terms))
    matched_term_ids = list(dict.fromkeys(matched_term_ids))
    matched_categories = list(dict.fromkeys(matched_categories))
    matched_expressions = list(dict.fromkeys(matched_expressions))

    return {
        "matched_term_ids": " | ".join(matched_term_ids),
        "matched_terms": " | ".join(matched_terms),
        "matched_categories": " | ".join(matched_categories),
        "matched_expressions": " | ".join(matched_expressions),
        "match_count": len(matched_terms),
        "is_matched": len(matched_terms) > 0,
    }


# ============================================================
# 8. 원본 데이터에 도메인 사전 적용
# ============================================================


def apply_dictionary(
    inven_df,
    dictionary_entries,
):

    result_df = inven_df.copy()

    # 제목 + 본문 결합
    result_df["_match_text"] = (
        result_df["title_clean"].fillna("").astype(str)
        + " "
        + result_df["content_clean"].fillna("").astype(str)
    )

    match_results = result_df["_match_text"].apply(
        lambda text: match_document(
            text,
            dictionary_entries,
        )
    )

    match_df = pd.DataFrame(match_results.tolist())

    result_df = pd.concat(
        [
            result_df.reset_index(drop=True),
            match_df.reset_index(drop=True),
        ],
        axis=1,
    )

    result_df = result_df.drop(columns=["_match_text"])

    return result_df


# ============================================================
# 9. Coverage 계산
# ============================================================


def calculate_coverage(tagged_df):

    total_documents = len(tagged_df)

    matched_documents = int(tagged_df["is_matched"].sum())

    unmatched_documents = total_documents - matched_documents

    coverage = matched_documents / total_documents * 100 if total_documents > 0 else 0

    summary = pd.DataFrame(
        [
            {
                "type": "전체",
                "category": "전체",
                "total_documents": total_documents,
                "matched_documents": matched_documents,
                "unmatched_documents": unmatched_documents,
                "coverage_percent": round(
                    coverage,
                    2,
                ),
            }
        ]
    )

    # --------------------------------------------------------
    # 기존 인벤 카테고리별 Coverage
    # --------------------------------------------------------

    category_rows = []

    for category, group in tagged_df.groupby("category_clean"):

        category_total = len(group)

        category_matched = int(group["is_matched"].sum())

        category_unmatched = category_total - category_matched

        category_coverage = (
            category_matched / category_total * 100 if category_total > 0 else 0
        )

        category_rows.append(
            {
                "type": "카테고리",
                "category": category,
                "total_documents": category_total,
                "matched_documents": category_matched,
                "unmatched_documents": category_unmatched,
                "coverage_percent": round(
                    category_coverage,
                    2,
                ),
            }
        )

    category_summary = pd.DataFrame(category_rows)

    summary = pd.concat(
        [
            summary,
            category_summary,
        ],
        ignore_index=True,
    )

    return summary


# ============================================================
# 10. 도메인 용어별 사용 빈도
# ============================================================


def calculate_term_usage(
    tagged_df,
    dictionary_df,
):

    usage_counter = {}

    for terms in tagged_df["matched_terms"]:

        if pd.isna(terms) or not str(terms).strip():
            continue

        for term in str(terms).split("|"):

            term = term.strip()

            if not term:
                continue

            usage_counter[term] = usage_counter.get(term, 0) + 1

    usage_df = dictionary_df[
        [
            "term_id",
            "canonical_term",
            "category",
        ]
    ].copy()

    usage_df["matched_document_count"] = (
        usage_df["canonical_term"].map(usage_counter).fillna(0).astype(int)
    )

    usage_df = usage_df.sort_values(
        "matched_document_count",
        ascending=False,
    )

    return usage_df


# ============================================================
# 11. 실행
# ============================================================


def main():

    # --------------------------------------------------------
    # CSV 로드
    # --------------------------------------------------------

    inven_df = pd.read_csv(INVEN_PATH)

    dictionary_df = pd.read_csv(DICTIONARY_PATH)

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    validate_inven(inven_df)
    validate_dictionary(dictionary_df)

    print("=" * 50)
    print("데이터 로드")
    print("=" * 50)

    print(f"인벤 문서 수: " f"{len(inven_df):,}")

    print(f"도메인 사전 용어 수: " f"{len(dictionary_df):,}")

    # --------------------------------------------------------
    # 검색 사전 생성
    # --------------------------------------------------------

    dictionary_entries = build_dictionary_entries(dictionary_df)

    # --------------------------------------------------------
    # 전체 인벤 데이터 매칭
    # --------------------------------------------------------

    tagged_df = apply_dictionary(
        inven_df,
        dictionary_entries,
    )

    # --------------------------------------------------------
    # Coverage
    # --------------------------------------------------------

    coverage_df = calculate_coverage(tagged_df)

    # --------------------------------------------------------
    # 미매칭 문서
    # --------------------------------------------------------

    unmatched_df = tagged_df[tagged_df["is_matched"] == False].copy()

    # --------------------------------------------------------
    # 용어별 사용 빈도
    # --------------------------------------------------------

    term_usage_df = calculate_term_usage(
        tagged_df,
        dictionary_df,
    )

    # ========================================================
    # 12. 저장
    # ========================================================

    tagged_path = OUTPUT_DIR / "inven_domain_tagged.csv"

    unmatched_path = OUTPUT_DIR / "inven_domain_unmatched.csv"

    coverage_path = OUTPUT_DIR / "domain_coverage_summary.csv"

    usage_path = OUTPUT_DIR / "domain_term_usage.csv"

    tagged_df.to_csv(
        tagged_path,
        index=False,
        encoding="utf-8-sig",
    )

    unmatched_df.to_csv(
        unmatched_path,
        index=False,
        encoding="utf-8-sig",
    )

    coverage_df.to_csv(
        coverage_path,
        index=False,
        encoding="utf-8-sig",
    )

    term_usage_df.to_csv(
        usage_path,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # 13. 결과 출력
    # ========================================================

    total = len(tagged_df)

    matched = int(tagged_df["is_matched"].sum())

    unmatched = total - matched

    coverage = matched / total * 100 if total else 0

    print()
    print("=" * 50)
    print("Coverage 결과")
    print("=" * 50)

    print(f"전체 문서: " f"{total:,}")

    print(f"매칭 문서: " f"{matched:,}")

    print(f"미매칭 문서: " f"{unmatched:,}")

    print(f"Coverage: " f"{coverage:.2f}%")

    print()
    print("카테고리별 Coverage")
    print(coverage_df.to_string(index=False))

    print()
    print("=" * 50)
    print("생성 파일")
    print("=" * 50)

    print(f"전체 태깅 데이터: " f"{tagged_path}")

    print(f"미매칭 데이터: " f"{unmatched_path}")

    print(f"Coverage 통계: " f"{coverage_path}")

    print(f"용어 사용 빈도: " f"{usage_path}")


if __name__ == "__main__":
    main()
