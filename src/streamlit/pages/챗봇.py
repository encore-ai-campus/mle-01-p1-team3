"""메이플스토리 가이드 챗봇.

notebooks/rag_chain_retriever.ipynb 의 retriever 기반 RAG 체인을 그대로 옮긴 페이지.
질문 분류 -> source별 retriever -> context 구성 -> prompt -> answer
"""

from __future__ import annotations

import os
import sys
from html import escape
from pathlib import Path
from typing import Any

os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import streamlit as st

PAGE_DIR = Path(__file__).resolve().parent
STREAMLIT_DIR = PAGE_DIR.parent
PROJECT_ROOT = STREAMLIT_DIR.parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

PERSIST_DIRECTORY = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "maplestory_guides"
EMBEDDING_MODEL = "jhgan/ko-sroberta-multitask"
CHAT_MODEL = "gpt-4o-mini"

ROUTE_LABELS = {
    "jobs": "직업",
    "items": "아이템",
    "guide": "가이드",
    "mixed": "통합",
}

WELCOME = "메이플스토리에 대해 궁금한 점을 물어보세요. 가이드 문서를 찾아 정리해 드립니다."

EXAMPLE_QUESTIONS = [
    "메이플스토리 뉴비에게 추천하는 직업은 무엇인가요?",
    "잠재능력 큐브는 어떤 순서로 돌려야 하나요?",
    "레벨 200 이후에 뭘 해야 하나요?",
]


