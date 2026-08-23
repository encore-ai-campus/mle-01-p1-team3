import os
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_PATH = PROJECT_ROOT / "data" / "processed" / "inven_question_final.csv"
FIGURE_DATA_DIR = PROJECT_ROOT / "인벤데이터 시각화" / "outputs"

ORANGE = "#F0912D"
RED = "#E7503C"
YELLOW = "#F5B942"
TITLE_COLOR = "#8B2E1F"


st.markdown(
    """
    <style>
    .block-container { max-width: 1500px; }
    /* 제목 + 그래프를 감싼 반투명 흰 카드 */
    div[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .db-anchor) {
        background: rgba(255,255,255,.55); backdrop-filter: blur(5px);
        border: 1px solid rgba(255,255,255,.65); border-radius: 16px;
        padding: 16px 18px 10px; margin-bottom: 18px; box-shadow: 0 10px 28px rgba(20,30,60,.18); }
    .db-title { color: #8B2E1F; font-size: 19px; font-weight: 800; }
    .db-sub { color: #6b7280; font-size: 12.5px; font-weight: 600; margin: 2px 0 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ===================
# 분석 대시보드
# ===================
st.title("메이플스토리 유저 질문 분석")


@st.cache_data
def load_questions() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


@st.cache_data
def load_figure_data(file_name: str) -> pd.DataFrame:
    path = FIGURE_DATA_DIR / file_name
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def card_open(title: str, subtitle: str = "") -> None:
    """카드 배경(CSS)이 붙도록 앵커 클래스를 함께 넣는다."""
    st.markdown(
        f'<div class="db-title db-anchor">{title}</div>'
        + (f'<div class="db-sub">{subtitle}</div>' if subtitle else ""),
        unsafe_allow_html=True,
    )


def shorten(text: str, limit: int = 22) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def base_layout(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=30, t=30, b=45),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#5b6472", size=12),
        showlegend=False,
        bargap=0.35,
    )
    fig.update_xaxes(
        gridcolor="rgba(20,30,60,.12)", zerolinecolor="rgba(20,30,60,.25)",
        tickfont=dict(color="#5b6472"), title_font=dict(color="#5b6472"),
    )
    fig.update_yaxes(
        gridcolor="rgba(20,30,60,.06)", automargin=True,
        tickfont=dict(color="#5b6472"), title_font=dict(color="#5b6472"),
    )
    return fig


def chart_top10_comparison(overall: pd.DataFrame, target: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=1, cols=2, horizontal_spacing=0.06,
        subplot_titles=("전체 질문 조회수 TOP 10", "신규·복귀 질문 조회수 TOP 10"),
    )
    for column, (frame, color) in enumerate(((overall, ORANGE), (target, RED)), start=1):
        labels = [f"[{row.category}] {shorten(row.title)}" for row in frame.itertuples()]
        fig.add_trace(
            go.Bar(
                x=frame["views"], y=labels, orientation="h", marker_color=color,
                text=[f"{value:,}" for value in frame["views"]],
                textposition="outside", textfont=dict(size=11, color="#5b6472"),
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
        annotation.font.update(size=14, color="#8B2E1F")
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
            textposition="outside", textfont=dict(size=11, color="#5b6472"),
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
                textposition="outside", textfont=dict(size=10.5, color="#5b6472"),
                hovertemplate="%{y}<br>" + name + " %{x:.1f}%<extra></extra>",
            )
        )
    base_layout(fig, 620)
    fig.update_traces(cliponaxis=False)
    fig.update_layout(
        barmode="group", bargap=0.3, bargroupgap=0.05, showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11, color="#5b6472")),
        margin=dict(l=10, r=30, t=20, b=70),
    )
    fig.update_xaxes(title_text="해당 키워드가 등장한 게시글 비율 (%)", range=[0, frame["target_rate"].max() * 1.28])
    return fig


PLOTLY_CONFIG = {"displayModeBar": False}

df = load_questions()

# 지표
c1, c2 = st.columns(2)
c1.metric("질문 수", f"{len(df)}개")
c2.metric("카테고리 수", f"{df['category'].nunique()}개")

st.divider()

overall_top10 = load_figure_data("overall_top10.csv")
target_top10 = load_figure_data("target_top10.csv")
keyword_top15 = load_figure_data("overall_keyword_top15.csv")
group_comparison = load_figure_data("keyword_group_comparison.csv")

# 1. 전체 / 신규·복귀 조회수 TOP 10
if not overall_top10.empty and not target_top10.empty:
    with st.container():
        card_open("전체 이용자와 신규·복귀 이용자의 주요 관심 질문", "각 패널은 독립적인 조회수 축을 사용합니다.")
        st.plotly_chart(
            chart_top10_comparison(overall_top10, target_top10),
            use_container_width=True, theme=None, config=PLOTLY_CONFIG,
        )

# 2. 전체 질문 키워드 TOP 15
if not keyword_top15.empty:
    total_questions = round(
        keyword_top15["document_count"].iloc[0] / keyword_top15["document_rate"].iloc[0] * 100
    )
    with st.container():
        card_open(
            "전체 질문의 주요 관심 키워드 TOP 15",
            f"전체 {total_questions:,}개 질문 기준 · 동일 게시글 내 같은 단어는 1회만 집계",
        )
        st.plotly_chart(chart_keyword_top15(keyword_top15), use_container_width=True, theme=None, config=PLOTLY_CONFIG)

# 3. 신규·복귀 표현 포함 여부 비교
if not group_comparison.empty:
    general_total = round(
        group_comparison["general_count"].iloc[0] / group_comparison["general_rate"].iloc[0] * 100
    )
    target_total = round(
        group_comparison["target_count"].iloc[0] / group_comparison["target_rate"].iloc[0] * 100
    )
    with st.container():
        card_open(
            "신규·복귀 표현 포함 여부에 따른 주요 키워드 비교",
            f"미포함 질문 {general_total:,}개 · 신규·복귀 질문 {target_total:,}개 · "
            "집단 크기 차이를 고려해 게시글 비율로 비교",
        )
        st.plotly_chart(chart_group_comparison(group_comparison), use_container_width=True, theme=None, config=PLOTLY_CONFIG)

if overall_top10.empty and keyword_top15.empty and group_comparison.empty:
    st.info(f"시각화 데이터를 찾지 못했습니다: {FIGURE_DATA_DIR}")
