# 메이플 인벤 팁 RAG 데이터 파이프라인

## 1. 목적

이 폴더의 `maple_inven_rag_원본(1~10p).csv`를 다음 순서로 처리한다.

```text
CSV 입력
  → 스키마 검증·병합
  → 텍스트와 메타데이터 전처리
  → 모델 tokenizer 기준 청킹
  → SentenceTransformer 임베딩
  → ChromaDB 적재 직전 JSON·NPY·manifest
```

이번 코드의 범위는 **임베딩 생성까지**다. 인벤 크롤링과 ChromaDB 생성·적재는 포함하지 않는다. 코드, 테스트, 설명서, 생성 결과는 모두 이 `ㅋㅌㅊ` 폴더 안에 둔다.

## 2. 폴더 구조

```text
ㅋㅌㅊ/
├── maple_inven_rag_원본(1~10p).csv
├── README.md
├── inven_tip_rag/
│   ├── __init__.py       모델·청킹 기본값
│   ├── input.py          CSV 경로 탐색·스키마 검증·병합
│   ├── preprocess.py     텍스트·URL·숫자·날짜 정규화
│   ├── chunking.py       128토큰 제한 청킹
│   ├── embedding.py      벡터 생성·L2 정규화·manifest
│   ├── pipeline.py       단계 연결·원자적 파일 저장
│   └── __main__.py       preprocess/chunk/embed/all CLI
├── tests/                빠른 단위·통합 테스트
└── output/               실제 실행 후 생성되는 산출물
```

## 3. 실행 환경

프로젝트 루트의 `pyproject.toml`과 가상환경을 재사용한다. PowerShell에서 이 폴더로 이동한 뒤 명령을 실행한다.

```powershell
Set-Location "C:\Users\Playdata\Desktop\team3_ 프로젝트1\mle-01-p1-team3\ㅋㅌㅊ"
```

### 테스트

```powershell
uv run --no-sync --project .. python -m unittest discover -s tests -p "test_*.py" -v
```

`--no-sync`는 이미 구성된 프로젝트 가상환경을 그대로 사용한다. 처음 환경을 설치해야 한다면 `--no-sync`를 빼고 한 번 실행한다.

## 4. 전체 파이프라인 실행

```powershell
uv run --no-sync --project .. python -m inven_tip_rag all `
  --input "maple_inven_rag_원본(1~10p).csv" `
  --output-root output `
  --model-name jhgan/ko-sroberta-multitask `
  --chunk-tokens 100 `
  --overlap-tokens 20 `
  --max-tokens 128 `
  --batch-size 32
```

처음 실행할 때 Hugging Face에서 임베딩 모델을 내려받을 수 있다. 이후에는 로컬 캐시를 재사용한다.

## 5. 단계별 실행

앞 단계의 결과를 확인하거나 특정 단계만 다시 실행할 수 있다.

### 5.1 전처리

```powershell
uv run --no-sync --project .. python -m inven_tip_rag preprocess `
  --input "maple_inven_rag_원본(1~10p).csv" `
  --output-root output
```

생성 파일:

- `output/processed/maple_inven_tips_processed.json`
- `output/processed/maple_inven_tips_rejected.json`

### 5.2 청킹

```powershell
uv run --no-sync --project .. python -m inven_tip_rag chunk `
  --output-root output `
  --model-name jhgan/ko-sroberta-multitask `
  --chunk-tokens 100 `
  --overlap-tokens 20 `
  --max-tokens 128
```

생성 파일:

- `output/RAG/maple_inven_tips_documents_chunked.json`

### 5.3 임베딩

```powershell
uv run --no-sync --project .. python -m inven_tip_rag embed `
  --output-root output `
  --model-name jhgan/ko-sroberta-multitask `
  --chunk-tokens 100 `
  --overlap-tokens 20 `
  --max-tokens 128 `
  --batch-size 32
```

생성 파일:

- `output/RAG/maple_inven_tips_embeddings.npy`
- `output/RAG/maple_inven_tips_embeddings_manifest.json`

## 6. 입력 데이터 계약

### 필수 컬럼

| 컬럼 | 사용 목적 |
| --- | --- |
| `url` | 문서 ID 생성, URL 중복 제거, 출처 링크 |
| `title` | 제목 metadata와 임베딩 prefix |
| `content` | RAG 청킹 본문 |

### 선택 컬럼

| 컬럼 | 사용 목적 |
| --- | --- |
| `category` | `section_title`; 비어 있으면 `기타` |
| `author` | 전처리 결과에 원본 보존 |
| `created_at` | ISO 8601 정규화 |
| `views` | nullable integer metadata |
| `likes` | nullable integer metadata |

