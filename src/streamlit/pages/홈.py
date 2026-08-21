from __future__ import annotations

import base64
from datetime import date
from pathlib import Path

import streamlit as st


PAGE_DIR = Path(__file__).resolve().parent
ASSET_DIR = PAGE_DIR.parent / "assets"


def asset_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


background_uri = asset_data_uri(ASSET_DIR / "배경.png")
icon_uri = asset_data_uri(ASSET_DIR / "메이플 아이콘.png")

st.markdown(
    f"""
    <style>
    :root {{ --purple:#7258e9; --purple-dark:#5941d2; --ink:#273043; --line:#e7eaf2; }}
    [data-testid="stAppViewContainer"] {{ min-height:100vh; background:#f7f8fc; background-image:url('{background_uri}');
        background-size:100% auto; background-position:center top; background-repeat:no-repeat; }}
    [data-testid="stHeader"] {{ background:transparent; }}
    .block-container {{ max-width:none; padding:0 !important; }}
    .center-logo {{ width:100%; text-align:center; margin:0 auto; }}
    .center-logo img {{ width:185px; height:185px; object-fit:contain; }}
    .home-hero {{ min-height:92px; padding:66px 7vw 0; text-align:center; color:white; position:relative; }}
    .hero-inner {{ position:relative; z-index:1; max-width:900px; margin:0 auto; }}
    .eyebrow {{ font-size:15px; letter-spacing:.34em; font-weight:700; text-shadow:0 2px 8px rgba(0,0,0,.16); }}
    .hero-subtitle {{ margin:5px 0 26px; font-size:20px; font-weight:700; text-shadow:0 2px 8px rgba(0,0,0,.24); }}
    .hero-hint {{ color:rgba(39,48,67,.84); font-size:15px; font-weight:600; margin-top:13px; }}
    .home-logo {{ margin:15px auto 0; width:185px; height:145px; object-fit:contain; }}
    div[data-testid="stTextInput"] {{ max-width:760px; margin:0 auto; }}
    div[data-testid="stTextInput"] input {{ height:64px; padding:0 30px; border:0; border-radius:34px; background:rgba(255,255,255,.96);
        color:var(--ink); font-size:19px; box-shadow:0 7px 25px rgba(41,57,95,.18); }}
    div[data-testid="stTextInput"] input:focus {{ border-color:transparent; box-shadow:0 0 0 3px rgba(114,88,233,.22),0 7px 25px rgba(41,57,95,.18); }}
    div[data-testid="stTextInput"] input::placeholder {{ color:#9298a5; opacity:1; }}
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
    @media (max-width:800px) {{ [data-testid="stAppViewContainer"] {{ background-size:100% auto; }} .home-hero {{ min-height:92px; padding:45px 20px 0; }} .eyebrow {{ font-size:12px; letter-spacing:.2em; }}
        .hero-subtitle {{ font-size:17px; }} .cards-wrap {{ max-width:92%; margin-top:28px; }} .home-card {{ margin-bottom:18px; }} .search-button {{ margin-left:-72px; }} }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <section class="home-hero"><div class="hero-inner">
      <div class="eyebrow">MAPLESTORY SEARCH &amp; CHAT</div>
      <div class="hero-subtitle">뉴비를 위한 가이드라인 웹사이트</div>
    </div></section>
    """,
    unsafe_allow_html=True,
)

# st.markdown(
#     f'<div class="center-logo"><img src="{icon_uri}" alt="메이플 아이콘"></div>',
#     unsafe_allow_html=True,
# )
    # search_col, button_col = st.columns([8, 1], gap="small")
    # with search_col:
    #     character_name = st.text_input("캐릭터명", placeholder="캐릭터명을 입력해주세요", label_visibility="collapsed", key="home_character_query")
    # with button_col:
    #     st.markdown('<div class="search-button">', unsafe_allow_html=True)
    #     search_clicked = st.button("⌕", key="home_search", help="캐릭터 검색")
    # #     st.markdown("</div>", unsafe_allow_html=True)

    # _, action_center, _ = st.columns([1, 2, 1])
    # with action_center:
    #     st.markdown('<div class="hero-actions">', unsafe_allow_html=True)
    #     st.button("📣  공지사항", key="home_notice", type="primary")
    #     st.button("☆  즐겨찾기", key="home_favorite")
#     #     st.markdown('<div class="hero-hint">즐겨찾기로 빠르게 이동하세요!</div></div>', unsafe_allow_html=True)

# if search_clicked:
#     if not character_name.strip():
#         st.warning("캐릭터명을 입력해주세요.")
#     else:
#         st.session_state.pending_character_name = character_name.strip()
#         st.switch_page("pages/정보검색.py")

# events = [
#     ("D-2", "프리미엄PC방 접속보상 이벤트 & 기프트샵", True),
#     ("D-5", "썸머 아메이플", True),
#     ("D-5", "메이플스토리에 진심! 달성 이벤트", True),
#     ("D-26", "울티아 유물 탐사", False),
#     ("D-26", "보스 격파 이벤트 - 광신도의 저격", False),
# ]
# notices = [
#     ("2026.08.21", "[수정] [패션컬럼] 8/21(금) 전체 월드 채널 점검 (14:00~15:00)"),
#     ("2026.08.20", "[패치완료] 8/20(목) ver.1.2.418 아나이버전(패치) (16:18 적용)"),
#     ("2026.08.20", "[패치완료] 8/20(목) 전체 월드 채널 패치 (15:00~16:00)"),
#     ("2026.08.20", "[완료] 8/20(목) 마스터 이벤트 에어 무료 임시 사용 제한 및 거래 제한 안내"),
#     ("2026.08.20", "[수정] 8/20(목) 넥카드 오류 안내"),
#     ("2026.08.20", "클라이언트 1.2.418 업데이트 안내"),
# ]

# st.markdown('<div class="cards-wrap">', unsafe_allow_html=True)
# card_left, card_right = st.columns(2, gap="large")
# with card_left:
#     event_rows = "".join(
#         f'<div class="list-row"><span class="dday {"dday-near" if near else "dday-far"}">{day}</span><span class="notice-title">{title}</span></div>'
#         for day, title, near in events
#     )
#     st.markdown(f'<div class="home-card"><div class="card-heading">🍄 진행중인 이벤트 <span>전체보기 〉</span></div>{event_rows}</div>', unsafe_allow_html=True)
# with card_right:
#     notice_rows = "".join(
#         f'<div class="list-row"><span class="notice-date">{notice_date}</span><span class="notice-title">{title}</span></div>'
#         for notice_date, title in notices
#     )
#     st.markdown(f'<div class="home-card"><div class="card-heading">📣 공지사항 <span>전체보기 〉</span></div>{notice_rows}</div>', unsafe_allow_html=True)
# st.markdown('</div>', unsafe_allow_html=True)
