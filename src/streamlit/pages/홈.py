from __future__ import annotations

import base64
import html
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st


PAGE_DIR = Path(__file__).resolve().parent
ASSET_DIR = PAGE_DIR.parent / "assets"
PROJECT_ROOT = PAGE_DIR.parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "inven_question_final.csv"


def asset_data_uri(path: Path) -> str:
    if not path.is_file():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


icon_uri = asset_data_uri(ASSET_DIR / "메이플_아이콘.png")
brand_icon = f'<img src="{icon_uri}" alt="메이플 아이콘">' if icon_uri else ""

q_uri = asset_data_uri(ASSET_DIR / "top질문_아이콘.png")
ques_icon = f'<img src="{q_uri}" alt="top질문 아이콘">' if q_uri else ""

st.markdown(
    f"""
    <style>
    :root {{ --purple:#7258e9; --purple-dark:#5941d2; --ink:#273043; --line:#e7eaf2; }}
    .block-container {{ max-width:none; padding:0 !important; }}
    .center-logo {{ width:100%; text-align:center; margin:0 auto; }}
    .center-logo img {{ width:185px; height:185px; object-fit:contain; }}
    .home-hero {{ min-height:92px; padding:66px 7vw 0; text-align:center; color:white; position:relative; }}
    .hero-inner {{ position:relative; z-index:1; max-width:900px; margin:0 auto; }}
    .eyebrow {{ font-size:15px; letter-spacing:.34em; font-weight:700; text-shadow:0 1px 2px rgba(0,0,0,.6), 0 2px 10px rgba(0,0,0,.5); }}
    .hero-brand {{ display:inline-flex; align-items:center; justify-content:center; gap:14px; margin:16px 0 8px;
        font-size:46px; font-weight:800; line-height:1; text-shadow:0 2px 4px rgba(0,0,0,.6), 0 4px 18px rgba(0,0,0,.5); }}
    .hero-brand img {{ width:1.9em; height:1.9em; object-fit:contain; }}
    .hero-subtitle {{ margin:0 0 26px; font-size:20px; font-weight:700; text-shadow:0 1px 3px rgba(0,0,0,.6), 0 3px 14px rgba(0,0,0,.5); }}
    .hero-hint {{ color:rgba(39,48,67,.84); font-size:15px; font-weight:600; margin-top:13px; }}
    .home-logo {{ margin:15px auto 0; width:185px; height:145px; object-fit:contain; }}
    div[data-testid="stTextInput"] {{ max-width:760px; margin:0 auto; }}
    div[data-testid="stTextInput"] input {{ height:64px; padding:0 30px; border:0; border-radius:34px; background:rgba(255,255,255,.96);
        color:var(--ink); font-size:19px; box-shadow:0 7px 25px rgba(41,57,95,.18); }}
    div[data-testid="stTextInput"] input:focus {{ border-color:transparent; box-shadow:0 0 0 3px rgba(114,88,233,.22),0 7px 25px rgba(41,57,95,.18); }}
    div[data-testid="stTextInput"] input::placeholder {{ color:#9298a5; opacity:1; }}
    div[data-testid="stForm"] {{ background:rgba(23,30,52,.62); backdrop-filter:blur(7px); border:1px solid rgba(255,255,255,.16);
        border-radius:18px; padding:20px 22px; margin:0 auto 34px; box-shadow:0 14px 34px rgba(15,20,40,.28); }}
    div[data-testid="stForm"] div[data-testid="stMarkdownContainer"] p {{ color:#f2f4fa; font-size:15px; font-weight:700; }}
    div[data-testid="stForm"] div[data-testid="stTextInput"] {{ max-width:none; margin:0; }}
    div[data-testid="stForm"] div[data-testid="stTextInput"] input {{ height:44px; padding:0 14px; border:1px solid rgba(255,255,255,.12);
        border-radius:10px; background:rgba(255,255,255,.10); color:#f2f4fa; font-size:15px; font-weight:400; box-shadow:none; }}
    div[data-testid="stForm"] div[data-testid="stTextInput"] input::placeholder {{ color:rgba(238,240,250,.55); opacity:1; }}
    div[data-testid="stForm"] button {{ width:100%; height:44px; min-height:44px; padding:0; border:0;
        border-radius:10px; background:#FA7000; color:#fff; box-shadow:0 4px 12px rgba(250,112,0,.30); }}
    div[data-testid="stForm"] button:hover {{ background:#e06400; border-color:transparent; color:#fff; }}
    div[data-testid="stForm"] button p {{ color:#fff; font-size:15px; font-weight:700; }}
    .search-button {{ margin-left:-82px; position:relative; z-index:2; }}
    .search-button button {{ width:54px; height:54px; margin-top:5px; border:0; border-radius:50%; background:var(--purple); color:white;
        font-size:24px; box-shadow:0 6px 15px rgba(89,65,210,.35); }}
    .search-button button:hover {{ background:var(--purple-dark); color:white; border-color:transparent; }}
    .hero-actions {{ margin-top:20px; }}
    .hero-actions button {{ border-radius:24px; min-height:44px; font-weight:800; padding:0 22px; }}
    .hero-actions button[kind="primary"] {{ background:var(--purple); border-color:var(--purple); color:white; }}
    .hero-actions button:not([kind="primary"]) {{ background:white; border-color:#e1e4ec; color:var(--ink); }}
    .cards-wrap {{ max-width:90%; margin:-74px auto 0; position:relative; z-index:3; padding-bottom:28px; }}
    .home-card {{ background:rgba(255,255,255,.96); border:1px solid rgba(220,224,235,.82); border-radius:20px; padding:24px 22px 20px;
        box-shadow:0 9px 28px rgba(48,57,82,.12); min-height:315px; }}
    .card-heading {{ display:flex; align-items:center; justify-content:space-between; color:var(--ink); font-size:21px; font-weight:800; margin-bottom:18px; }}
    .card-heading span {{ color:var(--purple); font-size:14px; font-weight:800; }}
    .list-row {{ display:flex; align-items:center; gap:14px; min-height:48px; border-top:1px solid #edf0f5; color:#3d4555; font-size:14px; }}
    .list-row:first-of-type {{ border-top:0; }}
    .dday {{ display:inline-flex; align-items:center; justify-content:center; min-width:58px; padding:6px 9px; border-radius:7px; color:white; font-weight:800; font-size:13px; }}
    .dday-near {{ background:#ff9d1d; }} .dday-far {{ background:#578ce3; }}
    .notice-date {{ min-width:82px; color:#7e8798; font-size:13px; }}
    .notice-title {{ min-width:0; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }}
    .home-footer {{ text-align:center; color:#a4aab7; font-size:13px; padding:0 0 25px; }}
    @media (max-width:800px) {{ [data-testid="stAppViewContainer"] {{ background-size:100% 100%, 100% auto; }} .home-hero {{ min-height:92px; padding:45px 20px 0; }} .eyebrow {{ font-size:12px; letter-spacing:.2em; }}
        .hero-subtitle {{ font-size:16px; }} .hero-brand {{ font-size:34px; }} .cards-wrap {{ max-width:92%; margin-top:28px; }} .home-card {{ margin-bottom:18px; }} .search-button {{ margin-left:-72px; }} }}

    /* ===== 흰색 글씨 가독성용 그림자 ===== */
    div[data-testid="stForm"] div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stForm"] button p,
    .search-button button,
    .hero-actions button[kind="primary"],
    .dday {{ text-shadow: 0 1px 3px rgba(0, 0, 0, .45); }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <section class="home-hero"><div class="hero-inner">
      <div class="eyebrow">MAPLESTORY SEARCH &amp; CHAT</div>
      <div class="hero-brand">{brand_icon}메이플 스토리</div>
      <div class="hero-subtitle">뉴비를 위한 가이드라인 웹사이트</div>
    </div></section>
    """,
    unsafe_allow_html=True,
)