각 레코드에는 원본 파일의 절대 경로와 CSV 행 번호도 기록한다. 문제가 있는 데이터가 어느 파일의 몇 번째 행인지 다시 찾기 위함이다.

## 7. 향후 CSV가 추가되는 경우

크롤러 코드는 없지만 같은 컬럼의 CSV가 늘어나도 그대로 처리할 수 있다.

### 여러 파일 직접 지정

```powershell
uv run --no-sync --project .. python -m inven_tip_rag all `
  --input "maple_inven_rag_원본(1~10p).csv" `
  --input "maple_inven_rag_원본(11~20p).csv" `
  --output-root output
```

### glob 패턴 사용

```powershell
uv run --no-sync --project .. python -m inven_tip_rag all `
  --input "maple_inven_rag_원본(*p).csv" `
  --output-root output
```

입력 순서대로 파일을 합치고 canonical URL 기준으로 중복을 제거한다. 동일 URL이 다시 나오면 나중에 입력된 유효 레코드를 사용하고 교체된 레코드는 `duplicate_url_replaced` 사유로 제외 보고서에 남긴다.

## 8. 전처리 규칙

`preprocess.py`는 다음 규칙을 적용한다.

1. HTML entity를 복원한다. 예: `&amp;` → `&`.
2. Unicode NFKC를 적용한다. 예: 전각 `Ａ` → `A`.
3. CRLF/CR 줄바꿈을 LF(`\n`)로 통일한다.
4. 문단 구분은 유지하고 줄 내부의 연속 공백만 하나로 줄인다.
5. URL query string과 fragment를 제거한다.
6. 조회수·추천수의 쉼표를 제거하고 integer로 변환한다.
7. 파싱 가능한 날짜는 ISO 8601로 변환한다.
8. URL·제목·본문이 비어 있으면 제외 보고서에 사유를 남긴다.
9. 본문이 100자 미만이면 버리지 않고 `text_quality="short"`로 표시한다.
10. 본문의 SHA-256을 저장해 향후 내용 변경을 비교할 수 있게 한다.

현재 CSV에서는 `author`가 대부분 비어 있으므로 RAG 청크 metadata에는 넣지 않는다. 전처리 JSON에는 원본 추적을 위해 보존한다.

## 9. 불용어를 제거하지 않는 이유

`stopwords_ko.json`은 단어 빈도나 키워드 분석에서 조사·상투어를 제외할 때 사용하는 사전이다. 이번 단계는 문장을 SentenceTransformer에 넣어 의미 벡터를 만드는 작업이다.

문장 임베딩 전에 불용어를 삭제하면 다음 문제가 생길 수 있다.

- 조사와 서술 관계가 사라져 문장 의미가 바뀔 수 있다.
- `시간`, `사용`, `가능`, `스펙`처럼 메이플 질문에서 중요한 단어도 제거될 수 있다.
- 사용자의 자연어 질문과 정제된 문서의 표현 차이가 커질 수 있다.

따라서 이번 파이프라인은 `stopwords_ko.json`을 읽거나 수정하지 않는다. 불용어 처리는 별도의 EDA·키워드 분석 단계에서만 수행하는 것이 적절하다.

## 10. 128토큰의 의미와 청킹 계산

`128`은 글자 수나 임베딩 벡터 차원이 아니다. `jhgan/ko-sroberta-multitask`의 SentenceTransformer가 한 번에 읽는 **입력 토큰 수의 상한**이다.

```text
원문 → tokenizer → subword token IDs → 최대 128개 입력 → 768차원 벡터
```

- 입력 한도: 128토큰
- 출력 벡터: 768차원
- 기본 본문 청크 상한: 100토큰
- 인접 청크 중첩: 20토큰

각 청크에는 검색 품질을 위해 다음 prefix가 붙는다.

```text
문서 제목: <게시글 제목>
카테고리: <게시판 카테고리>

