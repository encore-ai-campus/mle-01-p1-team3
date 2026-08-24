"""검색 평가 - Hit@K / Precision@K / Recall@K / MRR@K

평가셋(docs/rag_eval_gold_100.csv)의 gold 라벨이 article 전체 청크를 묶은
'문서 단위' 라벨이라, 두 눈금으로 함께 잰다.

  - chunk 단위 : 교안 정의 그대로. 라벨이 넓어 Recall 이 구조적으로 낮게 나온다.
  - article 단위 : 예측 청크와 gold 청크를 모두 article_id 로 접어서 잰다.
                   라벨이 붙은 단위와 눈금이 맞으므로 이쪽이 주 지표다.

사용:
    uv run python src/evaluate_retrieval.py            # 필터 없는 순수 벡터 검색
    uv run python src/evaluate_retrieval.py --filter   # retrieve.py 의 키워드 필터 포함
"""

import argparse
from pathlib import Path

import chromadb
import pandas as pd
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVALSET_PATH = PROJECT_ROOT / "docs" / "rag_eval_gold_100.csv"
CHROMA_PATH = str(PROJECT_ROOT / "chroma_db")
COLLECTION_NAME = "maplestory_guides"
EMBEDDING_MODEL_NAME = "jhgan/ko-sroberta-multitask"
KS = (3, 5, 10)


# =========================================================
# 네 가지 지표 - 교안 02 정의 그대로
# =========================================================

def hit_at_k(predicted, relevant, k):
    """상위 k개 중 정답이 하나라도 있으면 1, 없으면 0."""
    return 1 if any(p in relevant for p in predicted[:k]) else 0


def precision_at_k(predicted, relevant, k):
    """상위 k개 중 정답의 비율. 분모는 언제나 k."""
    return sum(1 for p in predicted[:k] if p in relevant) / k


def recall_at_k(predicted, relevant, k):
    """전체 정답 중 상위 k개가 건진 비율. 분모는 그 문항의 정답 개수."""
    if not relevant:
        return float("nan")
    return sum(1 for p in predicted[:k] if p in relevant) / len(relevant)


def mrr_at_k(predicted, relevant, k):
    """첫 정답 순위의 역수. 상위 k개 안에 없으면 0."""
    for rank, p in enumerate(predicted[:k], 1):
        if p in relevant:
            return 1 / rank
    return 0.0


# =========================================================
# 평가셋 / 색인 준비
# =========================================================

def load_chunk_to_article(collection):
    """chunk_id -> article_id 대응표. 예측과 gold 를 문서 단위로 접을 때 쓴다."""
    data = collection.get(include=["metadatas"])
    return {
        chunk_id: str(metadata.get("article_id"))
        for chunk_id, metadata in zip(data["ids"], data["metadatas"])
    }


def load_evalset(chunk_to_article):
    """gold 를 목록으로 되돌리고, 잴 수 없는 문항을 걸러낸다."""
    evalset = pd.read_csv(EVALSET_PATH)

    def parse_gold(cell):
        if pd.isna(cell):
            return []
        return [chunk.strip() for chunk in str(cell).split(";") if chunk.strip()]

    evalset["gold"] = evalset["gold_source_ids"].apply(parse_gold)

    # 점검 1) 색인에 없는 라벨 - 검색기 탓이 아니라 평가셋 탓인 실패의 원인이다.
    missing = {
        chunk
        for gold in evalset["gold"]
        for chunk in gold
        if chunk not in chunk_to_article
    }
    if missing:
        print(f"[경고] 색인에 없는 gold 청크 {len(missing)}개: {sorted(missing)[:5]} ...")

    # 점검 2) gold 가 비었거나 answerable=no 인 문항은 검색 지표로 잴 수 없다.
    no_gold = evalset["gold"].apply(len) == 0
    unanswerable = evalset["answerable"].astype(str).str.lower() != "yes"
    dropped = no_gold | unanswerable
    if dropped.any():
        print(f"[제외] gold 없음 {int(no_gold.sum())}문항 / "
              f"answerable=no {int(unanswerable.sum())}문항 -> 총 {int(dropped.sum())}문항 제외")

    evalset = evalset[~dropped].copy()
    evalset["gold_articles"] = evalset["gold"].apply(
        lambda gold: sorted({chunk_to_article[c] for c in gold if c in chunk_to_article})
    )
    evalset["정답청크수"] = evalset["gold"].apply(len)
    evalset["정답문서수"] = evalset["gold_articles"].apply(len)
    return evalset


