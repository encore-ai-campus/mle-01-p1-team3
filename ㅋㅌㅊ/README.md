# 메이플 인벤 팁 RAG 노트북 파이프라인

이 폴더는 `maple_inven_rag_원본(1~10p).csv`를 전처리하고, 청킹하고, 임베딩한 뒤 ChromaDB 적재 직전 파일까지 생성한다.

크롤링과 ChromaDB 적재는 포함하지 않는다. 불용어 제거도 임베딩 문맥을 훼손할 수 있어 적용하지 않는다.

## 실행 파일

`inven_tip_rag` 폴더의 노트북을 번호 순서대로 연다.

1. `01_input.ipynb`: CSV 탐색, 필수 컬럼 검증, 원본 미리보기
2. `02_preprocess.ipynb`: 텍스트·URL·날짜·숫자 정규화, 제외 행 확인
3. `03_chunking.ipynb`: tokenizer 기준 청킹, 청크·토큰 수 확인
4. `04_embedding.ipynb`: 모델 로드, 임베딩 생성, shape·벡터 샘플 확인
5. `05_pipeline.ipynb`: 전체 파일 무결성 검증, 최종 보고서 생성

`main.ipynb`나 `.py` 파일은 사용하지 않는다. 각 노트북은 이전 단계가 저장한 파일을 읽으므로 서로 다른 커널에서 실행해도 된다.

## VS Code 실행 방법

각 노트북을 열고 오른쪽 위의 **모두 실행**을 누른다. Python 커널은 프로젝트의 `.venv`를 선택한다.

중간 단계를 건너뛰면 필요한 파일이 없다는 메시지가 나온다. 이때는 바로 앞 번호의 노트북부터 실행한다.

`output` 폴더를 삭제했더라도 `01`부터 `05`까지 다시 실행하면 전부 재생성된다. 임베딩 노트북은 CPU에서 약 10분 걸릴 수 있다.

## 데이터 흐름

```text
원본 CSV
  → output/intermediate 원본 스냅샷·설정
  → output/processed 전처리·제외 JSON
  → output/RAG 청크 JSON
  → output/RAG 임베딩 NPY·manifest
  → output/RAG 최종 검증 보고서
```

추가 CSV가 생기면 `01_input.ipynb`의 `CSV_PATTERNS` 목록에 파일 경로나 glob을 추가한다. 모든 CSV에는 `url`, `title`, `content` 컬럼이 있어야 한다.

## 현재 실행 결과

| 검사항목 | 결과 |
| --- | ---: |
| 입력 행 | 300 |
| 유효 게시글 | 299 |
| 제외 행 | 1 (`empty_content`) |
| 짧은 본문 표시 | 19 |
| 생성 청크 | 5,506 |
| 임베딩 shape | `(5506, 768)` |
| dtype | `float32` |
| 실제 입력 토큰 범위 | 21~128 |
| 128토큰 초과 | 0 |

`128`은 모델의 입력 토큰 한도이고 `768`은 청크 하나를 변환한 출력 벡터 차원이다.

`05_pipeline.ipynb`에서 다음 항목을 모두 검사한다.

- 청크 수와 임베딩 행 수
- 청크 ID 고유성 및 manifest 순서
- `float32`와 유한값 여부
- L2 norm이 1인지 여부
- 최종 모델 입력이 128토큰 이하인지 여부
- 청크 JSON과 임베딩 NPY의 SHA-256

## ChromaDB 담당자 인계 파일

- `output/RAG/maple_inven_tips_documents_chunked.json`
- `output/RAG/maple_inven_tips_embeddings.npy`
- `output/RAG/maple_inven_tips_embeddings_manifest.json`

연결 규약은 다음과 같다.

```text
documents_chunked[i]["id"]           → Chroma ID
documents_chunked[i]["page_content"] → Chroma document
documents_chunked[i]["metadata"]     → Chroma metadata
embeddings[i]                          → Chroma embedding
```

`documents_chunked[i]`와 `embeddings[i]`는 항상 같은 청크다. 이 노트북들은 기존 `chroma_db` 파일을 열거나 수정하지 않는다.
