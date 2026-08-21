import os
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

# app.py와 nexon_client.py가 같은 폴더에 있음
STREAMLIT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(STREAMLIT_DIR))

from nexon_client import NexonApiError, NexonClient

st.set_page_config(page_title="메이플스토리 스타터 유저 가이드라인", page_icon="🍁", layout="wide")

with st.sidebar:
    st.session_state.sidebar_slot = st.empty()
    st.divider

pg = st.navigation(
    {
        "시작": [
            st.Page("pages/홈.py", title="홈", icon="🏘️", default=True),
        ],
        "분석" : [
            st.Page("pages/대시보드.py", title="질문 분석 대시보드", icon="📊"),
        ],
        "정보검색" : [
            st.Page("pages/정보검색.py", title="캐릭터 정보검색", icon="🎮"),
        ],
    }
)

pg.run()