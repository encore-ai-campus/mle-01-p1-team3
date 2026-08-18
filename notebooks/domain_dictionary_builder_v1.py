import pandas as pd

# ==============================
# 설정
# ==============================

INPUT_CSV = "../data/processed/doamain_dictionary/domain_dictionary_review.csv"
OUTPUT_CSV = "../data/processed/doamain_dictionary/domain_dictionary_v1.csv"

SOURCE = "inven"
VERSION = "v1"


# ==============================
# 유틸 함수
# ==============================

def clean_text(value):
    """NaN, 공백 등을 빈 문자열로 통일"""
    if pd.isna(value):
        return ""
    return str(value).strip()


def merge_aliases(*values):
    """
    aliases_candidate + 사람이 입력한 aliases를 병합
    구분자는 | 사용
    중복 제거
    """

    aliases = []

    for value in values:
        value = clean_text(value)

        if not value:
            continue

        # | 기준으로 별칭 분리
        for alias in value.split("|"):
            alias = alias.strip()

            if alias and alias not in aliases:
                aliases.append(alias)

    return " | ".join(aliases)


# ==============================
# 데이터 로드
# ==============================

df = pd.read_csv(INPUT_CSV)

print(f"전체 검수 데이터: {len(df)}개")


# ==============================
# keep 값 정규화
# ==============================

df["keep"] = (
    df["keep"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.upper()
)


# ==============================
# keep=Y만 선택
# ==============================

df_keep = df[df["keep"] == "Y"].copy()

print(f"keep=Y: {len(df_keep)}개")


# ==============================
# 최종 표준 용어 결정
# ==============================

def get_final_term(row):

    final_term = clean_text(row["final_term"])

    # 사람이 수정한 값이 있으면 우선 사용
    if final_term:
        return final_term

    # 없으면 자동 후보 사용
    return clean_text(row["canonical_term_candidate"])


df_keep["canonical_term"] = df_keep.apply(
    get_final_term,
    axis=1,
)


# ==============================
# 최종 카테고리 결정
# ==============================

def get_final_category(row):

    final_category = clean_text(row["final_category"])

    # 사람이 수정한 값이 있으면 우선
    if final_category:
        return final_category

    # 없으면 자동 추천 카테고리
    return clean_text(row["category_candidate"])


df_keep["category"] = df_keep.apply(
    get_final_category,
    axis=1,
)


# ==============================
# aliases 병합
# ==============================

df_keep["aliases_final"] = df_keep.apply(
    lambda row: merge_aliases(
        row["aliases_candidate"],
        row["aliases"],
    ),
    axis=1,
)


# ==============================
# 표준어 자신은 aliases에서 제거
# ==============================

def remove_canonical_from_aliases(row):

    canonical = row["canonical_term"]

    aliases = [
        alias.strip()
        for alias in row["aliases_final"].split("|")
        if alias.strip()
    ]

    aliases = [
        alias
        for alias in aliases
        if alias != canonical
    ]

    # 중복 제거
    aliases = list(dict.fromkeys(aliases))

    return " | ".join(aliases)


df_keep["aliases_final"] = df_keep.apply(
    remove_canonical_from_aliases,
    axis=1,
)


# ==============================
# 동일 표준어 중복 제거
# ==============================

df_keep = df_keep.drop_duplicates(
    subset=["canonical_term", "category"],
    keep="first",
).reset_index(drop=True)


# ==============================
# term_id 생성
# ==============================

df_keep["term_id"] = [
    f"TERM_{i:03d}"
    for i in range(1, len(df_keep) + 1)
]


# ==============================
# 메타데이터
# ==============================

df_keep["source"] = SOURCE
df_keep["version"] = VERSION


# ==============================
# 최종 컬럼
# ==============================

domain_dictionary = df_keep[
    [
        "term_id",
        "canonical_term",
        "aliases_final",
        "category",
        "source",
        "version",
    ]
].copy()

domain_dictionary = domain_dictionary.rename(
    columns={
        "aliases_final": "aliases"
    }
)


# ==============================
# 저장
# ==============================

domain_dictionary.to_csv(
    OUTPUT_CSV,
    index=False,
    encoding="utf-8-sig",
)


# ==============================
# 결과 확인
# ==============================

print()
print("===== Domain Dictionary 생성 완료 =====")
print(f"최종 용어 수: {len(domain_dictionary)}")
print()

print("카테고리 분포:")
print(domain_dictionary["category"].value_counts())

print()
print(domain_dictionary.head(10))

print()
print(f"저장 위치: {OUTPUT_CSV}")