# ===================
# 캐릭터 검색 (결과는 '캐릭터 정보검색' 페이지에서 표시)
# ===================
_, search_center, _ = st.columns([1, 18, 1])
with search_center:
    with st.form("home_character_search", border=True):
        st.markdown("**캐릭터명을 입력하세요**")
        query_col, button_col = st.columns([6, 1])
        with query_col:
            character_name = st.text_input(
                "캐릭터명",
                placeholder="캐릭터명을 입력하세요",
                label_visibility="collapsed",
                key="home_character_query",
            )
        with button_col:
            search_clicked = st.form_submit_button("조회", type="primary", width="stretch")

if search_clicked:
    if not character_name.strip():
        st.warning("캐릭터명을 입력해주세요.")
    else:
        st.session_state.pending_character_name = character_name.strip()
        st.switch_page("pages/정보검색.py")


# ===================
# 인기 질문 랭킹 (추천 수 / 조회 수 TOP 10)
# ===================
@st.cache_data
def load_questions() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def top_questions(df: pd.DataFrame, column: str) -> list[tuple[str, int]]:
    ranked = (
        df[["title", column]]
        .assign(**{column: pd.to_numeric(df[column], errors="coerce")})
        .dropna(subset=[column])
        .sort_values(column, ascending=False)
        .head(10)
    )
    return [(str(title), int(value)) for title, value in ranked.itertuples(index=False)]