st.markdown(
    """
    <style>
    .block-container { max-width: 1500px; padding-top: 1.5rem; }
    /* 히어로 + 질문 예시를 함께 감싸는 패널 */
    div[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .hero-anchor) {
        background: rgba(23,30,52,.62); backdrop-filter: blur(7px);
        border: 1px solid rgba(255,255,255,.16); border-radius: 18px;
        padding: 18px 20px; margin-bottom: 14px; }
    .chat-hero { margin-bottom: 2px; }
    .chat-hero h2 { color: #ffd45c; font-size: 21px; font-weight: 800; margin: 0 0 4px; }
    .chat-hero p { color: rgba(255,255,255,.72); font-size: 13.5px; margin: 0; }
    .chat-hint { color: rgba(255,255,255,.6); font-size: 12.5px; font-weight: 600; margin: 10px 0 2px; }
    [class*="st-key-example_"] { margin-top: 16px; }
    [data-testid="stChatMessage"] { background: rgba(255,255,255,.82); backdrop-filter: blur(5px);
        border: 1px solid rgba(255,255,255,.6); border-radius: 14px; padding-right: 26px; }
    [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li { color: #29324a; }
    .src-line { color: #46506b; font-size: 12.5px; line-height: 1.7; margin-bottom: 6px; }
    .src-line b { color: #1f2740; }
    .src-line a, .src-chip a { color: #2f5fbf; text-decoration: none; }
    .src-line a:hover, .src-chip a:hover { text-decoration: underline; }
    .src-links { margin-top: 2px; margin-bottom: 18px; }
    .src-links .label { color: #55607a; font-size: 12px; font-weight: 700; margin-right: 4px; }
    .src-chip { display: inline-block; background: rgba(41,50,74,.07); border: 1px solid rgba(41,50,74,.16);
        border-radius: 999px; padding: 3px 11px; margin: 3px 5px 0 0; font-size: 12px; max-width: 100%;
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: middle; }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_openai_api_key() -> str | None:
    """실행 위치와 무관하게 OPENAI_API_KEY를 찾는다."""
    try:
        key = st.secrets.get("OPENAI_API_KEY")
    except Exception:
        key = None
    if key:
        return key
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    try:
        from dotenv import dotenv_values
    except ImportError:
        return None
    for env_path in (PROJECT_ROOT / ".env", STREAMLIT_DIR / ".env"):
        if env_path.is_file():
            key = dotenv_values(env_path).get("OPENAI_API_KEY")
            if key:
                return key
    return None


@st.cache_resource(show_spinner=False)
def get_vectorstore():
    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings

    embedding_function = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    return Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=str(PERSIST_DIRECTORY),
        embedding_function=embedding_function,
    )


@st.cache_resource(show_spinner=False)
def get_chat_model(api_key: str):
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=CHAT_MODEL, temperature=0, timeout=60, api_key=api_key)


@st.cache_resource(show_spinner=False)
def get_prompt():
    from langchain_core.prompts import ChatPromptTemplate

    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "당신은 메이플스토리 정보를 안내하는 도우미입니다. "
                    "반드시 제공된 context에 근거해서만 답변하세요. "
                    "답변은 먼저 핵심 결론을 2~4문장으로 간결하게 설명하고, "
                    "이어서 근거가 될 만한 정보를 목록으로 짧게 정리하세요. "
                    "추천 질문이면 각 항목을 분리해 설명하고, "
                    "context가 부족하면 부족한 이유를 정확히 말하세요."
                ),
            ),
            ("human", "[Context]\n{context}\n\n[Question]\n{question}"),
        ]
    )


def retrieve_documents(question: str) -> tuple[str, dict[str, Any], list[Any]]:
    """질문을 분류해 source별 retriever로 문서를 가져온다."""
    from rag_chain_utils import classify_question, make_search_kwargs

    route = classify_question(question)
    search_kwargs = make_search_kwargs(route)
    retriever = get_vectorstore().as_retriever(
        search_type="similarity",
        search_kwargs=search_kwargs,
    )
    return route, search_kwargs, retriever.invoke(question)


def _doc_meta(doc: Any) -> tuple[str, str, str, str]:
    metadata = getattr(doc, "metadata", {}) or {}
    title = str(metadata.get("name") or metadata.get("title") or "문서")
    section = str(metadata.get("section_title") or "")
    url = str(metadata.get("url") or "")
    source = str(metadata.get("source") or "-")
    return title, section, url, source


def source_lines(docs: list[Any]) -> str:
    """익스팬더에 들어갈 문서 목록(제목 링크 + 미리보기)."""
    lines = []
    for index, doc in enumerate(docs, start=1):
        title, section, url, source = _doc_meta(doc)
        heading = (
            f'<a href="{escape(url)}" target="_blank" rel="noopener">{escape(title)}</a>'
            if url
            else escape(title)
        )
        preview = " ".join((getattr(doc, "page_content", "") or "").split())
        lines.append(
            f'<div class="src-line"><b>[{index}] {heading}</b> · {escape(source)}'
            + (f" · {escape(section)}" if section else "")
            + f"<br>{escape(preview[:160])}…</div>"
        )
    return "".join(lines) or '<div class="src-line">검색된 문서가 없습니다.</div>'


def source_links(docs: list[Any], limit: int = 6) -> str:
    """답변 바로 아래에 보여 줄 원문 링크 칩(중복 URL 제거)."""
    chips = []
    seen: set[str] = set()
    for doc in docs:
        title, _, url, _ = _doc_meta(doc)
        if not url or url in seen:
            continue
        seen.add(url)
        chips.append(
            f'<span class="src-chip">🔗 <a href="{escape(url)}" target="_blank" '
            f'rel="noopener">{escape(title)}</a></span>'
        )
        if len(chips) >= limit:
            break
    if not chips:
        return ""
    return '<div class="src-links"><span class="label">참고 문서</span>' + "".join(chips) + "</div>"


def answer_question(question: str, api_key: str):
    """RAG 체인을 실행해 (스트림, route, 문서)를 돌려준다."""
    from rag_chain_utils import build_context

    route, _, docs = retrieve_documents(question)
    chain = get_prompt() | get_chat_model(api_key)
    stream = chain.stream({"context": build_context(docs), "question": question})
    return stream, route, docs


# ===================
# 화면
# ===================
hero = st.container()

if not PERSIST_DIRECTORY.is_dir():
    st.error(f"벡터스토어를 찾지 못했습니다: {PERSIST_DIRECTORY}")
    st.stop()

api_key = get_openai_api_key()
if not api_key:
    st.error("OPENAI_API_KEY가 설정되지 않았습니다. 프로젝트 루트의 .env 파일을 확인해 주세요.")
    st.stop()

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

with st.sidebar:
    st.markdown("#### 💬 챗봇")
    if st.button("대화 새로 시작", width="stretch"):
        st.session_state.chat_messages = []
        st.rerun()

with hero:
    st.markdown(
        f'<div class="chat-hero hero-anchor"><h2>🍄 메이플스토리 가이드 챗봇</h2>'
        f"<p>{WELCOME}</p></div>",
        unsafe_allow_html=True,
    )
    if not st.session_state.chat_messages:
        example_cols = st.columns(len(EXAMPLE_QUESTIONS))
        for column, example in zip(example_cols, EXAMPLE_QUESTIONS):
            with column:
                if st.button(example, key=f"example_{example}", width="stretch"):
                    st.session_state.pending_question = example
                    st.rerun()

for message in st.session_state.chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("links"):
            st.markdown(message["links"], unsafe_allow_html=True)
        if message.get("sources"):
            with st.expander(f"참고한 문서 {message['doc_count']}건 · {message['route']}"):
                st.markdown(message["sources"], unsafe_allow_html=True)

question = st.chat_input("궁금한 점을 입력하세요") or st.session_state.pop("pending_question", None)

if question:
    st.session_state.chat_messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("가이드 문서를 찾는 중입니다... (첫 질문은 모델 로딩으로 조금 걸릴 수 있어요)"):
                stream, route, docs = answer_question(question, api_key)
            answer = st.write_stream(chunk.content for chunk in stream)
        except Exception as error:  # noqa: BLE001 - 사용자에게 원인을 그대로 보여준다
            st.error(f"답변을 생성하지 못했습니다: {error}")
        else:
            sources = source_lines(docs)
            links = source_links(docs)
            route_label = ROUTE_LABELS.get(route, route)
            if links:
                st.markdown(links, unsafe_allow_html=True)
            with st.expander(f"참고한 문서 {len(docs)}건 · {route_label}"):
                st.markdown(sources, unsafe_allow_html=True)
            st.session_state.chat_messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "links": links,
                    "doc_count": len(docs),
                    "route": route_label,
                }
            )
