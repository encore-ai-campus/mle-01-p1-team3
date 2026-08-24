# 🍄 메이플스토리 신규 · 복귀 유저를 위한 RAG 기반 가이드라인 챗봇

> 인벤 질문 게시판 **4,157건**을 분석해 뉴비가 실제로 막히는 지점을 찾고,
> 공식 가이드 · 직업 · 확률형 아이템 문서 **3,694 청크**를 벡터 DB로 구축해
> 근거 있는 답변만 돌려주는 정보 안내 서비스입니다.

<br>

## 🚩 목차

1. [기획 배경](#-기획-배경)
2. [서비스 소개](#-서비스-소개)
3. [데이터 파이프라인](#-데이터-파이프라인)
4. [데이터 분석 결과](#-데이터-분석-결과)
5. [기능 소개](#-기능-소개)
6. [기술 스택](#-기술-스택)
7. [프로젝트 구조](#-프로젝트-구조)
8. [실행 방법](#-실행-방법)
9. [팀원 소개 및 역할](#-팀원-소개-및-역할)

<br>

## ✨ 기획 배경

#### 개요

- **한 줄 설명** : 메이플스토리 신규 · 복귀 유저의 진입 장벽을 낮추는 **RAG 기반 정보 안내 챗봇**
- **서비스 명** : 

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
질문 임베딩 (ko-sroberta-multitask, 768차원)
   ↓
ChromaDB Top-K 검색 (cosine)
   ↓
build_context() — 출처 · 제목 · chunk_id · URL 을 붙인 Context 생성
   ↓
LangChain LCEL 체인 → GPT-4o-mini
   ↓
Context 기반 답변 + 출처 URL
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
     └─ jhgan/ko-sroberta-multitask · normalize_embeddings=True
                        ↓
[5] 벡터 DB 적재 (ChromaDB)
     └─ collection: maplestory_guides · hnsw:space = cosine
                        ↓
[6] 검색 · 생성 (RAG Chain)
     └─ retrieve() → build_context() → ChatPromptTemplate → GPT-4o-mini
```

#### 수집 데이터 현황

| 구분 | 원본 | 문서화 | 청킹 후 | 위치 |
| --- | ---: | ---: | ---: | --- |
| 공식 가이드 | 124건 | 124건 | **1,441 청크** | `data/RAG/maple_guides_documents_chunked.json` |
| 직업 정보 | 48건 | 48건 | 48 청크 | `data/RAG/maple_jobs_documents.json` |
| 확률형 아이템 | 57건 | 2,205행 | 2,205 청크 | `data/RAG/maple_items_documents.json` |
| 인벤 질문 게시판 | 4,244건 | — | — | `data/processed/inven_question_final.csv` (4,157건) |
| 뉴비 · 복귀 FAQ | 17건 | — | — | `data/RAG/newbi_comebak_guide.json` |

#### ChromaDB 메타데이터 스키마

```json
{
  "source": "guide",                  // 출처 (guide / jobs / items)
  "name": "보스 레이드: 자쿰 가이드",     // 문서 원본 제목
  "section_title": "보스/레이드",       // 카테고리 (필터링 핵심 키)
  "article_id": 101,                  // 원본 게시글 ID
  "board_id": 1,                      // 게시판 ID
  "url": "https://maplestory...",     // 출처 링크 (답변 시 참조 URL 제공용)
  "chunk_index": 0,                   // 문서 내 청크 순서
  "chunk_id": "guide_101_0"           // 청크 고유 식별자
}
```

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

## ✨ 기능 소개

Streamlit 멀티페이지 애플리케이션으로 구성되어 있습니다.

| 페이지 | 파일 | 기능 |
| --- | --- | --- |
| 🏘️ 홈 | `src/streamlit/pages/홈.py` | 서비스 소개 랜딩 화면 (배경 이미지 · 히어로 섹션) |
| 📊 질문 분석 대시보드 | `src/streamlit/pages/대시보드.py` | 인벤 질문 데이터 지표 · 카테고리 분포 시각화 |
| 🎮 캐릭터 정보검색 | `src/streamlit/pages/정보검색.py` | NEXON Open API 기반 캐릭터 상세 조회 |

#### 캐릭터 정보검색 상세

NEXON Open API(`open.api.nexon.com/maplestory/v1`)를 래핑한 `NexonClient` 로
캐릭터명 하나만 입력하면 아래 정보를 한 화면에 묶어서 보여줍니다.

- **CHARACTER SUMMARY** — 캐릭터 이미지 · 레벨 · 월드 · 직업 · 길드 · 인기도
- **종합 능력치** — `final_stat` 전체를 3열 그리드로 표시
- **ABILITY / HYPER STAT** — 활성 프리셋을 자동 판별해 표시
- **장착 장비 / 심볼** — 아이콘 포함, 상위 항목 표시 + 확장 뷰
- **성향** — Plotly 레이더 차트
- **유니온 / 길드** — 유니온 레벨 · 등급 · 공격대원 수, 길드 레벨 · 인원

API 오류는 `NexonApiError` 로 일원화해 NEXON 오류 코드(`OPENAPI00001`~`OPENAPI00011`)를
한국어 안내 메시지로 변환합니다.

```python
try:
    client.get_basic(ocid)
except NexonApiError as e:
    st.error(e.user_message)   # "API 호출량을 초과했습니다. 잠시 후 다시 시도해 주세요."
```

#### RAG 챗봇 (노트북 단계)

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 메이플스토리 정보 안내 챗봇입니다.\n"
               "반드시 제공된 Context를 기반으로 답변하세요.\n"
               "Context에 없는 정보는 임의로 만들어내지 마세요."),
    ("human", "[Context]\n{context}\n\n[Question]\n{question}"),
])

rag_chain = (
    {"context": retrieve_runnable | RunnableLambda(build_context),
     "question": RunnablePassthrough()}
    | prompt | model | StrOutputParser()
)
```

<br>

## ✨ 기술 스택

| 영역 | 스택 |
| --- | --- |
| **언어 · 환경** | Python 3.12, uv |
| **데이터 수집** | requests, BeautifulSoup4, Playwright, YouTube Data API v3, NEXON Open API |
| **데이터 처리 · 분석** | pandas, numpy, kiwipiepy, scikit-learn, wordcloud, networkx |
| **임베딩** | sentence-transformers (`jhgan/ko-sroberta-multitask`, 768차원) |
| **벡터 DB** | ChromaDB (cosine), Qdrant |
| **LLM · RAG** | LangChain (LCEL), langchain-openai, GPT-4o-mini, LangGraph |
| **평가** | RAGAS (ID 기반 Context Precision / Recall) |
| **관측성** | Langfuse |
| **프론트엔드** | Streamlit, Plotly, matplotlib, seaborn |
| **협업** | Git / GitHub (Feature Branch + PR), Notion |

<br>

## ✨ 프로젝트 구조

```
mle-01-p1-team3/
├── data/
│   ├── raw/                          # 원본 수집 데이터 (gitignore)
│   │   └── maple_inven_questions_원본.csv
│   ├── processed/                    # 전처리 결과
│   │   ├── inven_question_final.csv  # 질문 4,157건 (대시보드 데이터 소스)
│   │   ├── maple_items_process.json
│   │   └── stopwords_ko.json         # 한국어 불용어 679개
│   ├── RAG/                          # 벡터 DB 적재용 Document
│   │   ├── maple_guides_documents_chunked.json   # 1,441 청크
│   │   ├── maple_jobs_documents.json             #    48 청크
│   │   ├── maple_items_documents.json            # 2,205 청크
│   │   └── newbi_comebak_guide.json
│   ├── Top-k/Top_k.ipynb             # Top-K retriever 구현
│   └── data/chroma_db/               # ChromaDB persist 디렉터리
│
├── src/
│   ├── data_collect/
│   │   ├── als00als/                 # 공식 가이드 · 직업 · 아이템 · 인벤 크롤링
│   │   └── seventy4/                 # Playwright 인벤 크롤러 · YouTube API
│   ├── embedding.py                  # Document 통합 · chunk_id 부여 · 임베딩
│   └── streamlit/
│       ├── app.py                    # st.navigation 진입점
│       ├── nexon_client.py           # NEXON Open API 클라이언트
│       ├── dashboard_utils.py        # 응답 포맷팅 유틸
│       ├── assets/
│       └── pages/{홈,대시보드,정보검색}.py
│
├── notebooks/
│   ├── inven_eda.ipynb               # 인벤 데이터 EDA
│   ├── inven_data_process.ipynb      # 정제 파이프라인
│   ├── inven_data_analysis_new.ipynb # 키워드 · 토크나이즈 분석
│   ├── inven_guide_document.ipynb    # Document 변환
│   ├── inven_guide_chunking.ipynb    # 청킹
│   ├── data_embedding.ipynb          # 임베딩
│   ├── Chromadb_connect.ipynb        # ChromaDB 스키마 · 적재
│   ├── build_context.ipynb           # Context 빌더
│   └── rag_chain.ipynb               # LCEL RAG 체인
│
├── 인벤데이터 시각화/
│   ├── visualization.ipynb           # 조회수 · 키워드 · 그룹 비교 시각화
│   ├── figures/                      # 결과 그래프
│   └── outputs/                      # 분석 결과 CSV / PKL
│
├── api_streamlit_test/               # NEXON API 프로토타입
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
YOUTUBE_API_KEY=...
GEMINI_API_KEY=...
```

NEXON Open API 키는 Streamlit secrets 로 관리합니다.
`src/streamlit/.streamlit/secrets.toml` 을 생성하세요. *(gitignore 대상)*

```toml
NEXON_API_KEY = "발급받은_넥슨_오픈API_키"
```

#### 3. 벡터 DB 구축

`chroma_db/` 는 저장소에서 관리하지 않습니다. 아래 노트북을 순서대로 실행해 직접 생성합니다.

```
notebooks/inven_guide_document.ipynb   →  Document 변환
notebooks/inven_guide_chunking.ipynb   →  청킹
notebooks/Chromadb_connect.ipynb       →  ChromaDB 적재
```

#### 4. Streamlit 실행

```bash
uv run streamlit run src/streamlit/app.py
```

<br>

## ✨ 팀원 소개 및 역할

**Team 3 · 엔코아 AI 캠퍼스 MLE 1기 프로젝트 1**

| 팀원 | GitHub | 담당 |
| --- | --- | --- |
| 김수민 | [@als00als](https://github.com/als00als) | 공식 가이드 · 직업 · 확률형 아이템 크롤링, 데이터 전처리 · 청킹, 임베딩, RAG 체인, Streamlit 화면 구성 |
| seventy4 | [@seventy4-git](https://github.com/seventy4-git) | Playwright 기반 인벤 게시판 크롤러, YouTube Data API 수집, 도메인 사전 구축 |
| 이승재 | — | 인벤 질문 데이터 시각화, 키워드 그룹 비교 분석, Top-K Retriever 구현 · DB 연결 |

#### 브랜치 전략

`main` 보호 · Feature Branch + Pull Request 리뷰 후 병합

```
feature/{이름}-data-collect      # 데이터 수집
feat/{이름}-data-process         # 전처리
feat/{이름}-rag-data-chunk       # 청킹
feat/{이름}-embedding            # 임베딩
feat/{이름}-rag-chain            # RAG 체인
feat/streamlit                   # 웹 화면
feat/top-k                       # Top-K 검색
feat/domain-dictionary           # 도메인 사전
```

#### 개발 규칙

- 커밋 메시지는 `feat:` / `fix:` / `ref:` / `chore:` 접두어 사용
- 크롤링 시 `User-Agent` 명시 및 요청 간 `REQUEST_DELAY = 1.0` 초 대기
- 원본 데이터(`data/raw/`)와 벡터 DB(`chroma_db/`)는 저장소에서 제외
- API 키는 `.env` · `secrets.toml` 로만 관리하며 절대 커밋하지 않음