<청크 본문>
```

코드는 다음 순서로 실제 본문 예산을 계산한다.

1. 모델 tokenizer로 제목·카테고리 prefix의 토큰 수를 센다.
2. `[CLS]`, `[SEP]` 같은 특수 토큰 여유 2개를 둔다.
3. `128 - prefix 토큰 수 - 2`와 기본값 100 중 작은 값을 본문 한도로 사용한다.
4. 문단 → 줄바꿈 → 문장부호 → 공백 → 글자 순으로 분할한다.
5. 최종 `prefix + 본문`이 128토큰을 넘지 않는지 다시 검증한다.

이 과정을 거치면 긴 게시글도 모델이 조용히 뒷부분을 잘라내지 않고 여러 청크로 처리된다.

## 11. 문서와 metadata 구조

URL 마지막의 인벤 게시글 번호로 안정적인 ID를 만든다.

```text
document_id = inven_tip_<article_id>
chunk_id    = inven_tip_<article_id>_<chunk_index>
```

청크 예시는 다음과 같다.

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

`source="guide"`는 현재 팀 RAG의 가이드 검색 필터와 호환하기 위한 값이다. 실제 데이터 출처는 `origin="inven_tip"`, `source_name`, `url`로 구분한다.

## 12. 임베딩 산출물

`embedding.py`는 청크 순서를 바꾸지 않고 모델에 전달한다. 모델 출력은 다음 검사를 거친다.

- 행 수가 청크 수와 같은지 확인
- 2차원 행렬인지 확인
- `float32`로 변환
- 0 벡터 거부
- 모든 벡터를 L2 normalize
- 각 행의 norm이 허용 오차 안에서 1인지 확인

cosine similarity 검색에서 정규화 벡터를 사용하면 두 벡터의 내적을 바로 유사도 점수로 사용할 수 있다.

## 13. 최종 산출물

| 파일 | 내용 |
| --- | --- |
| `output/processed/maple_inven_tips_processed.json` | 유효 게시글과 정규화 필드 |
| `output/processed/maple_inven_tips_rejected.json` | 제외된 행과 사유 |
| `output/RAG/maple_inven_tips_documents_chunked.json` | RAG 청크와 metadata |
| `output/RAG/maple_inven_tips_embeddings.npy` | 청크 순서와 같은 임베딩 행렬 |
| `output/RAG/maple_inven_tips_embeddings_manifest.json` | 모델·shape·checksum·chunk ID 순서 |
| `output/RAG/maple_inven_tips_pipeline_report.json` | 입력·유효·제외·청크 통계 |

각 파일은 같은 디렉터리에 임시 파일을 완성한 다음 `os.replace()`로 교체한다. 실행 도중 중단되어 기존 정상 파일이 반쪽짜리 JSON이나 NPY로 바뀌는 것을 방지한다.

## 14. ChromaDB 담당자 인계 규약

ChromaDB 담당자는 다음 세 파일을 사용하면 된다.

- `maple_inven_tips_documents_chunked.json`
- `maple_inven_tips_embeddings.npy`
- `maple_inven_tips_embeddings_manifest.json`

인덱스 연결 규약은 다음과 같다.

```text
documents_chunked[i]["id"]           → Chroma ID
documents_chunked[i]["page_content"] → Chroma document
documents_chunked[i]["metadata"]     → Chroma metadata
embeddings[i]                          → Chroma embedding
```

즉 `documents_chunked[i]`와 `embeddings[i]`는 항상 같은 청크다. manifest의 `chunk_ids`도 같은 순서이며, JSON과 NPY의 SHA-256으로 서로 같은 실행에서 생성됐는지 확인할 수 있다.

이 폴더의 코드는 `chroma_db`를 열거나 변경하지 않는다.

## 15. 현재 CSV 실제 실행 결과

`maple_inven_rag_원본(1~10p).csv`에 기본 설정을 적용한 결과다.

| 검사항목 | 결과 |
| --- | ---: |
| 입력 행 | 300 |
| 유효 게시글 | 299 |
| 제외 행 | 1 (`empty_content`) |
| 중복 URL | 0 |
| 짧은 본문 표시 | 19 |
| 생성 청크 | 5,506 |
| 임베딩 shape | `(5506, 768)` |
| dtype | `float32` |
| 실제 입력 토큰 범위 | 21~128 |
| 128토큰 초과 | 0 |
| 고유 chunk ID | 5,506 |

모든 임베딩 값은 유한값이며 L2 norm 범위는 약 `0.99999988~1.00000012`다. 청크 JSON의 ID 순서와 manifest의 `chunk_ids` 순서가 일치하고, manifest에 기록된 JSON·NPY SHA-256도 실제 파일과 일치함을 확인했다.

여기서 `128`은 모델에 한 번에 넣을 수 있는 **입력 토큰 수**, `768`은 한 청크를 변환한 **출력 벡터 차원**이다. 서로 다른 값이다.

## 16. 문제 해결

### 입력 CSV를 찾지 못한 경우

괄호와 `~`가 포함된 경로 전체를 큰따옴표로 감싼다. 현재 폴더에서 실행하면 파일명만 지정하면 된다.

### 모델 다운로드 실패

네트워크 연결과 Hugging Face 캐시 디렉터리 권한을 확인한다. 모델 다운로드가 완료된 뒤에는 캐시를 재사용할 수 있다.

### 메모리 부족

`--batch-size 16` 또는 `--batch-size 8`로 낮춘다. 배치 크기는 결과 벡터의 순서나 값의 의미를 바꾸지 않는다.

### 필수 컬럼 오류

CSV 헤더에 `url`, `title`, `content`가 모두 있는지 확인한다. 선택 컬럼이 없으면 빈 값으로 처리한다.