def rank_card(title_ko: str, title_en: str, rows: list[tuple[str, int]], unit: str) -> str:
    row_html = "".join(
        f'<div class="rank-row">'
        f'<span class="rank-no rank-{"gold" if no == 1 else "silver" if no <= 3 else "blue"}">{no}위</span>'
        f'<span class="rank-title">{html.escape(title)}</span>'
        f'<span class="rank-value">{value:,}{unit}</span></div>'
        for no, (title, value) in enumerate(rows, start=1)
    )
    return (
        '<div class="rank-card">'
        f'<div class="rank-head">{ques_icon}'
        f'<span class="rank-head-text"><b>{title_ko}</b><em>{title_en}</em></span></div>'
        f'<div class="rank-body">{row_html}</div></div>'
    )


st.markdown(
    """
    <style>
    .rank-wrap { display:flex; gap:22px; width:90%; max-width:1480px; margin:30px auto 44px; }
    .rank-card { flex:1; min-width:0; background:rgba(23,30,52,.62); backdrop-filter:blur(7px);
        border:1px solid rgba(255,255,255,.16); border-radius:18px; padding:16px 18px 18px;
        box-shadow:0 14px 34px rgba(15,20,40,.28); }
    .rank-head { display:flex; align-items:center; gap:12px; margin-bottom:12px; }
    .rank-head img { width:46px; height:46px; object-fit:contain; flex:none; }
    .rank-head-text { flex:1; min-width:0; display:flex; flex-direction:column; line-height:1.25; }
    .rank-head-text b { color:#ffd45c; font-size:20px; font-weight:800; }
    .rank-head-text em { color:rgba(255,255,255,.6); font-size:12px; font-style:normal; font-weight:600; }
    .rank-more { color:rgba(255,255,255,.72); font-size:13px; font-weight:600; flex:none; }
    .rank-row { display:flex; align-items:center; gap:14px; background:rgba(255,255,255,.10); border-radius:10px;
        padding:11px 14px; margin-top:8px; color:#f2f4fa; font-size:14px; }
    .rank-row:first-child { margin-top:0; }
    .rank-no { flex:none; min-width:54px; padding:5px 0; text-align:center; border-radius:6px;
        color:white; font-weight:800; font-size:13px; }
    .rank-gold { background:#e8465f; } .rank-silver { background:#f0a02a; } .rank-blue { background:#4f86dd; }
    .rank-title { flex:1; min-width:0; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
    .rank-value { flex:none; color:rgba(255,255,255,.66); font-size:13px; font-weight:700; }
    @media (max-width:900px) { .rank-wrap { flex-direction:column; width:94%; } }

    /* ===== 흰색 글씨 가독성용 그림자 ===== */
    .rank-head-text em,
    .rank-more,
    .rank-row,
    .rank-no,
    .rank-value { text-shadow: 0 1px 3px rgba(0, 0, 0, .45); }
    </style>
    """,
    unsafe_allow_html=True,
)

questions = load_questions()

st.markdown(
    '<div class="rank-wrap">'
    + rank_card("추천 많은 질문", "Most Liked Questions", top_questions(questions, "likes"), "개")
    + rank_card("조회 많은 질문", "Most Viewed Questions", top_questions(questions, "views"), "회")
    + "</div>",
    unsafe_allow_html=True,
)
