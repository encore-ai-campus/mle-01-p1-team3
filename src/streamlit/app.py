import os
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import base64
from pathlib import Path

import streamlit as st

ASSET_DIR = Path(__file__).resolve().parent / "assets"
FONT_PATH = ASSET_DIR / "MaplestoryLight.ttf"
BACKGROUND_PATH = ASSET_DIR / "배경.png"


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

@st.cache_data(show_spinner=False)
def background_css(path: str) -> str:
    """모든 페이지 공통 배경 이미지."""
    image = Path(path)
    if not image.is_file():
        return ""
    encoded = base64.b64encode(image.read_bytes()).decode("ascii")
    return f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        min-height: 100vh;
        background-image:
            linear-gradient(rgba(255, 255, 255, .6), rgba(255, 255, 255, .6)),
            url(data:image/png;base64,{encoded});
        background-size: 100% 100%, 100% auto;
        background-position: center top;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    [data-testid="stHeader"] {{ background: transparent; }}
    </style>
    """



# 챗봇 히어로와 동일한 반투명 다크 패널. 컨테이너 안에 .glass-anchor 를 넣으면 적용된다.
GLASS_ANCHOR = '<span class="glass-anchor"></span>'
GLASS_SCOPE = 'div[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .glass-anchor)'
PANEL_CSS = f"""
<style>
{GLASS_SCOPE} {{
    background: rgba(23, 30, 52, .62);
    backdrop-filter: blur(7px);
    border: 1px solid rgba(255, 255, 255, .16);
    border-radius: 18px;
    padding: 18px 22px;
    margin-bottom: 16px;
    box-shadow: 0 14px 34px rgba(15, 20, 40, .28);
}}
{GLASS_SCOPE} h1,
{GLASS_SCOPE} h2,
{GLASS_SCOPE} h3,
{GLASS_SCOPE} [data-testid="stMetricLabel"],
{GLASS_SCOPE} [data-testid="stMetricLabel"] p,
{GLASS_SCOPE} [data-testid="stMetricValue"],
{GLASS_SCOPE} [data-testid="stMarkdownContainer"] p {{
    color: #f2f4fa !important;
    text-shadow: 0 1px 3px rgba(0, 0, 0, .45);
}}
/* 앵커 자체는 자리를 차지하지 않게 숨긴다. */
[data-testid="stElementContainer"]:has(.glass-anchor) {{ display: none; }}
</style>
"""


st.set_page_config(page_title="MapleStory Search & Chat", page_icon="🍄", layout="wide", initial_sidebar_state="expanded")

st.markdown(font_face_css(str(FONT_PATH)), unsafe_allow_html=True)
st.markdown(background_css(str(BACKGROUND_PATH)), unsafe_allow_html=True)
st.markdown(PANEL_CSS, unsafe_allow_html=True)

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
        "챗봇" : [
            st.Page("pages/챗봇.py", title="메이플스토리 가이드챗봇", icon="💬"),
        ],
    },
    position="sidebar",
)

pg.run()
