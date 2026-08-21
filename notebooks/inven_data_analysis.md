# INVEN 질문/답변(Q&A) 게시판 데이터 분석

> **수집 데이터 크기 (행, 열)** : `4157, 12`
> **수집 기간** : `2026-06-17 ~ 2026-08-19`
> **카테고리** : `기타 / 몬스터 / 시세 / 아이템 / 직업 / 퀘스트`

---

#### 1. 라이브러리 및 환경 설정
```python
import re
import json
from collections import Counter
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from kiwipiepy import Kiwi
from wordcloud import WordCloud
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from collections import Counter, defaultdict    # 카테고리별로 Counter를 각각 가질 수 있는 딕셔너리 생성
import platform

# 한글 폰트 — 실행 중인 OS 에 맞춰 자동 설정
if platform.system() == 'Windows':
    KOREAN_FONT = 'Malgun Gothic'
    FONT_PATH = 'C:/Windows/Fonts/malgun.ttf'
elif platform.system() == 'Darwin':          # macOS
    KOREAN_FONT = 'AppleGothic'
    FONT_PATH = '/System/Library/Fonts/Supplemental/AppleGothic.ttf'
else:                                        # Linux (Colab 등)
    KOREAN_FONT = 'NanumGothic'
    FONT_PATH = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'

plt.rcParams['font.family'] = KOREAN_FONT
plt.rcParams['axes.unicode_minus'] = False   # 마이너스(−) 부호 깨짐 방지

kiwi = Kiwi()   # 한국어 형태소 분석기(자바 불필요)
```

---

#### 2. RAW 데이터 확인
###### (1) category / info. 확인  
```python
DATA SIZE : (4157, 12)

CATEGORY
카테고리 수: 6개 [['기타' '아이템' '퀘스트' '직업' '시세' '몬스터']]

DATA INFO
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 4157 entries, 0 to 4156
Data columns (total 12 columns):
 #   Column               Non-Null Count  Dtype 
---  ------               --------------  ----- 
 0   category             4157 non-null   object
 1   title                4157 non-null   object
 2   created_at           4157 non-null   object
 3   views                4157 non-null   int64 
 4   likes                4157 non-null   int64 
 5   content              4157 non-null   object
 6   comment_count        4157 non-null   int64 
 7   title_clean          4157 non-null   object
 8   content_clean        4156 non-null   object
 9   analysis_text        4157 non-null   object
 10  has_question_signal  4157 non-null   bool  
 11  is_question          4157 non-null   bool  
dtypes: bool(2), int64(3), object(7)
memory usage: 333.0+ KB
```
###### (2) head(3) 확인
<img src="../images/RAW DATA HEAD 실행 결과.png">

---

#### 3. DATA Tokenize

###### (1) RAW 데이터 복제 및 tokens 칼럼 추가
```python
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 4157 entries, 0 to 4156
Data columns (total 13 columns):
 #   Column               Non-Null Count  Dtype 
---  ------               --------------  ----- 
 0   category             4157 non-null   object
 1   title                4157 non-null   object
 2   created_at           4157 non-null   object
 3   views                4157 non-null   int64 
 4   likes                4157 non-null   int64 
 5   content              4157 non-null   object
 6   comment_count        4157 non-null   int64 
 7   title_clean          4157 non-null   object
 8   content_clean        4156 non-null   object
 9   analysis_text        4157 non-null   object
 10  has_question_signal  4157 non-null   bool  
 11  is_question          4157 non-null   bool  
 12  tokens               4157 non-null   object
dtypes: bool(2), int64(3), object(8)
memory usage: 365.5+ KB
```
###### (2) head() 확인
<img src="../images/TOKENIZE HEAD 실행 결과.png">

###### (3) 카테고리별 질문 수
<img src="../images/카테고리별 질문 수 확인.png">

###### (4) 카테고리별 VIEWS 합계
```python
카테고리별 VIEWS
category
기타     1444263
몬스터     143017
시세      147318
아이템    1827157
직업      342270
퀘스트     127602
Name: views, dtype: int64
```

###### (5) VIEWS 상위 게시글 TOP 5
<img src="../images/VIEWS 상위 게시글 TOP 5.png">

---

#### 4. 빈도 상위 단어 확인

###### (1) 가장 많이 언급된 단어 상위 20개 내역
<img src='../images/가장 많이 본 글의 단어 top20.png'>

###### (2) 카테고리별 가장 많이 언급된 단어 상위 5개 내역
<table border=0>
<tr valign=top border=0>
    <td><img src="../images/카테고리별 핵심 키워드 top 5 (1).png"></td>
    <td><img src="../images/카테고리별 핵심 키워드 top 5 (2).png"></td>
</table>

---

#### 5. **<font color=green>뉴비/복귀 유저 포함 데이터</font>**

###### (1) 가장 많이 언급된 단어 상위 20개 내역

<img src='../images/가장 많이 본 글의 단어(뉴비_복귀포함) top20.png'>

###### (2) 카테고리별 가장 많이 언급된 단어 상위 5개 내역
<table border=0>
<tr valign=top border=0>
    <td><img src="../images/카테고리별 핵심 키워드(뉴비_복귀포함) top 5 (1).png"></td>
    <td><img src="../images/카테고리별 핵심 키워드(뉴비_복귀포함) top 5 (2).png"></td>
</table>

###### (3) 뉴비/복귀 유저가 언급된 게시글 내역 (head)
```python
(938, 13)
```
<img src="../images/뉴비_복귀 유저가 언급된 게시글(head).png">
---

#### 6. 데이터 분석 결과
> - **데이터 수집 기간 동안 INVEN 질문/답변(Q&A) 게시판 카테고리 중 `"아이템"(2,031), "기타"(1,332)`의 질문 수가 다른 카테고리와 비교해 월등히 많았고, 조횟수 역시, `"아이템"(1,827,157), "기타"(4144,263)`로 다른 카테고리와 비교해 월등히 많았다.**
>
> - **조횟수(VIEWS) 최상위 게시글은 조횟수(35,501)의 `"노말 카이 최소컷이 몇이에요? 지금 레테 리레4랩 컨티3랩있고 투력 1300만인데 ..."`으로, 토큰화된 단어는 `"카이, 최소, 레테, 컨티, 투력"` 으로 확인 됐다.**
>
> - **전체 카테고리에서 가장 많이 언급된 단어(포함된 글 수)는 `"챌섭"(1,028), "무기"(459), "해방"(416), "보조"(415), "보스"(381)`으로 확인 됐다.**
>
> - **<font color=yellow>"뉴비", "복귀"</font> 유저와 관련된 단어를 포함해 분석해 본 결과,
>   `"뉴비"(500), "시작"(251), "복귀"(243)`이 많이 본 글 top 20에 포함된 것이 확인 됐다. **
> 
