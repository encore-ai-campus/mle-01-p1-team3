# 메이플 인벤 팁 데이터 RAG 전처리·청킹·임베딩 파이프라인 설계

## 1. 목적

메이플 인벤 「팁과 노하우」 게시판에서 이미 수집한 CSV를 입력으로 받아 다음 작업을 재현 가능한 하나의 파이프라인으로 제공한다.

1. 입력 검증 및 병합
2. 텍스트·메타데이터 전처리
3. RAG 문서 변환
4. 토큰 길이 기반 청킹
5. SentenceTransformer 임베딩 생성
6. ChromaDB 담당자에게 전달할 산출물과 검증 정보 저장

현재 처리 대상은 다음 파일 한 개다.

`ㅋㅌㅊ/maple_inven_rag_원본(1~10p).csv`

크롤러 구현과 ChromaDB 적재는 이번 범위에서 제외한다.

## 2. 범위

### 포함

- 현재 CSV 300건에 대한 데이터 품질 검사
- 같은 스키마의 CSV를 추가 입력할 수 있는 구조
- URL 기준 중복 제거와 안정적인 문서 ID 생성
- RAG용 텍스트 정규화
- 토큰 길이 기준 청킹
- 정규화된 임베딩 행렬 생성
- 처리 결과 및 제외 사유 보고
- 단위 테스트와 전체 파이프라인 통합 테스트
- 실행 방법과 각 처리 규칙을 설명하는 문서

### 제외

- 인벤 웹사이트 크롤링
- ChromaDB 컬렉션 생성·수정·적재
- 기존 ChromaDB 파일 변경
- Streamlit 또는 기존 retriever 수정
- 불용어를 이용한 키워드 분석

## 3. 입력 계약

CSV는 다음 컬럼을 사용한다.

| 컬럼 | 필수 여부 | 용도 |
| --- | --- | --- |
| `url` | 필수 | 문서 식별, 출처 링크 |
| `category` | 선택 | 게시판 카테고리 |
| `title` | 필수 | 문서 제목 및 임베딩 문맥 |
| `author` | 선택 | 원본 보존용 메타데이터 |
| `created_at` | 선택 | 게시글 작성 시각 |
| `views` | 선택 | 조회수 메타데이터 |
| `likes` | 선택 | 추천수 메타데이터 |
| `content` | 필수 | RAG 본문 |

현재는 지정된 CSV 한 개만 처리한다. 향후 페이지가 추가된 CSV가 생기면 CLI의 `--input`을 여러 번 지정하거나 glob 패턴을 사용해 같은 파이프라인에 넣을 수 있다. 모든 입력은 합친 뒤 canonical URL 기준으로 중복 제거한다.

## 4. 처리 구조

패키지는 책임별로 나눈다.

```text
src/inven_tip_rag/
├── input.py          CSV 탐색·검증·병합
├── preprocess.py     텍스트 및 메타데이터 정규화
├── chunking.py       RAG 문서 변환과 토큰 기반 청킹
├── embedding.py      임베딩 생성과 산출물 저장
├── pipeline.py       단계 연결 및 처리 보고서 생성
└── __main__.py       CLI 진입점
```

각 단계는 메모리상의 명확한 레코드 구조를 입력·출력으로 사용하고, 개별적으로 테스트할 수 있어야 한다.

## 5. 전처리 규칙

### 5.1 필드 정규화

- HTML entity를 복원한다.
- Unicode를 NFKC로 정규화한다.
- 줄바꿈을 `\n`으로 통일한다.
- 문단 구분은 유지하면서 줄 내부의 연속 공백을 하나로 줄인다.
- URL의 query string과 fragment를 제거하고 trailing slash를 정리한다.
- `views`, `likes`는 nullable integer로 변환한다.
- `created_at`은 파싱 가능한 경우 ISO 8601 문자열로 저장한다.

### 5.2 유효성 및 제외 규칙

- URL 또는 제목이 없으면 제외한다.
- 본문이 비어 있으면 임베딩 근거가 없으므로 제외한다.
- URL 중복이 있으면 입력 순서상 마지막 유효 레코드를 사용한다.
- 짧은 본문은 이미지 중심 게시글일 수 있으므로 자동 제외하지 않는다. 대신 `text_quality="short"` 메타데이터를 기록한다.
- 제외된 레코드는 원본 위치, URL, 제목, 제외 사유를 별도 JSON 보고서에 남긴다.

### 5.3 불용어 처리

`data/processed/stopwords_ko.json`은 빈도 분석용 사전이며 이번 임베딩 파이프라인에서는 사용하지 않는다. 문장 임베딩에 필요한 조사·서술 관계와 `시간`, `사용`, `가능`, `스펙` 같은 도메인 의미를 보존한다.

## 6. 문서 및 메타데이터 스키마

게시글 번호를 URL에서 추출해 안정적인 ID를 만든다.

- `document_id`: `inven_tip_<article_id>`
- `chunk_id`: `inven_tip_<article_id>_<chunk_index>`

청킹 결과 JSON의 각 항목은 다음 구조를 갖는다.

```json
{
  "id": "inven_tip_48082_0",
  "page_content": "청크 본문",
  "metadata": {
    "source": "guide",
    "origin": "inven_tip",
    "source_name": "메이플 인벤 팁과 노하우",
    "document_id": "inven_tip_48082",
    "chunk_id": "inven_tip_48082_0",
    "chunk_index": 0,
    "article_id": "48082",
    "name": "뉴비에서 메잘알까지 1편 - 쿨타임 시스템",
    "section_title": "실험",
    "url": "https://www.inven.co.kr/board/maple/2304/48082",
    "created_at": "2026-08-03T12:43:00",
    "views": 12988,
    "likes": 18,
    "text_quality": "normal"
  }
}
```