# =========================================================
# 검색
# =========================================================

def make_search_fn(collection, embed_model, use_filter):
    """질문 -> 청크 id 목록(순위 순).

    K 마다 따로 검색한다. Chroma 의 HNSW 는 근사 검색이라 n_results 가 탐색 폭에
    영향을 주므로, K=10 으로 한 번 검색해 앞 3개를 자르면 K=3 검색과 결과가 달라진다
    (측정 결과 문항의 15% 에서 top-3 가 바뀌었다). 쓸 K 로 직접 검색해야 한다.
    """
    if use_filter:
        from retrieve import retrieve_top_k, get_search_filter

        def search_ids(question, k):
            results = retrieve_top_k(
                query=question,
                collection=collection,
                embed_model=embed_model,
                top_k=k,
                where=get_search_filter(question),
            )
            return [r["id"] for r in results]
    else:
        def search_ids(question, k):
            query_embedding = embed_model.encode([question], normalize_embeddings=True)
            result = collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=k,
                include=[],
            )
            return result["ids"][0]

    return search_ids


# =========================================================
# 평가
# =========================================================

def evaluate(evalset, search_fn, chunk_to_article):
    rows = []
    for row in evalset.itertuples():
        for k in KS:
            # 재는 K 로 그때그때 검색한다 -- 넓게 뽑아 자르면 다른 값이 나온다.
            predicted = search_fn(row.question, k)
            # 예측도 gold 와 같은 단위로 접는다. 순서는 유지하고 중복만 없앤다.
            predicted_articles = list(
                dict.fromkeys(chunk_to_article.get(c, c) for c in predicted)
            )

            for level, pred, gold in (
                ("chunk", predicted, row.gold),
                ("article", predicted_articles, row.gold_articles),
            ):
                rows.append({
                    "eval_id": row.eval_id,
                    "level": level,
                    "K": k,
                    "Hit": hit_at_k(pred, gold, k),
                    "P": precision_at_k(pred, gold, k),
                    "R": recall_at_k(pred, gold, k),
                    "MRR": mrr_at_k(pred, gold, k),
                })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--filter", action="store_true",
                        help="retrieve.py 의 키워드 metadata 필터를 적용해 평가")
    args = parser.parse_args()

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(name=COLLECTION_NAME)
    embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    chunk_to_article = load_chunk_to_article(collection)
    evalset = load_evalset(chunk_to_article)
    print(f"잰 문항 수: {len(evalset)} / 색인 청크 수: {collection.count()}")
    print(f"문항당 정답 청크 수 중앙값: {evalset['정답청크수'].median():.0f}"
          f" / 정답 문서 수 중앙값: {evalset['정답문서수'].median():.0f}\n")

    scores = evaluate(evalset, make_search_fn(collection, embed_model, args.filter),
                      chunk_to_article)

    summary = (scores.groupby(["level", "K"])[["Hit", "P", "R", "MRR"]]
               .mean().round(3))
    print("=== 평균 ===")
    print(summary.to_string(), "\n")

    # 평균보다 실패 문항이 먼저다.
    main_k = 5
    failed = scores[(scores["level"] == "article")
                    & (scores["K"] == main_k)
                    & (scores["Hit"] == 0)]["eval_id"].tolist()
    print(f"=== article 기준 Hit@{main_k} = 0 인 문항 {len(failed)}개 ===")
    print(failed)

    out_dir = PROJECT_ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    suffix = "filtered" if args.filter else "plain"
    scores.to_csv(out_dir / f"retrieval_scores_{suffix}.csv", index=False,
                  encoding="utf-8-sig")
    summary.to_csv(out_dir / f"retrieval_summary_{suffix}.csv", encoding="utf-8-sig")
    print(f"\n저장: output/retrieval_scores_{suffix}.csv, output/retrieval_summary_{suffix}.csv")


if __name__ == "__main__":
    main()
