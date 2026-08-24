# 🍄 메이플스토리 신규 · 복귀 유저를 위한 RAG 기반 가이드라인 챗봇

**웹페이지 url** : [메이플 뉴비/복귀 유저들을 위한 가이드라인 챗봇](https://mapleinfoguide.streamlit.app/)

> 인벤 질문 게시판 **4,157건**을 분석해 뉴비가 실제로 막히는 지점을 찾고,
> 공식 가이드 · 직업 · 확률형 아이템 문서 **3,694 청크**를 벡터 DB로 구축해
> 근거 있는 답변만 돌려주는 정보 안내 서비스입니다.

<br>

## 🚩 목차

1. [기획 배경](#-기획-배경)
2. [서비스 소개](#-서비스-소개)
3. [데이터 파이프라인](#-데이터-파이프라인)
4. [데이터 분석 결과](#-데이터-분석-결과)
5. [RAG 아키텍처](#-rag-아키텍처)
6. [기능 소개](#-기능-소개)
7. [기술 스택](#-기술-스택)
8. [프로젝트 구조](#-프로젝트-구조)
9. [실행 방법](#-실행-방법)
10. [팀원 소개 및 역할](#-팀원-소개-및-역할)

<br>

## ✨ 기획 배경

#### 개요

- **한 줄 설명** : 메이플스토리 신규 · 복귀 유저의 진입 장벽을 낮추는 **RAG 기반 정보 안내 챗봇**

#### 문제 정의

메이플스토리는 20년 넘게 누적된 콘텐츠와 시스템을 가진 게임입니다.
신규 · 복귀 유저가 겪는 어려움은 **정보가 없어서**가 아니라, **정보가 너무 많고 흩어져 있어서** 발생합니다.

| 문제 | 근거 |
| --- | --- |
| 공식 문서가 카테고리별로 파편화되어 있음 | 공식 가이드 9개 카테고리 · 124개 문서 |
| 직업 선택 기준을 한눈에 비교할 수 없음 | 5개 직업군 · 48개 직업 |
| 확률형 아이템 정보가 표 형태로만 제공됨 | 57개 아이템 · 2,205개 확률 행 |
| 결국 커뮤니티에 질문하고 답을 얻어야 함 | 인벤 질문 게시판 4,157건 수집 |

#### 접근 방법

1. **커뮤니티 질문을 먼저 분석한다** — 뉴비가 실제로 무엇을 묻는지 데이터로 확인
2. **공식 문서를 벡터 DB로 만든다** — 답변의 근거를 공식 출처로 한정
3. **Context 밖의 답은 만들지 않는다** — 할루시네이션 대신 "모른다"를 말하는 챗봇

<br>

## ✨ 서비스 소개

#### 페르소나

- **신규 유저** : 직업을 고르고 싶지만 48개 중 무엇을 골라야 할지 모른다.
- **복귀 유저** : 계정은 있지만 그동안 바뀐 시스템(해방 · 헥사 · 챌린저스 서버)을 모른다.
- **일반 유저** : 확률형 아이템 확률, 장비 강화 기준을 빠르게 확인하고 싶다.

#### 서비스 시퀀스

```
유저 질문
   ↓
질문 분류 (classify_question)  →  jobs / items / guide / mixed
   ↓
source 필터 + k 조정된 retriever 검색  (ChromaDB · cosine)
   ↓
build_context() — source · title · url · excerpt 로 압축, 중복 문서 제거
   ↓
ChatPromptTemplate → GPT-4o-mini (스트리밍)
   ↓
답변 + 참고 문서 링크 칩 + 근거 문서 목록
```

#### 기대 효과

- 흩어진 공식 문서를 **하나의 질의 창구**로 통합
- 답변마다 **출처 URL**을 제공해 검증 가능한 정보 전달
- 커뮤니티 질문 데이터를 근거로 **뉴비가 막히는 지점을 지표화**

<br>

## ✨ 데이터 파이프라인

```
[1] 수집 (Crawling / API)
     ├─ 공식 가이드     maplestory.nexon.com/Guide/N23GameInformation   →   124건
     ├─ 직업 정보       maplestory.nexon.com/Guide/N23Job               →    48건
     ├─ 확률형 아이템   maplestory.nexon.com/Guide/CashShop/Probability →    57건
     ├─ 인벤 질문게시판 inven.co.kr/board/maple/2304                    → 4,244건
     └─ 유튜브 댓글     YouTube Data API v3 (search / videos / comments)
                        ↓
[2] 전처리 · 문서화 (Document 변환)
     ├─ 정규표현식 기반 본문 정제 · 공백 정규화
     ├─ HTML 표 rowspan / colspan 전개 → 행 단위 문서화
     └─ page_content + metadata 구조의 LangChain Document 생성
                        ↓
[3] 청킹 (Chunking)
     └─ 가이드 문서 124건 → 1,441 청크 (chunk_index 부여)
                        ↓
[4] 임베딩 (Embedding)
     └─ jhgan/ko-sroberta-multitask · 768차원 · normalize_embeddings=True
                        ↓
[5] 벡터 DB 적재 (ChromaDB)         ← src/build_chroma.py 로 재현 가능
     └─ collection: maplestory_guides · hnsw:space = cosine · 3,694 청크
                        ↓
[6] 검색 · 생성 (RAG Chain)
     └─ 질문 분류 → source 필터 검색 → build_context() → GPT-4o-mini
```

#### 수집 데이터 현황

| 구분 | 원본 | 문서화 | 벡터 DB 적재 | 위치 |
| --- | ---: | ---: | ---: | --- |
| 공식 가이드 | 124건 | 124건 | **1,441 청크** | `data/RAG/maple_guides_documents_chunked.json` |
| 직업 정보 | 48건 | 48건 | 48 청크 | `data/RAG/maple_jobs_documents.json` |
| 확률형 아이템 | 57건 | 2,205행 | 2,205 청크 | `data/RAG/maple_items_documents.json` |
| **합계** | | | **3,694 청크** | `chroma_db/` (collection `maplestory_guides`) |
| 인벤 질문 게시판 | 4,244건 | — | — | `data/processed/inven_question_final.csv` (4,157건) |
| 뉴비 · 복귀 FAQ | 17건 | — | — | `data/RAG/newbi_comebak_guide.json` |

#### 문서 메타데이터 스키마

```json
{
  "source": "guide",                  // 출처 (guide / jobs / items) — 검색 필터 키
  "name": "보스 레이드: 자쿰 가이드",     // 문서 원본 제목
  "section_title": "보스/레이드",       // 카테고리
  "article_id": 101,                  // 원본 게시글 ID
  "board_id": 1,                      // 게시판 ID
  "url": "https://maplestory...",     // 출처 링크 (답변 시 참조 URL 제공용)
  "chunk_index": 0                    // 문서 내 청크 순서
}
```

> ChromaDB의 SQLite 내부 스키마(테이블 15종 · FTS5 가상 테이블)는
> [`docs/chromadb-schema-and-system-prompt.md`](docs/chromadb-schema-and-system-prompt.md) 에 별도 정리되어 있습니다.

<br>

## ✨ 데이터 분석 결과

인벤 질문 게시판 4,157건을 **kiwipiepy** 로 형태소 분석하고,
일반 불용어(679개)에 메이플 도메인 불용어를 더해 키워드를 추출했습니다.

#### 카테고리 분포

| 카테고리 | 질문 수 | 비율 |
| --- | ---: | ---: |
| 아이템 | 2,031 | 48.9% |
| 기타 | 1,332 | 32.0% |
| 직업 | 385 | 9.3% |
| 시세 | 156 | 3.8% |
| 몬스터 | 144 | 3.5% |
| 퀘스트 | 109 | 2.6% |

![카테고리별 질문 수](./images/%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC%EB%B3%84%20%EC%A7%88%EB%AC%B8%20%EC%88%98%20%ED%99%95%EC%9D%B8.png)

#### 전체 질문 주요 키워드 TOP 15

![전체 키워드 TOP 15](./%EC%9D%B8%EB%B2%A4%EB%8D%B0%EC%9D%B4%ED%84%B0%20%EC%8B%9C%EA%B0%81%ED%99%94/figures/02_overall_keyword_top15.png)

`챌섭(24.7%)` · `무기(11.0%)` · `해방(10.0%)` · `보조(10.0%)` · `보스(9.2%)` 순으로,
**신규 서버(챌린저스)와 장비 · 해방 콘텐츠**에 질문이 집중되어 있었습니다.

#### 신규 · 복귀 유저 질문의 차별점

"뉴비 · 복귀 · 시작" 등 신규/복귀 표현이 포함된 질문군을 분리해 일반 질문군과 비교했습니다.

| 키워드 | 일반 질문 등장률 | 신규·복귀 질문 등장률 | 차이(%p) |
| --- | ---: | ---: | ---: |
| 챌섭 | 20.1% | 37.5% | **+17.4** |
| 시작 | 2.7% | 15.2% | **+12.5** |
| 메소 | 4.9% | 12.3% | +7.4 |
| 해방 | 8.3% | 14.7% | +6.3 |
| 감사 | 3.7% | 9.7% | +5.9 |
| 보조 | 8.5% | 14.1% | +5.6 |

![키워드 그룹 비교](./%EC%9D%B8%EB%B2%A4%EB%8D%B0%EC%9D%B4%ED%84%B0%20%EC%8B%9C%EA%B0%81%ED%99%94/figures/03_keyword_group_comparison.png)

> **인사이트** — 신규 · 복귀 유저는 "무엇을 먼저 시작해야 하는가"와
> "챌린저스 서버에서의 성장 루트"를 압도적으로 많이 묻습니다.
> 즉 개별 스펙 질문보다 **초기 진입 경로 안내**의 우선순위가 높습니다.

#### 조회수 상위 질문 비교

![TOP 10 비교](./%EC%9D%B8%EB%B2%A4%EB%8D%B0%EC%9D%B4%ED%84%B0%20%EC%8B%9C%EA%B0%81%ED%99%94/figures/01_top10_comparison.png)

위 세 그래프는 **질문 분석 대시보드** 페이지에서 Plotly 인터랙티브 차트로 다시 제공됩니다.

<details>
<summary>추가 분석 이미지 보기</summary>

<br>

**카테고리별 핵심 키워드 TOP 5**

![카테고리별 핵심 키워드 1](./images/%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC%EB%B3%84%20%ED%95%B5%EC%8B%AC%20%ED%82%A4%EC%9B%8C%EB%93%9C%20top%205%20%281%29.png)

![카테고리별 핵심 키워드 2](./images/%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC%EB%B3%84%20%ED%95%B5%EC%8B%AC%20%ED%82%A4%EC%9B%8C%EB%93%9C%20top%205%20%282%29.png)

**가장 많이 본 글의 단어 TOP 20**

![가장 많이 본 글의 단어](./images/%EA%B0%80%EC%9E%A5%20%EB%A7%8E%EC%9D%B4%20%EB%B3%B8%20%EA%B8%80%EC%9D%98%20%EB%8B%A8%EC%96%B4%20top20.png)

**뉴비 · 복귀 유저가 언급된 게시글**

![뉴비 복귀 게시글](./images/%EB%89%B4%EB%B9%84_%EB%B3%B5%EA%B7%80%20%EC%9C%A0%EC%A0%80%EA%B0%80%20%EC%96%B8%EA%B8%89%EB%90%9C%20%EA%B2%8C%EC%8B%9C%EA%B8%80%28head%29.png)

**토크나이즈 결과**

![TOKENIZE](./images/TOKENIZE%20HEAD%20%EC%8B%A4%ED%96%89%20%EA%B2%B0%EA%B3%BC.png)

</details>

<br>

## ✨ RAG 아키텍처

#### 문제: 단일 컬렉션 · 고정 k 검색의 한계

초기 체인은 `maplestory_guides` 컬렉션 하나를 필터 없이 `k=4` 로 검색했습니다.
이 컬렉션에는 `items 2,205` · `guide 1,441` · `jobs 48` 이 함께 들어 있어,
**"직업 추천" 질문이 아이템 · 가이드 문서에 묻히는** 문제가 있었습니다.
특히 `jobs` 문서는 48개뿐이라 직업 질문에서도 관련 없는 조각이 먼저 잡히기 쉬웠습니다.

> 진단 과정과 개선 우선순위는 [`notebooks/RAG_chain_점검.md`](notebooks/RAG_chain_점검.md) 에 기록되어 있습니다.

#### 해결: 질문 라우팅 + source 필터 + context 압축

**1. 질문 분류** — [`src/rag_chain_utils.py`](src/rag_chain_utils.py)

```python
def classify_question(question: str) -> str:
    # JOB_KEYWORDS / ITEM_KEYWORDS / GUIDE_KEYWORDS 매칭
    # 두 개 이상 걸리거나 하나도 안 걸리면 "mixed"
```

| route | 매칭 키워드 예시 | 검색 설정 |
| --- | --- | --- |
| `jobs` | 직업 · 전직 · 스킬트리 · 링크 스킬 · 유니온 | `k=6`, `filter={"source": "jobs"}` |
| `items` | 아이템 · 장비 · 잠재 · 큐브 · 스타포스 · 추옵 | `k=6`, `filter={"source": "items"}` |
| `guide` | 가이드 · 콘텐츠 · 퀘스트 · 보스 · 사냥터 · 메소 | `k=5`, `filter={"source": "guide"}` |
| `mixed` | (복수 매칭 또는 미매칭) | `k=8`, 필터 없음 |

**2. Context 압축** — 문서 전문을 그대로 붙이지 않고 `source · title · url · excerpt(220자)` 만 정리합니다.
`(source, title)` 기준 중복 제거와 `max_chars=1800` 상한을 적용해 잡음을 줄였습니다.

**3. 프롬프트 강화** — "핵심 결론을 2~4문장으로 먼저, 이어서 근거를 목록으로,
context가 부족하면 부족한 이유를 정확히 말하라"로 출력 전략을 명시했습니다.

#### 검색 모듈 구성

| 모듈 | 역할 |
| --- | --- |
| [`src/build_chroma.py`](src/build_chroma.py) | 소스 JSON → 임베딩 → ChromaDB 전체 재생성 (HNSW 인덱스 손상 복구용) |
| [`src/retrieve.py`](src/retrieve.py) | chromadb 네이티브 Top-K 검색. 직업명 60여 개를 포함한 키워드 필터, `where` 필터 실패 시 Python 폴백 |
| [`src/build_context.py`](src/build_context.py) | 검색 결과(dict) → context 문자열. 결과가 없으면 빈 문자열 대신 명시적 안내 문구 반환 |
| [`src/rag_chain_utils.py`](src/rag_chain_utils.py) | Streamlit 챗봇이 쓰는 질문 분류 · 검색 파라미터 · context 압축 |
| [`notebooks/rag_sql_analysis.ipynb`](notebooks/rag_sql_analysis.ipynb) | ChromaDB SQLite에 직접 SQL을 던지는 Text-to-SQL 진단 에이전트 (SELECT 외 차단) |

<br>

## ✨ 기능 소개

Streamlit 멀티페이지 애플리케이션으로 구성되어 있습니다. 진입점은 [`src/streamlit/app.py`](src/streamlit/app.py) 이며,
Maplestory 폰트와 배경 이미지를 base64로 인라인해 전 페이지에 공통 적용합니다.

| 페이지 | 파일 | 기능 |
| --- | --- | --- |
| 🏘️ 홈 | `pages/홈.py` | 캐릭터 검색 폼, 추천 수 · 조회 수 기준 인기 질문 TOP 10 |
| 📊 질문 분석 대시보드 | `pages/대시보드.py` | 인벤 질문 데이터 Plotly 인터랙티브 차트 3종 |
| 🎮 캐릭터 정보검색 | `pages/정보검색.py` | NEXON Open API 기반 캐릭터 상세 조회 |
| 💬 메이플스토리 가이드챗봇 | `pages/챗봇.py` | RAG 기반 질의응답 · 출처 링크 제공 |

#### 💬 가이드 챗봇

- **스트리밍 답변** — `st.write_stream` 으로 토큰 단위 출력
- **참고 문서 링크 칩** — 답변 바로 아래에 원문 URL을 중복 제거해 최대 6개 표시
- **근거 문서 익스팬더** — 검색된 문서의 제목 · source · 섹션 · 본문 미리보기와 라우팅 결과 표시
- **예시 질문 버튼** — 첫 진입 시 3개 제공
- **대화 새로 시작** — 사이드바에서 세션 초기화
- **캐싱** — 임베딩 모델 · 벡터스토어 · LLM · 프롬프트를 `@st.cache_resource` 로 1회만 로드

```python
route, _, docs = retrieve_documents(question)      # 질문 분류 → source별 retriever
chain = get_prompt() | get_chat_model(api_key)
stream = chain.stream({"context": build_context(docs), "question": question})
```

#### 🎮 캐릭터 정보검색

NEXON Open API(`open.api.nexon.com/maplestory/v1`)를 래핑한 `NexonClient` 로
캐릭터명 하나만 입력하면 아래 정보를 한 화면에 묶어서 보여줍니다.

- **CHARACTER INFO** — 캐릭터 이미지 · 레벨 · 월드 · 직업 · 길드 · 인기도
- **종합 능력치 / ABILITY / HYPER STAT** — 활성 프리셋을 자동 판별해 표시
- **장착 장비 / 심볼** — 아이콘 포함, 보유 개수 표기
- **PROPENSITY** — Plotly 레이더 차트
- **EXP HISTORY** — 최근 8일간 일자별 경험치 비율 (`get_basic(date=...)` 반복 조회, 데이터 없는 날 건너뜀)
- **무릉도장 / 유니온 / 길드** — 도장 기록, 유니온 레벨 · 등급, 길드 레벨 · 인원

API 오류는 `NexonApiError` 로 일원화해 NEXON 오류 코드(`OPENAPI00001`~`OPENAPI00011`)를
한국어 안내 메시지로 변환합니다.

```python
try:
    client.get_basic(ocid)
except NexonApiError as e:
    st.error(e.user_message)   # "API 호출량을 초과했습니다. 잠시 후 다시 시도해 주세요."
```

홈 화면에서 캐릭터명을 입력하면 `st.session_state` 를 거쳐 이 페이지로 자동 전환됩니다.

#### 📊 질문 분석 대시보드

`인벤데이터 시각화/outputs/` 의 분석 결과 CSV를 읽어 Plotly로 렌더링합니다.

1. **전체 / 신규·복귀 조회수 TOP 10** — 좌우 서브플롯, 각각 독립 축
2. **전체 질문 키워드 TOP 15** — 게시글 등장 비율 기준 (동일 게시글 내 중복 단어는 1회만 집계)
3. **신규·복귀 표현 포함 여부 비교** — 집단 크기 차이를 고려해 비율로 그룹 바 비교

<br>

## ✨ 기술 스택

| 영역 | 스택 |
| --- | --- |
| **언어 · 환경** | Python 3.12, uv, Dev Container (Codespaces) |
| **데이터 수집** | requests, BeautifulSoup4, Playwright, YouTube Data API v3, NEXON Open API |
| **데이터 처리 · 분석** | pandas, numpy, kiwipiepy, scikit-learn, wordcloud, networkx |
| **임베딩** | sentence-transformers (`jhgan/ko-sroberta-multitask`, 768차원) |
| **벡터 DB** | ChromaDB (cosine), langchain-chroma, Qdrant |
| **LLM · RAG** | LangChain (LCEL), langchain-openai, GPT-4o-mini, LangGraph |
| **평가 · 진단** | RAGAS, Text-to-SQL 진단 에이전트 (`create_agent` + 구조화 출력) |
| **관측성** | Langfuse |
| **프론트엔드** | Streamlit, Plotly, matplotlib, seaborn |
| **협업** | Git / GitHub (Feature Branch + PR), Notion |

<br>

## ✨ 프로젝트 구조

```
mle-01-p1-team3/
├── data/
│   ├── raw/                          # 원본 수집 데이터 (gitignore)
│   ├── processed/                    # 전처리 결과
│   │   ├── inven_question_final.csv  # 질문 4,157건 (홈 · 대시보드 데이터 소스)
│   │   ├── maple_items_process.json
│   │   └── stopwords_ko.json         # 한국어 불용어 679개
│   └── RAG/                          # 벡터 DB 적재용 Document
│       ├── maple_guides_documents_chunked.json   # 1,441 청크
│       ├── maple_jobs_documents.json             #    48 청크
│       ├── maple_items_documents.json            # 2,205 청크
│       └── newbi_comebak_guide.json
│
├── chroma_db/                        # ChromaDB persist 디렉터리 (gitignore)
│
├── src/
│   ├── build_chroma.py               # 소스 JSON → 임베딩 → ChromaDB 재생성
│   ├── retrieve.py                   # 키워드 라우팅 + Top-K 검색
│   ├── build_context.py              # 검색 결과 → context 문자열
│   ├── rag_chain_utils.py            # 질문 분류 · 검색 파라미터 · context 압축
│   ├── embedding.py                  # Document 통합 · chunk_id 부여 · 임베딩
│   ├── data_collect/
│   │   ├── als00als/                 # 공식 가이드 · 직업 · 아이템 · 인벤 크롤링
│   │   └── seventy4/                 # Playwright 인벤 크롤러 · YouTube API
│   └── streamlit/
│       ├── app.py                    # st.navigation 진입점 · 공통 폰트/배경
│       ├── nexon_client.py           # NEXON Open API 클라이언트
│       ├── dashboard_utils.py        # 응답 포맷팅 유틸
│       ├── assets/                   # 폰트 · 아이콘 · 배경
│       └── pages/{홈,대시보드,정보검색,챗봇}.py
│
├── notebooks/
│   ├── inven_eda.ipynb               # 인벤 데이터 EDA
│   ├── inven_data_process.ipynb      # 정제 파이프라인
│   ├── inven_data_analysis_new.ipynb # 키워드 · 토크나이즈 분석
│   ├── inven_guide_document.ipynb    # Document 변환
│   ├── inven_guide_chunking.ipynb    # 청킹
│   ├── data_embedding.ipynb          # 임베딩
│   ├── Chromadb_connect.ipynb        # ChromaDB 스키마 · 적재
│   ├── Top_k.ipynb                   # Top-K retriever
│   ├── build_context.ipynb           # Context 빌더
│   ├── rag_chain.ipynb               # LCEL RAG 체인
│   ├── rag_chain_retriever.ipynb     # retriever 기반 체인 (챗봇 페이지 원본)
│   ├── rag_chain_dev.ipynb           # 체인 실험
│   ├── rag_sql_analysis.ipynb        # ChromaDB Text-to-SQL 진단 에이전트
│   └── RAG_chain_점검.md              # 검색 품질 진단 기록
│
├── docs/
│   └── chromadb-schema-and-system-prompt.md   # SQLite 스키마 + system prompt
│
├── 인벤데이터 시각화/
│   ├── visualization.ipynb           # 조회수 · 키워드 · 그룹 비교 시각화
│   ├── figures/                      # 결과 그래프
│   └── outputs/                      # 분석 결과 CSV / PKL (대시보드 데이터 소스)
│
├── .devcontainer/devcontainer.json   # Codespaces 실행 설정 (포트 8501)
├── images/                           # 분석 결과 이미지
└── pyproject.toml
```

<br>

## ✨ 실행 방법

#### 1. 환경 준비

```bash
git clone https://github.com/encore-ai-campus/mle-01-p1-team3.git
```

```bash
uv sync
```

#### 2. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 만들고 아래 키를 채웁니다.

```bash
OPENAI_API_KEY=sk-...
NEXON_API_KEY=...
```

두 API 키는 **Streamlit secrets → 환경 변수 → `.env` / `secrets.toml`** 순으로 탐색하므로
`.streamlit/secrets.toml` 로 관리해도 됩니다. *(gitignore 대상)*

```toml
OPENAI_API_KEY = "sk-..."
NEXON_API_KEY  = "발급받은_넥슨_오픈API_키"
```

#### 3. 벡터 DB 구축

`chroma_db/` 는 저장소에서 관리하지 않습니다. 아래 스크립트로 한 번에 생성합니다.

```bash
uv run python src/build_chroma.py
```

`data/RAG/` 의 JSON 3종을 읽어 임베딩한 뒤 `maplestory_guides` 컬렉션(3,694 청크)을 만듭니다.
기존 디렉터리는 삭제 후 재생성하므로, **DB를 열고 있는 노트북 커널은 먼저 종료**해야 합니다.

#### 4. Streamlit 실행

```bash
uv run streamlit run src/streamlit/app.py
```

> GitHub Codespaces에서는 `.devcontainer/devcontainer.json` 설정에 따라
> 컨테이너 접속 시 8501 포트로 앱이 자동 실행됩니다.

<br>

## ✨ 팀원 소개 및 역할

**Team 3 · 엔코아 AI 캠퍼스 MLE 1기 프로젝트 1**

| 팀원 | GitHub | 담당 |
| --- | --- | --- |
| 김수민 | [@als00als](https://github.com/als00als) | 공식 가이드 · 직업 · 확률형 아이템 크롤링, 데이터 전처리 · 청킹, 임베딩, RAG 체인, Streamlit 전 페이지 구현 |
| seventy4 | [@seventy4-git](https://github.com/seventy4-git) | Playwright 기반 인벤 게시판 크롤러, YouTube Data API 수집, 도메인 사전, ChromaDB 스키마 문서화 · Text-to-SQL 진단 |
| 이승재 | — | 인벤 질문 데이터 시각화, 키워드 그룹 비교 분석, Top-K Retriever 구현 · DB 연결 |

### 회고

**김동석** : 
**이승재** :
**김수민** : 비정형 데이터 중 텍스트 데이터를 전처리하는건 처음 해봐서 어려움도 많았고 '게임'이라는 주제에서 신경 써야할게 많아 완성하기에 어려움이 있었지만 팀원들과 소통하고 잘 해결하여 만족스러운 결과를 얻을 수 있었습니다. 이후에 도메인/불용어 사전과 RAG 문서 데이터를 더 추가해서 답변 품질을 높이고 싶습니다.



#### 브랜치 전략

`main` 보호 · Feature Branch + Pull Request 리뷰 후 병합

```
feature/{이름}-data-collect      # 데이터 수집
feat/{이름}-data-process         # 전처리
feat/{이름}-rag-data-chunk       # 청킹
feat/{이름}-embedding            # 임베딩
feature/74-ragchain              # RAG 체인
feat/streamlit                   # 웹 화면
feat/top-k                       # Top-K 검색
feat/domain-dictionary           # 도메인 사전
```

#### 개발 규칙

- 커밋 메시지는 `feat:` / `fix:` / `ref:` / `chore:` 접두어 사용
- 크롤링 시 `User-Agent` 명시 및 요청 간 `REQUEST_DELAY = 1.0` 초 대기
- 원본 데이터(`data/raw/`)와 벡터 DB(`chroma_db/`)는 저장소에서 제외
- API 키는 `.env` · `secrets.toml` 로만 관리하며 절대 커밋하지 않음
