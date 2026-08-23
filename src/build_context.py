"""
Retriever 결과를 LLM 프롬프트에 넣을 context 문자열로 변환합니다.

사용 예:
    from retrieve import retrieve
    from build_context import build_context

    context = build_context(retrieve("표창을 사용하는 직업", k=5))
"""

NO_RESULT_MESSAGE = "관련 검색 결과가 없습니다."

SEPARATOR = "\n\n---\n\n"


def _format_document(index, document):
    """검색 결과 한 건을 context 블록 문자열로 만듭니다."""
    metadata = document.get("metadata") or {}

    source = metadata.get("source", "unknown")
    title = metadata.get("title") or metadata.get("name") or "제목 없음"
    chunk_id = document.get("id", "")
    url = metadata.get("url", "")
    page_content = document.get("page_content", "")

    return f"""
[검색 결과 {index}]
문서 유형: {source}
문서 제목: {title}
chunk_id: {chunk_id}

내용:
{page_content}

출처 URL:
{url}
""".strip()


def build_context(documents):
    """
    Retriever 결과(list[dict])를 LLM에 전달할 context 문자열로 변환합니다.

    documents: retrieve()가 돌려주는 리스트. 각 항목은
        {"id", "page_content", "metadata", "rank", "score", "distance"} 형태.

    검색 결과가 없으면 NO_RESULT_MESSAGE를 돌려줍니다. 빈 문자열을 돌려주면
    프롬프트의 [Context] 항목이 통째로 비어 LLM이 자유롭게 지어내기 쉬워집니다.
    """
    if not documents:
        return NO_RESULT_MESSAGE

    context_parts = [
        _format_document(index, document)
        for index, document in enumerate(documents, start=1)
    ]

    return SEPARATOR.join(context_parts)


def has_brace(text):
    """
    context에 중괄호가 있는지 확인합니다.

    ChatPromptTemplate은 중괄호를 템플릿 변수로 해석하므로,
    context에 중괄호가 섞이면 format 단계에서 KeyError가 납니다.
    """
    return "{" in text or "}" in text
