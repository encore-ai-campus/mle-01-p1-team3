import os
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import streamlit as st

st.set_page_config(page_title="메짱 · MapleStory Search & Chat", page_icon="🍄", layout="wide", initial_sidebar_state="expanded")

with st.sidebar:
    st.markdown("# 🍁 메이플스토리 뉴비 가이드라인")
    st.caption("MapleStory Search & Chat")
    st.divider()

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
    },
    position="sidebar",
)

pg.run()
