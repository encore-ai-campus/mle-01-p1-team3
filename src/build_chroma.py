"""
chroma_db를 소스 JSON에서 다시 만듭니다.

HNSW 벡터 인덱스가 sqlite 메타데이터와 어긋나면
collection.get(include=["embeddings"]) / collection.query()가
"Error finding id"로 실패합니다. 이 스크립트로 전체를 재생성합니다.

실행: python src/build_chroma.py
"""

import json
import shutil
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "RAG"
CHROMA_PATH = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "maplestory_guides"
EMBEDDING_MODEL_NAME = "jhgan/ko-sroberta-multitask"

SOURCES = [
    ("maple_guides_documents_chunked.json", "guide"),
    ("maple_jobs_documents.json", "jobs"),
    ("maple_items_documents.json", "items"),
]


def load_documents():
    documents = []

    for file_name, source in SOURCES:
        with open(DATA_DIR / file_name, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            metadata = dict(item["metadata"])
            metadata["source"] = source
            documents.append((item["page_content"], metadata))

    return documents


def reset_chroma_dir():
    """
    기존 DB 디렉터리를 지웁니다.

    Jupyter 커널 등 다른 프로세스가 DB를 열어 두면 Windows에서
    파일 삭제가 실패하므로, 임베딩 계산 전에 먼저 확인합니다.
    """
    if not CHROMA_PATH.exists():
        return

    print(f"기존 DB 삭제: {CHROMA_PATH}")

    try:
        shutil.rmtree(CHROMA_PATH)
    except PermissionError as error:
        message = (
            "기존 chroma_db를 삭제하지 못했습니다. "
            "chroma_db를 열고 있는 노트북 커널을 모두 종료한 뒤 다시 실행하세요. "
            f"원인: {error}"
        )
        raise SystemExit(message)


def main():
    reset_chroma_dir()

    documents = load_documents()
    print(f"문서 수: {len(documents)}")

    ids = [f"chunk_{index}" for index in range(len(documents))]
    texts = [text for text, _ in documents]
    metadatas = []

    for index, (_, metadata) in enumerate(documents):
        metadata.setdefault("chunk_index", index)
        metadatas.append(metadata)

    print("임베딩 모델 로드 중...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    print("임베딩 계산 중...")
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=32,
        show_progress_bar=True,
    )
    print("임베딩 shape:", embeddings.shape)

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    batch_size = 500

    for start in range(0, len(ids), batch_size):
        end = start + batch_size
        collection.add(
            ids=ids[start:end],
            documents=texts[start:end],
            metadatas=metadatas[start:end],
            embeddings=embeddings[start:end].tolist(),
        )
        print(f"저장 {min(end, len(ids))}/{len(ids)}")

    print("collection.count():", collection.count())


if __name__ == "__main__":
    main()
