from pathlib import Path

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer


# =========================================================
# 기본 설정
# =========================================================

EMBEDDING_MODEL_NAME = "jhgan/ko-sroberta-multitask"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHROMA_PATH = str(PROJECT_ROOT / "chroma_db")
COLLECTION_NAME = "maplestory_guides"


# =========================================================
# 모델 / DB 연결
# =========================================================

embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_collection(name=COLLECTION_NAME)


# =========================================================
# 질문 분류 키워드
# =========================================================

JOB_KEYWORDS = [
    "직업",
    "직업추천",
    "직업 추천",
    "주스탯",
    "주 스탯",
    "주스텟",
    "무기",
    "전직",
    "전사",
    "마법사",
    "궁수",
    "도적",
    "해적",
    "히어로",
    "팔라딘",
    "다크나이트",
    "아크메이지",
    "비숍",
    "보우마스터",
    "신궁",
    "패스파인더",
    "나이트로드",
    "섀도어",
    "듀얼블레이드",
    "바이퍼",
    "캡틴",
    "캐논슈터",
    "소울마스터",
    "미하일",
    "플레임위자드",
    "윈드브레이커",
    "나이트워커",
    "스트라이커",
    "아란",
    "에반",
    "메르세데스",
    "팬텀",
    "루미너스",
    "은월",
    "데몬슬레이어",
    "데몬어벤져",
    "블래스터",
    "배틀메이지",
    "와일드헌터",
    "메카닉",
    "제논",
    "카이저",
    "카인",
    "카데나",
    "엔젤릭버스터",
    "아델",
    "일리움",
    "아크",
    "칼리",
    "호영",
    "라라",
    "제로",
    "키네시스",
    "렌",
]

ITEM_KEYWORDS = [
    "확률",
    "아이템",
    "장비",
    "큐브",
    "잠재",
    "잠재능력",
    "에디셔널",
    "스타포스",
    "강화",
    "획득 확률",
]


def get_search_filter(query):
    """질문 키워드에 따라 검색할 source를 결정합니다."""
    query = query.strip().lower()

    if any(keyword.lower() in query for keyword in JOB_KEYWORDS):
        return {"source": "jobs"}

    if any(keyword.lower() in query for keyword in ITEM_KEYWORDS):
        return {"source": "items"}

    return None


def _validate_query(query, top_k):
    query = query.strip()

    if not query:
        raise ValueError("검색 질문이 비어 있습니다.")

    if top_k < 1:
        raise ValueError("top_k는 1 이상이어야 합니다.")

    return query


def _get_filtered_documents(collection, where):
    """
    source에 해당하는 문서와 임베딩을 가져옵니다.

    우선 Chroma의 get(where=...)를 사용하고, 이 단계에서도 필터 오류가
    발생하면 전체 문서를 가져온 뒤 Python에서 metadata를 필터링합니다.
    """
    include = ["documents", "metadatas", "embeddings"]

    try:
        return collection.get(where=where, include=include)
    except Exception:
        data = collection.get(include=include)
        source = where.get("source")

        selected_indices = [
            index
            for index, metadata in enumerate(data["metadatas"])
            if metadata.get("source") == source
        ]

        return {
            "ids": [data["ids"][index] for index in selected_indices],
            "documents": [data["documents"][index] for index in selected_indices],
            "metadatas": [data["metadatas"][index] for index in selected_indices],
            "embeddings": [data["embeddings"][index] for index in selected_indices],
        }


def _retrieve_with_metadata_filter(
    query,
    collection,
    embed_model,
    top_k,
    where,
):
    """
    Chroma의 query(where=...)를 사용하지 않고,
    source별 문서를 가져온 뒤 cosine similarity로 Top-K를 계산합니다.
    """
    data = _get_filtered_documents(collection, where)

    if not data["ids"]:
        return []

    doc_embeddings = np.asarray(data["embeddings"], dtype=np.float32)

    if doc_embeddings.ndim != 2:
        raise ValueError(
            f"문서 임베딩 차원 오류: {doc_embeddings.shape}"
        )

    query_embedding = embed_model.encode(
        [query],
        normalize_embeddings=True,
    )
    query_embedding = np.asarray(query_embedding, dtype=np.float32)

    if query_embedding.ndim != 2 or query_embedding.shape[0] != 1:
        raise ValueError(
            f"질문 임베딩 차원 오류: {query_embedding.shape}"
        )

    query_vector = query_embedding[0]

    if doc_embeddings.shape[1] != query_vector.shape[0]:
        raise ValueError(
            "질문 임베딩과 문서 임베딩의 차원이 다릅니다: "
            f"query={query_vector.shape[0]}, docs={doc_embeddings.shape[1]}"
        )

    # DB 임베딩이 정규화되어 있지 않은 경우에도 cosine similarity가
    # 올바르게 계산되도록 문서 임베딩을 한 번 더 정규화합니다.
    norms = np.linalg.norm(doc_embeddings, axis=1, keepdims=True)
    doc_embeddings = doc_embeddings / np.clip(norms, 1e-12, None)

    scores = doc_embeddings @ query_vector
    result_count = min(top_k, len(scores))
    top_indices = np.argsort(scores)[::-1][:result_count]

    results = []

    for rank, index in enumerate(top_indices, start=1):
        score = float(scores[index])

        results.append(
            {
                "rank": rank,
                "id": data["ids"][index],
                "page_content": data["documents"][index],
                "metadata": data["metadatas"][index],
                "distance": 1.0 - score,
                "score": score,
            }
        )

    return results


def retrieve_top_k(
    query,
    collection,
    embed_model,
    top_k=8,
    where=None,
):
    query = _validate_query(query, top_k)

    if collection.count() == 0:
        return []

    # metadata filter가 있는 경우 Chroma query(where=...)를 사용하지 않습니다.
    if where:
        return _retrieve_with_metadata_filter(
            query=query,
            collection=collection,
            embed_model=embed_model,
            top_k=top_k,
            where=where,
        )

    # 전체 검색은 기존 Chroma vector query를 그대로 사용합니다.
    query_embedding = embed_model.encode(
        [query],
        normalize_embeddings=True,
    )

    if query_embedding.ndim != 2 or query_embedding.shape[0] != 1:
        raise ValueError(
            f"질문 임베딩 차원 오류: {query_embedding.shape}"
        )

    document_count = collection.count()

    raw_results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=min(top_k, document_count),
        include=["documents", "metadatas", "distances"],
    )

    results = []

    for index, chunk_id in enumerate(raw_results["ids"][0]):
        distance = raw_results["distances"][0][index]

        results.append(
            {
                "rank": index + 1,
                "id": chunk_id,
                "page_content": raw_results["documents"][0][index],
                "metadata": raw_results["metadatas"][0][index],
                "distance": distance,
                "score": 1.0 - distance,
            }
        )

    return results


def search_documents(
    query,
    collection,
    embed_model,
    top_k=5,
):
    where = get_search_filter(query)

    if where is None:
        print("검색 범위: 전체 문서")
    else:
        print(f"검색 범위: {where['source']}")

    return retrieve_top_k(
        query=query,
        collection=collection,
        embed_model=embed_model,
        top_k=top_k,
        where=where,
    )


# =========================================================
# build_context에서 사용할 최종 인터페이스
# =========================================================

def retrieve(query, k=5):
    return search_documents(
        query=query,
        collection=collection,
        embed_model=embed_model,
        top_k=k,
    )