`source="guide"`는 기존 RAG의 가이드 검색 필터와 호환하기 위한 값이다. 실제 출처는 `origin="inven_tip"`과 `source_name`으로 구분한다.

## 7. 청킹

임베딩 모델 `jhgan/ko-sroberta-multitask`의 SentenceTransformer 최대 입력은 128토큰이다. 청크 본문은 모델 토크나이저 기준 최대 100토큰, 중첩 20토큰을 기본값으로 사용한다.

- 문단, 줄바꿈, 문장 경계를 우선한다.
- 제목과 카테고리를 임베딩 입력의 prefix로 매 청크에 붙인다.
- 문서별로 prefix 토큰 수를 먼저 계산하고, 특수 토큰 여유 2개를 제외한 `128 - prefix 토큰 수 - 2`와 기본 본문 한도 100 중 작은 값을 실제 본문 청크 한도로 사용한다.
- 제목이 비정상적으로 길어 prefix만으로 한도를 초과하면 제목을 토큰 단위로 줄이되 원래 제목은 metadata에 그대로 보존한다.
- prefix를 포함한 최종 임베딩 입력이 128토큰을 넘지 않는지 검증한다.
- 빈 청크는 생성하지 않는다.
- 한 문서 안의 `chunk_index`는 0부터 시작한다.

청크 크기와 중첩은 CLI 옵션으로 변경할 수 있으나 잘못된 범위는 즉시 오류 처리한다.

## 8. 임베딩

- 모델: `jhgan/ko-sroberta-multitask`
- 출력 차원: 모델이 반환한 실제 차원을 기록한다.
- 배치 크기: 기본 32, CLI에서 변경 가능
- 출력 형식: NumPy `float32`
- 정규화: cosine similarity에 바로 사용할 수 있도록 L2 normalize

임베딩 행렬의 행 순서는 청킹 JSON의 항목 순서와 정확히 일치해야 한다. 저장 후 행 수, 차원, dtype, 각 벡터 norm을 검증한다.

## 9. 산출물

기본 출력은 다음과 같다.

```text
data/processed/maple_inven_tips_processed.json
data/processed/maple_inven_tips_rejected.json
data/RAG/maple_inven_tips_documents_chunked.json
data/RAG/maple_inven_tips_embeddings.npy
data/RAG/maple_inven_tips_embeddings_manifest.json
data/RAG/maple_inven_tips_pipeline_report.json
```

manifest에는 다음 정보를 저장한다.

- 모델 이름
- 청킹 설정
- 임베딩 행 수와 차원
- dtype과 normalize 여부
- 청킹 JSON 및 임베딩 파일 SHA-256
- 행 순서에 대응하는 `chunk_id` 목록
- 생성 시각

ChromaDB 담당자는 청킹 JSON, `.npy`, manifest만 읽어 적재할 수 있다.

## 10. CLI

전체 파이프라인은 프로젝트 루트에서 다음과 같이 실행한다.

```powershell
uv run python -m src.inven_tip_rag all `
  --input "ㅋㅌㅊ/maple_inven_rag_원본(1~10p).csv"
```

향후 입력이 늘어나면 다음 두 방식 모두 허용한다.

```powershell
uv run python -m src.inven_tip_rag all --input "data/raw/tips_1_10.csv" --input "data/raw/tips_11_20.csv"
uv run python -m src.inven_tip_rag all --input "data/raw/maple_inven_tips_*.csv"
```

`preprocess`, `chunk`, `embed` 하위 명령도 제공해 각 단계만 다시 실행할 수 있게 한다.

## 11. 오류 처리

- 필수 컬럼이 없으면 어떤 컬럼이 부족한지 표시하고 실행을 중단한다.
- glob이 어떤 파일도 찾지 못하면 실행을 중단한다.
- 한 레코드의 데이터가 잘못된 경우 전체 실행을 중단하지 않고 제외 보고서에 남긴다.
- 모델을 불러올 수 없으면 설치·네트워크·캐시 확인 메시지와 함께 임베딩 단계만 실패 처리한다.
- 기존 출력은 모든 검증을 통과한 뒤 원자적으로 교체해 중간 실패로 정상 파일이 손상되지 않게 한다.

## 12. 테스트 전략

### 단위 테스트

- 단일·다중·glob CSV 입력 탐색
- 필수 컬럼 검증
- URL canonicalization 및 중복 제거
- 텍스트 공백·개행·HTML entity 정규화
- 숫자·날짜 변환
- 빈 본문 제외와 짧은 본문 품질 표시
- 안정적인 문서·청크 ID
- 청크 순서와 토큰 길이 제한
- fake embedding model을 이용한 행 순서·정규화·manifest 검증

### 통합 테스트

- 소형 fixture CSV를 입력해 전처리부터 임베딩 산출물까지 실행
- 실제 모델 대신 deterministic fake encoder를 사용해 빠르게 검증
- 최종 검증에서 실제 300건 CSV와 실제 임베딩 모델로 전체 파이프라인 실행

## 13. 완료 기준

- 현재 CSV에서 본문이 없는 레코드는 사유와 함께 제외된다.
- 모든 유효 게시글이 하나 이상의 청크로 변환된다.
- 모든 chunk ID가 유일하다.
- 모든 임베딩 입력이 모델 최대 토큰 수를 넘지 않는다.
- 청킹 JSON 항목 수와 임베딩 행 수가 같다.
- 임베딩은 `float32`이며 L2 norm이 허용 오차 내에서 1이다.
- ChromaDB 파일과 기존 로컬 수정 파일은 변경하지 않는다.
- 테스트와 실제 전체 파이프라인 실행 결과가 문서에 기록된다.
