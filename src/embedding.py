# [제공 코드] 이 단원에 필요한 라이브러리와 한글 폰트를 준비합니다.
import numpy as np
import json
import pandas as pd
import matplotlib.pyplot as plt
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from umap import UMAP
from pathlib import Path
from langchain_core.documents import Document

import platform

# 한글 폰트 — 실행 중인 OS 에 맞춰 자동 설정
if platform.system() == "Windows":
    KOREAN_FONT = "Malgun Gothic"
    FONT_PATH = "C:/Windows/Fonts/malgun.ttf"
elif platform.system() == "Darwin":  # macOS
    KOREAN_FONT = "AppleGothic"
    FONT_PATH = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
else:  # Linux (Colab 등)
    KOREAN_FONT = "NanumGothic"
    FONT_PATH = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"

plt.rcParams["font.family"] = KOREAN_FONT
plt.rcParams["axes.unicode_minus"] = False  # 마이너스(−) 부호 깨짐 방지

from pathlib import Path

# 현재 파일(data_embedding.py)의 위치 기준
BASE_DIR = Path(__file__).resolve().parent

# 프로젝트 구조에 맞는 데이터 폴더
DATA_DIR = (BASE_DIR / ".." / "data" / "RAG").resolve()

model = SentenceTransformer("jhgan/ko-sroberta-multitask")

# ### 가져온 문서가 document 타입이 아닐 경우 변환하는 코드
def load_documents(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = [
        Document(page_content=doc["page_content"], metadata=doc["metadata"])
        for doc in data
    ]
    return documents


guide_documents = load_documents(DATA_DIR / "maple_guides_documents.json")

jobs_documents = load_documents(DATA_DIR / "maple_jobs_documents.json")

items_documents = load_documents(DATA_DIR / "maple_items_documents.json")

all_documents = guide_documents + jobs_documents + items_documents


# ### 문서 통합, 임베딩
def add_chunk_ids(documents):
    for i, doc in enumerate(documents):

        source = doc.metadata.get("source", "unknown")

        # -------------------------
        # Guide
        # -------------------------
        if source == "guide":
            article_id = doc.metadata.get("article_id")
            chunk_index = doc.metadata.get("chunk_index", 0)

            document_id = f"guide_{article_id}"
            chunk_id = f"{document_id}_{chunk_index}"

        # -------------------------
        # Item
        # -------------------------
        elif source == "probability item":
            name = doc.metadata.get("name", "unknown")
            table_index = doc.metadata.get("table_index", 0)
            row_index = doc.metadata.get("row_index", 0)

            document_id = f"item_{name}_{table_index}"
            chunk_index = row_index
            chunk_id = f"{document_id}_{row_index}"

        # -------------------------
        # Job
        # -------------------------
        elif source == "job":
            job_id = doc.metadata.get("job_id")

            document_id = f"job_{job_id}"
            chunk_index = 0
            chunk_id = f"{document_id}_0"

        # -------------------------
        # 예상하지 못한 데이터
        # -------------------------
        else:
            document_id = f"unknown_{i}"
            chunk_index = 0
            chunk_id = f"{document_id}_0"

        # 기존 metadata에 추가
        doc.metadata["document_id"] = document_id
        doc.metadata["chunk_id"] = chunk_id
        doc.metadata["chunk_index"] = chunk_index

    return documents


all_documents = add_chunk_ids(all_documents)

for doc in all_documents[:5]:
    print(doc.metadata)

embeddings = model.encode(all_documents)

print("임베딩 배열 모양:", embeddings.shape)
