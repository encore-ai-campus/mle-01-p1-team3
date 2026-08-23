import os
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import base64
from pathlib import Path

import streamlit as st

FONT_PATH = Path(__file__).resolve().parent / "assets" / "MaplestoryLight.ttf"


@st.cache_data(show_spinner=False)
def font_face_css(path: str) -> str:
    encoded = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f"""
    <style>
    @font-face {{
        font-family: 'Maplestory Light';
        src: url(data:font/ttf;base64,{encoded}) format('truetype');
        font-weight: 100 900;
        font-display: swap;
    }}
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
    h1, h2, h3, h4, h5, h6, p, div, span, a, li, td, th, label, button, input, textarea, select {{
        font-family: 'Maplestory Light', 'Malgun Gothic', sans-serif !important;
    }}
    span[data-testid="stIconMaterial"], .material-icons, .material-icons-outlined,
    [class*="material-symbols"], [data-testid="stIconEmoji"] {{
        font-family: 'Material Symbols Rounded', 'Material Icons' !important;
    }}
    code, pre, kbd, samp {{ font-family: 'Source Code Pro', monospace !important; }}
    </style>
    """

st.set_page_config(page_title="MapleStory Search & Chat", page_icon="🍄", layout="wide", initial_sidebar_state="expanded")

st.markdown(font_face_css(str(FONT_PATH)), unsafe_allow_html=True)

with st.sidebar:
    st.session_state.sidebar_slot = st.empty()

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
