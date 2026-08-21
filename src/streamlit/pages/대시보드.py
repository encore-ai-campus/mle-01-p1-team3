import os
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_PATH = PROJECT_ROOT / "data" / "processed" / "inven_question_final.csv"


# ===================
# 분석 대시보드
# ===================
st.title("메이플스토리 유저 질문 분석")

def load_questions():
    return pd.read_csv(DATA_PATH)

df = load_questions()

# 지표
c1, c2 = st.columns(2)

c1.metric("질문 수", f"{len(df)}개")
c2.metric("카테고리 수", f"{df['category'].nunique()}개")
