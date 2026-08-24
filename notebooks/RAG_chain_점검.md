주된 원인은 `OpenAI API` 자체보다, 현재 [`notebooks/rag_chain_retriever.ipynb`](D:/encore/mle-01-p1-team3/notebooks/rag_chain_retriever.ipynb) 의 검색 설계가 질문 의도를 충분히 좁히지 못하는 데 있어 보입니다.

**Findings**
1. 검색 대상 컬렉션이 너무 넓은데, 질문 유형별 분기가 없습니다. [`notebooks/rag_chain_retriever.ipynb:98`](D:/encore/mle-01-p1-team3/notebooks/rag_chain_retriever.ipynb:98) 에서 단일 컬렉션 `maplestory_guides`만 연결하고, [`notebooks/rag_chain_retriever.ipynb:107`](D:/encore/mle-01-p1-team3/notebooks/rag_chain_retriever.ipynb:107) 에서 아무 필터 없이 `as_retriever(search_kwargs={'k': 4})`만 사용합니다. 실제 DB를 확인해 보니 이 컬렉션 안에는 `items 2205`, `guide 1441`, `jobs 48`이 함께 들어 있습니다. 그래서 “직업 추천” 같은 질문도 아이템/가이드 문서에 묻혀 버릴 가능성이 큽니다.

2. `k=4` 고정 검색은 질문이 조금만 넓어져도 근거가 부족합니다. [`notebooks/rag_chain_retriever.ipynb:109`](D:/encore/mle-01-p1-team3/notebooks/rag_chain_retriever.ipynb:109) 에서 상위 4개만 가져오는데, 데이터 분포상 서로 다른 source가 섞이면 모델이 공통분모만 뽑아 애매하게 답하기 쉽습니다. 특히 `jobs` 문서는 48개뿐이라, 직업 질문에서도 관련 가이드 조각 몇 개가 먼저 잡히면 답변이 흐려질 수 있습니다.

3. `build_context()`가 검색 결과를 그대로 길게 이어 붙여서, 핵심 신호보다 잡음이 커집니다. [`notebooks/rag_chain_retriever.ipynb:156`](D:/encore/mle-01-p1-team3/notebooks/rag_chain_retriever.ipynb:156) 이후 로직은 각 문서의 `page_content`를 거의 통째로 넣고 있습니다. 요약, 문서별 핵심 포인트 추출, source별 그룹화가 없어서 LLM이 “정답 후보”보다 “긴 참고문”을 받는 구조입니다.

4. 프롬프트가 안전하긴 하지만, 선명한 답변을 유도하는 지시가 약합니다. [`notebooks/rag_chain_retriever.ipynb:192`](D:/encore/mle-01-p1-team3/notebooks/rag_chain_retriever.ipynb:192) 의 프롬프트는 “context에 근거해서만 답하라”는 제한은 좋지만, “가장 관련 높은 근거를 먼저 요약”, “질문이 추천형이면 비교 기준을 명시”, “근거가 부족하면 부족한 이유를 말하라” 같은 출력 전략이 없습니다. 그래서 모델이 보수적으로 두루뭉술한 문장을 만들기 쉽습니다.

5. 검색 결과 진단 장치는 있지만, 실제 품질 점검용으로는 부족합니다. [`notebooks/rag_chain_retriever.ipynb:131`](D:/encore/mle-01-p1-team3/notebooks/rag_chain_retriever.ipynb:131) 에서 `retriever.invoke(question)` 결과를 일부 출력하긴 하지만, 점수, source 분포, 왜 이 문서가 뽑혔는지까지는 보지 않습니다. 지금 상태에선 “답이 왜 흐린지”를 체감은 해도 정확히 어느 문서가 문제인지 바로 파악하긴 어렵습니다.

6. 컬렉션 이름과 실제 내용이 어긋나 있어 운영 관점에서 혼동을 만듭니다. [`notebooks/rag_chain_retriever.ipynb:99`](D:/encore/mle-01-p1-team3/notebooks/rag_chain_retriever.ipynb:99) 의 이름은 `maplestory_guides`지만 실제로는 `guide`, `items`, `jobs`가 함께 들어 있습니다. 이건 검색 품질을 직접 망치는 버그는 아니지만, 필터 설계나 디버깅 판단을 흐리게 만들 수 있습니다.

**정리**
현재 답변이 불명확한 가장 큰 이유는 `LLM이 못해서`라기보다, `질문 유형에 비해 너무 섞인 컬렉션에서 너무 적은 문서를 가져오고`, 그 문서들을 `정제 없이 길게 붙여` 모델에 넘기기 때문입니다. 즉 병목은 `retriever 설계`와 `context 구성` 쪽입니다.

**다음에 손보면 효과가 큰 순서**
- `source` 기준 필터 또는 질문 라우팅 추가
- `k` 조정과 `MMR` 또는 `score threshold` 검토
- `build_context()`에서 문서 요약/정렬/중복 제거
- 추천형 질문에 맞는 프롬프트 강화
- 검색 결과 진단용 출력 추가



`bounded`로 보고 짧은 설계를 먼저 잡겠습니다. 추천 방향은 `rag_chain_retriever.ipynb` 안에서 질문을 먼저 `guide / jobs / items / mixed`로 라우팅하고, 그 결과에 따라 retriever 필터와 `k`를 다르게 적용한 뒤, `build_context()`에서 문서 전문을 그대로 붙이지 말고 문서별 핵심 정보만 압축해서 넘기는 방식입니다.

구체적으로는 이렇게 가면 좋습니다. `1)` 질문 분류 함수 추가: 직업 추천/성능 비교는 `jobs`, 아이템 획득/옵션은 `items`, 시스템/콘텐츠 설명은 `guide`, 애매하면 `mixed`. `2)` retriever를 하나만 쓰지 않고 source별 필터를 주는 retriever 생성 함수로 바꾸기. `3)` `build_context()`는 문서 전체 대신 제목, source, 핵심 본문 일부, URL만 정리하고 중복되는 내용은 줄이기. `4)` 프롬프트는 “질문 의도에 맞는 결론부터 말하고, 근거 문서를 1-3개 인용하라. 근거 부족 시 부족하다고 명시하라”로 강화하기. `5)` 디버그 셀에서는 검색된 문서의 `source`, `title/name`, 일부 본문을 같이 보여서 왜 답이 흐린지 바로 확인할 수 있게 만들기. 테스트는 대표 질문 3종 정도로 보겠습니다: 직업 추천형, 아이템 정보형, 가이드 설명형.

