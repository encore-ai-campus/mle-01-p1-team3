import os
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

# import io
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
# from wordcloud import WordCloud


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_PATH = PROJECT_ROOT / "data" / "processed" / "inven_question_final.csv"
FIGURE_DATA_DIR = PROJECT_ROOT / "인벤데이터 시각화" / "outputs"
# WORDCLOUD_FONT = Path(__file__).resolve().parents[1] / "assets" / "MaplestoryLight.ttf"

ORANGE = "#F0912D"
RED = "#E7503C"
YELLOW = "#F5B942"
TITLE_COLOR = "#ffffff"

# UMAP 산점도에서 카테고리(군집)를 구분할 색상
CATEGORY_COLORS = {
    "아이템": "#F0912D",
    "기타": "#8E9AAF",
    "직업": "#5B7CD8",
    "시세": "#3FA796",
    "몬스터": "#E7503C",
    "퀘스트": "#B663B6",
}
FALLBACK_COLORS = ["#F0912D", "#E7503C", "#5B7CD8", "#3FA796", "#B663B6", "#8E9AAF"]


st.markdown(
    """
    <style>
    .block-container { max-width: none; padding-left: 5rem; padding-right: 5rem; }
    /* 제목 + 그래프를 감싼 반투명 다크 패널 */
    div[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .db-anchor) {
        background: rgba(23,30,52,.62); backdrop-filter: blur(7px);
        border: 1px solid rgba(255,255,255,.16); border-radius: 18px;
        padding: 16px 22px 10px; margin-bottom: 18px; box-shadow: 0 14px 34px rgba(15,20,40,.28); }
    .db-title { color: #ffffff; font-size: 19px; font-weight: 800;
        text-shadow: 0 1px 3px rgba(0,0,0,.6), 0 3px 14px rgba(0,0,0,.5); }
    .db-sub { color: #c9d4e4; font-size: 12.5px; font-weight: 600; margin: 2px 0 6px;
        text-shadow: 0 1px 3px rgba(0,0,0,.6); }
    /* 워드클라우드 비활성화 (아래 렌더링 코드와 함께 주석 처리)
    .wc-cap { color: #e6edf8; font-size: 14px; font-weight: 800; text-align: center; margin: 10px 0 2px;
        text-shadow: 0 1px 3px rgba(0,0,0,.6); } */

    /* 제목 + 지표: 배경 없이 글씨만 (그림자로 가독성 확보) */
    div[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .db-head-anchor) { margin-bottom: 18px; }
    /* 홈 히어로(.hero-brand)와 동일한 두 겹 그림자 */
    div[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .db-head-anchor) h1 { color: #ffffff !important;
        text-shadow: 0 2px 4px rgba(0,0,0,.6), 0 4px 18px rgba(0,0,0,.5); }
    div[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .db-head-anchor) [data-testid="stMetricLabel"],
    div[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .db-head-anchor) [data-testid="stMetricLabel"] p { color: #dfe6f2 !important;
        text-shadow: 0 1px 3px rgba(0,0,0,.6), 0 3px 14px rgba(0,0,0,.5); }
    div[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .db-head-anchor) [data-testid="stMetricValue"] { color: #ffffff !important;
        text-shadow: 0 1px 3px rgba(0,0,0,.6), 0 3px 14px rgba(0,0,0,.5); }
    /* 앵커 자체는 자리를 차지하지 않게 숨긴다. */
    [data-testid="stElementContainer"]:has(.db-head-anchor),
    [data-testid="stElementContainer"]:has(.db-anchor) { display: none; }

    /* 탭 (어두운 카드 위에서 읽히도록 색을 직접 지정) */
    [data-testid="stTab"],
    [data-testid="stTab"] [data-testid="stMarkdownContainer"] { color: #b9c6da !important; font-weight: 700; }
    [data-testid="stTab"]:hover,
    [data-testid="stTab"]:hover [data-testid="stMarkdownContainer"] { color: #e6edf8 !important; }
    [data-testid="stTab"][aria-selected="true"],
    [data-testid="stTab"][aria-selected="true"] [data-testid="stMarkdownContainer"] { color: #ffffff !important; }
    /* 선택된 탭 밑줄을 대시보드 색으로 */
    [data-testid="stTabs"] .react-aria-SelectionIndicator { background-color: #F0912D !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ===================
# 분석 대시보드
# ===================


@st.cache_data
def load_questions() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


@st.cache_data
def load_figure_data(file_name: str) -> pd.DataFrame:
    path = FIGURE_DATA_DIR / file_name
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def card_heading(title: str, subtitle: str = "") -> None:
    """탭 안에 들어가는 제목/부제. 카드 배경은 바깥 컨테이너의 .db-anchor 가 담당한다."""
    st.markdown(
        f'<div class="db-title">{title}</div>'
        + (f'<div class="db-sub">{subtitle}</div>' if subtitle else ""),
        unsafe_allow_html=True,
    )


def shorten(text: str, limit: int = 20) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def base_layout(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=30, t=30, b=45),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e6edf8", size=12),
        showlegend=False,
        bargap=0.35,
    )
    fig.update_xaxes(
        gridcolor="rgba(255,255,255,.16)", zerolinecolor="rgba(255,255,255,.30)",
        tickfont=dict(color="#e6edf8"), title_font=dict(color="#e6edf8"),
    )
    fig.update_yaxes(
        gridcolor="rgba(255,255,255,.08)", automargin=True,
        tickfont=dict(color="#e6edf8"), title_font=dict(color="#e6edf8"),
    )
    return fig


def chart_top10_comparison(overall: pd.DataFrame, target: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=1, cols=2, horizontal_spacing=0.14,
        subplot_titles=("전체 질문 조회수 TOP 10", "신규·복귀 질문 조회수 TOP 10"),
    )
    for column, (frame, color) in enumerate(((overall, ORANGE), (target, RED)), start=1):
        labels = [f"[{row.category}] {shorten(row.title)}" for row in frame.itertuples()]
        fig.add_trace(
            go.Bar(
                x=frame["views"], y=labels, orientation="h", marker_color=color,
                text=[f"{value:,}" for value in frame["views"]],
                textposition="outside", textfont=dict(size=11, color="#e6edf8"),
                hovertemplate="%{y}<br>조회수 %{x:,}<extra></extra>",
            ),
            row=1, col=column,
        )
        fig.update_xaxes(
            title_text="조회수", range=[0, float(frame["views"].max()) * 1.22],
            row=1, col=column,
        )
    fig.update_traces(cliponaxis=False)
    base_layout(fig, 470)
    fig.update_layout(margin=dict(l=10, r=24, t=40, b=45))
    for annotation in fig.layout.annotations:
        annotation.font.update(size=14, color="#ffffff")
    return fig


def chart_keyword_top15(keywords: pd.DataFrame) -> go.Figure:
    frame = keywords.sort_values("document_rate")
    fig = go.Figure(
        go.Bar(
            x=frame["document_rate"], y=frame["word"], orientation="h", marker_color=ORANGE,
            text=[
                f"{rate:.1f}%  ({count:,}건)"
                for rate, count in zip(frame["document_rate"], frame["document_count"])
            ],
            textposition="outside", textfont=dict(size=11, color="#e6edf8"),
            hovertemplate="%{y}<br>%{x:.1f}%<extra></extra>",
        )
    )
    base_layout(fig, 560)
    fig.update_traces(cliponaxis=False)
    fig.update_xaxes(title_text="해당 키워드가 등장한 게시글 비율 (%)", range=[0, frame["document_rate"].max() * 1.35])
    return fig


def chart_group_comparison(comparison: pd.DataFrame) -> go.Figure:
    frame = comparison.sort_values("target_rate")
    fig = go.Figure()
    for name, column, color in (
        ("신규·복귀 표현 미포함", "general_rate", YELLOW),
        ("신규·복귀 질문", "target_rate", RED),
    ):
        fig.add_trace(
            go.Bar(
                x=frame[column], y=frame["word"], orientation="h", name=name, marker_color=color,
                text=[f"{value:.1f}%" for value in frame[column]],
                textposition="outside", textfont=dict(size=10.5, color="#e6edf8"),
                hovertemplate="%{y}<br>" + name + " %{x:.1f}%<extra></extra>",
            )
        )
    base_layout(fig, 620)
    fig.update_traces(cliponaxis=False)
    fig.update_layout(
        barmode="group", bargap=0.3, bargroupgap=0.05, showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11, color="#e6edf8")),
        margin=dict(l=10, r=30, t=20, b=70),
    )
    fig.update_xaxes(title_text="해당 키워드가 등장한 게시글 비율 (%)", range=[0, frame["target_rate"].max() * 1.28])
    return fig


def chart_keyword_umap(points: pd.DataFrame) -> go.Figure:
    """카테고리별 핵심 키워드를 임베딩 공간(UMAP 2차원)에 뿌린 산점도."""
    rate_min = float(points["document_rate"].min())
    rate_max = float(points["document_rate"].max())
    rate_span = max(rate_max - rate_min, 1e-9)

    fig = go.Figure()
    categories = sorted(points["category"].unique())
    for order, category in enumerate(categories):
        frame = points[points["category"] == category]
        color = CATEGORY_COLORS.get(category, FALLBACK_COLORS[order % len(FALLBACK_COLORS)])
        fig.add_trace(
            go.Scatter(
                x=frame["umap_x"], y=frame["umap_y"], mode="markers+text",
                name=category, text=frame["word"], textposition="top center",
                textfont=dict(size=12, color="#e6edf8"),
                marker=dict(
                    size=[16 + (rate - rate_min) / rate_span * 16 for rate in frame["document_rate"]],
                    color=color, line=dict(width=1.4, color="rgba(255,255,255,.9)"), opacity=0.9,
                ),
                customdata=frame[["word", "document_count", "document_rate", "rank"]].to_numpy(),
                hovertemplate=(
                    "<b>%{customdata[0]}</b> · " + category + " %{customdata[3]}위"
                    "<br>등장 게시글 %{customdata[1]:,}건 (%{customdata[2]:.1f}%)<extra></extra>"
                ),
            )
        )

    base_layout(fig, 560)
    fig.update_traces(cliponaxis=False)
    fig.update_layout(
        showlegend=True,
        legend=dict(
            title_text="카테고리", orientation="v", yanchor="top", y=1, xanchor="left", x=1.01,
            bgcolor="rgba(11,18,34,.55)", bordercolor="rgba(255,255,255,.18)", borderwidth=1,
            font=dict(size=11.5, color="#e6edf8"),
        ),
        margin=dict(l=10, r=120, t=30, b=50),
    )
    fig.update_xaxes(title_text="UMAP 1")
    fig.update_yaxes(title_text="UMAP 2", gridcolor="rgba(255,255,255,.16)")
    return fig


# WORD_CLOUD_SCALE = 0.6  # 캔버스를 꽉 채웠을 때 대비 글자 크기 배율


# # 홈 화면 "조회" 버튼 색(#FA7000) = hsl(27, 100%, 49%)
# CLOUD_HUE, CLOUD_SATURATION = 27, 100
# CLOUD_LIGHTNESS = (42, 88)  # 작은 단어는 버튼 색보다 진하게, 큰 단어일수록 밝게


# def make_cloud_color(max_font_size: int):
    # """빈도가 높은 단어일수록 밝게 — 어두운 카드 위에서 대비를 유지한다."""
    # low, high = CLOUD_LIGHTNESS

    # def cloud_color(word, font_size, position, orientation, random_state=None, **kwargs) -> str:
        # ratio = min(max(font_size / max_font_size, 0.0), 1.0)
        # return f"hsl({CLOUD_HUE}, {CLOUD_SATURATION}%, {int(low + ratio * (high - low))}%)"

    # return cloud_color


# @st.cache_data(show_spinner=False)
# def word_cloud_png(items: tuple[tuple[str, int], ...]) -> bytes:
    # """단어-빈도 쌍으로 배경이 투명한 워드클라우드 PNG를 만든다."""
    # frequencies = dict(items)
    # settings = dict(
        # font_path=str(WORDCLOUD_FONT),
        # width=1280, height=520,
        # mode="RGBA", background_color=None,
        # max_words=30, prefer_horizontal=0.85,
        # relative_scaling=0.42, collocations=False,
        # random_state=42,
    # )

    # # WordCloud 는 캔버스를 꽉 채우도록 글자를 키우므로, 한 번 그려 본 뒤
    # # 가장 큰 글자 크기의 WORD_CLOUD_SCALE 배로 상한을 걸어 다시 그린다.
    # probe = WordCloud(min_font_size=10, **settings).generate_from_frequencies(frequencies)
    # largest = max(entry[1] for entry in probe.layout_)
    # max_font_size = max(int(largest * WORD_CLOUD_SCALE), 12)

    # cloud = WordCloud(
        # max_font_size=max_font_size,
        # min_font_size=max(int(10 * WORD_CLOUD_SCALE), 4),
        # color_func=make_cloud_color(max_font_size),
        # **settings,
    # ).generate_from_frequencies(frequencies)

    # buffer = io.BytesIO()
    # cloud.to_image().save(buffer, format="PNG")
    # return buffer.getvalue()


PLOTLY_CONFIG = {"displayModeBar": False}

df = load_questions()

# 제목 + 지표를 반투명 다크 패널로 감싼다.
with st.container():
    st.markdown('<span class="db-head-anchor"></span>', unsafe_allow_html=True)
    st.title("🍁 메이플스토리 유저 질문 분석")
    c1, c2 = st.columns(2)
    c1.metric("질문 수", f"{len(df)}개")
    c2.metric("카테고리 수", f"{df['category'].nunique()}개")

overall_top10 = load_figure_data("overall_top10.csv")
target_top10 = load_figure_data("target_top10.csv")
keyword_top15 = load_figure_data("overall_keyword_top15.csv")
group_comparison = load_figure_data("keyword_group_comparison.csv")
keyword_umap = load_figure_data("category_keyword_umap.csv")
# word_counts = load_figure_data("category_word_counts.csv")

EMPTY_MESSAGE = f"시각화 데이터를 찾지 못했습니다: {FIGURE_DATA_DIR}"

with st.container():
    st.markdown('<span class="db-anchor"></span>', unsafe_allow_html=True)
    # tab_views, tab_keywords, tab_groups, tab_umap, tab_cloud = st.tabs(
        # ["조회수 TOP 10", "키워드 TOP 15", "신규·복귀 비교", "임베딩 지도", "워드클라우드"]
    # )
    tab_views, tab_keywords, tab_groups, tab_umap = st.tabs(
        ["조회수 TOP 10", "키워드 TOP 15", "신규·복귀 비교", "임베딩 지도"]
    )

    # 1. 전체 / 신규·복귀 조회수 TOP 10
    with tab_views:
        if overall_top10.empty or target_top10.empty:
            st.info(EMPTY_MESSAGE)
        else:
            card_heading(
                "전체 이용자와 신규·복귀 이용자의 주요 관심 질문",
                "각 패널은 독립적인 조회수 축을 사용합니다.",
            )
            st.plotly_chart(
                chart_top10_comparison(overall_top10, target_top10),
                use_container_width=True, theme=None, config=PLOTLY_CONFIG,
            )

    # 2. 전체 질문 키워드 TOP 15
    with tab_keywords:
        if keyword_top15.empty:
            st.info(EMPTY_MESSAGE)
        else:
            total_questions = round(
                keyword_top15["document_count"].iloc[0] / keyword_top15["document_rate"].iloc[0] * 100
            )
            card_heading(
                "전체 질문의 주요 관심 키워드 TOP 15",
                f"전체 {total_questions:,}개 질문 기준 · 동일 게시글 내 같은 단어는 1회만 집계",
            )
            st.plotly_chart(chart_keyword_top15(keyword_top15), use_container_width=True, theme=None, config=PLOTLY_CONFIG)

    # 3. 신규·복귀 표현 포함 여부 비교
    with tab_groups:
        if group_comparison.empty:
            st.info(EMPTY_MESSAGE)
        else:
            general_total = round(
                group_comparison["general_count"].iloc[0] / group_comparison["general_rate"].iloc[0] * 100
            )
            target_total = round(
                group_comparison["target_count"].iloc[0] / group_comparison["target_rate"].iloc[0] * 100
            )
            card_heading(
                "신규·복귀 표현 포함 여부에 따른 주요 키워드 비교",
                f"미포함 질문 {general_total:,}개 · 신규·복귀 질문 {target_total:,}개 · "
                "집단 크기 차이를 고려해 게시글 비율로 비교",
            )
            st.plotly_chart(chart_group_comparison(group_comparison), use_container_width=True, theme=None, config=PLOTLY_CONFIG)

    # 4. 카테고리별 핵심 키워드 임베딩 지도
    with tab_umap:
        if keyword_umap.empty:
            st.info(EMPTY_MESSAGE)
        else:
            card_heading(
                "카테고리별 핵심 키워드 TOP 5 임베딩 지도",
                "각 키워드가 실제로 쓰인 게시글의 임베딩 평균을 UMAP으로 2차원 축소 · "
                "같은 색은 같은 카테고리이며 가까울수록 문맥이 비슷한 키워드",
            )
            st.plotly_chart(chart_keyword_umap(keyword_umap), use_container_width=True, theme=None, config=PLOTLY_CONFIG)

    # # 5. 카테고리별 워드클라우드 — 카테고리 탭으로 한 번에 하나씩 보여준다.
    # with tab_cloud:
        # if word_counts.empty:
            # st.info(EMPTY_MESSAGE)
        # else:
            # card_heading(
                # "카테고리별 질문 키워드 워드클라우드",
                # "카테고리마다 상위 30개 단어 · 글자가 클수록 해당 카테고리에서 자주 등장한 단어",
            # )
            # categories = list(dict.fromkeys(word_counts["category"]))
            # for category, category_tab in zip(categories, st.tabs(categories)):
                # with category_tab:
                    # frame = word_counts[word_counts["category"] == category]
                    # items = tuple(zip(frame["word"], frame["count"].astype(int)))
                    # st.image(word_cloud_png(items), use_container_width=True)
