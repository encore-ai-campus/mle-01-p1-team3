from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import streamlit as st


# ============================================================
# 1. 기존 NEXON API Client import
# ============================================================
#
# app.py가 api_streamlit_test 폴더에 있고,
# nexon_client.py가 api_streamlit_test/services 폴더에 있다는 전제입니다.
#
# api_streamlit_test/
# ├── app.py
# └── services/
#     └── nexon_client.py
# ============================================================

APP_DIR = Path(__file__).resolve().parent

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


try:
    from services.nexon_client import (
        NexonApiError,
        NexonClient,
    )

except ModuleNotFoundError:
    st.error(
        "services/nexon_client.py 파일을 찾지 못했습니다. "
        "현재 nexon_client.ipynb의 API 클래스 코드를 "
        "services/nexon_client.py로 복사해 주세요."
    )
    st.stop()


# ============================================================
# 2. Streamlit 기본 설정
# ============================================================

st.set_page_config(
    page_title="메이플 캐릭터 맞춤 가이드",
    page_icon="🍁",
    layout="wide",
)


# ============================================================
# 3. 간단한 화면 스타일
# ============================================================

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }

        .page-description {
            opacity: 0.72;
            margin-top: -0.6rem;
            margin-bottom: 1.5rem;
        }

        .section-description {
            opacity: 0.65;
            margin-top: -0.5rem;
            margin-bottom: 1rem;
        }

        div[data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.22);
            border-radius: 14px;
            padding: 0.85rem 1rem;
            background: rgba(100, 116, 139, 0.06);
        }

        .active-badge {
            display: inline-block;
            padding: 0.3rem 0.65rem;
            border-radius: 999px;
            font-size: 0.88rem;
            font-weight: 700;
            background: rgba(34, 197, 94, 0.14);
            border: 1px solid rgba(34, 197, 94, 0.35);
        }

        .inactive-badge {
            display: inline-block;
            padding: 0.3rem 0.65rem;
            border-radius: 999px;
            font-size: 0.88rem;
            font-weight: 700;
            background: rgba(148, 163, 184, 0.14);
            border: 1px solid rgba(148, 163, 184, 0.35);
        }

        .rag-box {
            border: 1px solid rgba(59, 130, 246, 0.30);
            border-radius: 16px;
            padding: 1.2rem 1.3rem;
            margin-top: 1rem;
            margin-bottom: 1rem;
            background: linear-gradient(
                135deg,
                rgba(59, 130, 246, 0.08),
                rgba(16, 185, 129, 0.07)
            );
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 4. 화면 출력용 보조 함수
# ============================================================

def safe_text(
    value: Any,
    default: str = "-",
) -> str:
    """
    None 또는 빈 문자열을 화면에 그대로 출력하지 않고
    기본값으로 변환합니다.
    """

    if value is None:
        return default

    text = str(value).strip()

    return text if text else default


def to_int(
    value: Any,
    default: int = 0,
) -> int:
    """
    API에서 문자열로 반환된 숫자를 int로 변환합니다.

    예:
        "150" -> 150
        None  -> 0
    """

    try:
        return int(float(str(value).replace(",", "")))

    except (TypeError, ValueError):
        return default


def format_number(
    value: Any,
    default: str = "-",
) -> str:
    """
    정수 형태의 값에 천 단위 쉼표를 붙입니다.

    예:
        "115609628" -> "115,609,628"
    """

    if value is None:
        return default

    text = str(value).strip()

    if not text:
        return default

    compact = text.replace(",", "")

    if compact.lstrip("-").isdigit():
        return f"{int(compact):,}"

    return text


def format_percent(
    value: Any,
) -> str:
    """
    퍼센트 값에 %가 없다면 붙여서 출력합니다.
    """

    text = safe_text(value)

    if text == "-":
        return text

    if text.endswith("%"):
        return text

    return f"{text}%"


def parse_access_flag(
    value: Any,
) -> bool:
    """
    NEXON API의 access_flag는 문자열 true/false일 수 있으므로
    Python bool 값으로 변환합니다.
    """

    return str(value).strip().lower() == "true"


def build_stat_map(
    stat_data: dict[str, Any] | None,
) -> dict[str, str]:
    """
    final_stat 배열을 사용하기 쉬운 dict 형태로 변환합니다.

    기존 구조:
        [
            {
                "stat_name": "전투력",
                "stat_value": "123456"
            }
        ]

    변환 결과:
        {
            "전투력": "123456"
        }
    """

    if not stat_data:
        return {}

    final_stat = stat_data.get(
        "final_stat",
        [],
    )

    if not isinstance(final_stat, list):
        return {}

    result: dict[str, str] = {}

    for row in final_stat:

        if not isinstance(row, dict):
            continue

        stat_name = row.get("stat_name")
        stat_value = row.get("stat_value")

        if stat_name is None:
            continue

        result[str(stat_name)] = safe_text(
            stat_value
        )

    return result


def find_stat(
    stat_map: dict[str, str],
    aliases: tuple[str, ...],
) -> str:
    """
    같은 능력치가 다른 이름으로 반환될 가능성에 대비해
    여러 이름 중 먼저 발견되는 값을 반환합니다.
    """

    for stat_name in aliases:

        if stat_name in stat_map:
            return stat_map[stat_name]

    return "-"


def calculate_symbol_progress(
    symbol: dict[str, Any],
) -> float:
    """
    심볼 성장 진행률을 0~1 사이 실수로 반환합니다.
    """

    current_growth = to_int(
        symbol.get(
            "symbol_growth_count"
        )
    )

    required_growth = to_int(
        symbol.get(
            "symbol_require_growth_count"
        )
    )

    if required_growth <= 0:
        return 0.0

    return min(
        current_growth / required_growth,
        1.0,
    )


def get_level_band(
    level: int,
) -> str:
    """
    이후 RAG 검색 필터에 사용할 레벨 구간입니다.
    """

    if level < 200:
        return "200 미만"

    if level < 220:
        return "200-219"

    if level < 240:
        return "220-239"

    if level < 260:
        return "240-259"

    if level < 280:
        return "260-279"

    if level < 300:
        return "280-299"

    return "300 이상"


def get_union_band(
    union_level: int,
) -> str:
    """
    이후 RAG 검색 필터에 사용할 유니온 구간입니다.
    """

    if union_level < 2000:
        return "0-1999"

    if union_level < 4000:
        return "2000-3999"

    if union_level < 6000:
        return "4000-5999"

    if union_level < 8000:
        return "6000-7999"

    return "8000 이상"


# ============================================================
# 5. API Key 가져오기
# ============================================================

def get_api_key() -> str:
    """
    API Key 조회 순서

    1. .streamlit/secrets.toml
    2. 환경변수 NEXON_API_KEY
    3. Streamlit 사이드바 비밀번호 입력
    """

    api_key: Any = None

    try:
        api_key = st.secrets.get(
            "NEXON_API_KEY"
        )

    except Exception:
        api_key = None

    if not api_key:
        api_key = os.getenv(
            "NEXON_API_KEY"
        )

    if not api_key:
        api_key = st.sidebar.text_input(
            "NEXON Open API Key",
            type="password",
            help=(
                "로컬 테스트용 입력입니다. "
                "정식 구현에서는 .streamlit/secrets.toml을 사용하세요."
            ),
        )

    if not isinstance(api_key, str):
        return ""

    return api_key.strip()


# ============================================================
# 6. 캐릭터 전체 정보 조회
# ============================================================

def load_character_profile(
    client: NexonClient,
    character_name: str,
) -> dict[str, Any]:
    """
    캐릭터명 하나로 다음 정보를 조회합니다.

    1. OCID
    2. 기본 정보
    3. 스탯
    4. 장비
    5. 심볼
    6. 유니온

    기본 정보 조회가 실패하면 전체 조회 실패로 처리합니다.

    스탯/장비/심볼/유니온 중 일부만 실패하면
    나머지 정상 데이터는 계속 표시합니다.
    """

    # 캐릭터명 -> OCID
    ocid = client.get_ocid(
        character_name
    )

    # 기본 정보는 필수
    basic = client.get_basic(
        ocid
    )

    profile: dict[str, Any] = {
        "ocid": ocid,
        "basic": basic,
        "stat": None,
        "equipment": None,
        "symbols": None,
        "union": None,
        "errors": {},
    }

    optional_api_calls = {
        "stat": client.get_stat,
        "equipment": client.get_equipment,
        "symbols": client.get_symbols,
        "union": client.get_union,
    }

    for (
        section_name,
        api_function,
    ) in optional_api_calls.items():

        try:
            profile[
                section_name
            ] = api_function(
                ocid
            )

        except NexonApiError as error:

            profile[
                "errors"
            ][section_name] = {
                "message": getattr(
                    error,
                    "user_message",
                    str(error),
                ),
                "status_code": getattr(
                    error,
                    "status_code",
                    None,
                ),
                "error_code": getattr(
                    error,
                    "error_code",
                    None,
                ),
                "original_message": getattr(
                    error,
                    "original_message",
                    None,
                ),
            }

    return profile


# ============================================================
# 7. 상단 캐릭터 프로필 출력
# ============================================================

def render_profile_header(
    profile: dict[str, Any],
) -> None:

    basic = profile.get("basic") or {}
    stat = profile.get("stat") or {}
    union = profile.get("union") or {}
    symbol_data = profile.get("symbols") or {}

    stat_map = build_stat_map(
        stat
    )

    symbols = symbol_data.get(
        "symbol",
        [],
    )

    if not isinstance(symbols, list):
        symbols = []

    total_symbol_force = sum(
        to_int(
            symbol.get(
                "symbol_force"
            )
        )
        for symbol in symbols
        if isinstance(symbol, dict)
    )

    active = parse_access_flag(
        basic.get(
            "access_flag"
        )
    )

    status_class = (
        "active-badge"
        if active
        else "inactive-badge"
    )

    status_text = (
        "● 최근 7일 접속"
        if active
        else "● 최근 7일 미접속"
    )

    with st.container(
        border=True
    ):

        image_col, info_col = st.columns(
            [1, 3]
        )

        with image_col:

            character_image = basic.get(
                "character_image"
            )

            if character_image:

                st.image(
                    character_image,
                    width=210,
                )

            else:

                st.info(
                    "캐릭터 이미지 없음"
                )

        with info_col:

            st.markdown(
                (
                    f"<span class='{status_class}'>"
                    f"{status_text}"
                    f"</span>"
                ),
                unsafe_allow_html=True,
            )

            st.header(
                safe_text(
                    basic.get(
                        "character_name"
                    ),
                    "이름 없음",
                )
            )

            st.write(
                f"**{safe_text(basic.get('world_name'))}** · "
                f"**{safe_text(basic.get('character_class'))}** · "
                f"Lv. **{format_number(basic.get('character_level'))}**"
            )

            st.write(
                f"길드: "
                f"**{safe_text(basic.get('character_guild_name'), '없음')}** "
                f"· 조회 기준일: "
                f"**{safe_text(basic.get('date'))}**"
            )

            metric_cols = st.columns(4)

            metric_cols[0].metric(
                "경험치",
                format_percent(
                    basic.get(
                        "character_exp_rate"
                    )
                ),
            )

            metric_cols[1].metric(
                "전투력",
                format_number(
                    find_stat(
                        stat_map,
                        ("전투력",),
                    )
                ),
            )

            metric_cols[2].metric(
                "유니온 레벨",
                format_number(
                    union.get(
                        "union_level"
                    )
                ),
            )

            metric_cols[3].metric(
                "심볼 포스 합계",
                format_number(
                    total_symbol_force
                ),
            )


# ============================================================
# 8. 일부 API 실패 출력
# ============================================================

def render_partial_errors(
    errors: dict[str, Any],
) -> None:

    if not errors:
        return

    section_names = {
        "stat": "능력치",
        "equipment": "장비",
        "symbols": "심볼",
        "union": "유니온",
    }

    with st.expander(
        "일부 정보를 불러오지 못했습니다"
    ):

        for (
            section_key,
            error_data,
        ) in errors.items():

            section_name = section_names.get(
                section_key,
                section_key,
            )

            st.warning(
                f"{section_name}: "
                f"{safe_text(error_data.get('message'))}"
            )

            st.caption(
                f"NEXON 오류 코드: "
                f"{safe_text(error_data.get('error_code'))} · "
                f"HTTP 상태 코드: "
                f"{safe_text(error_data.get('status_code'))}"
            )


# ============================================================
# 9. 핵심 스탯 출력
# ============================================================

CORE_STATS: list[
    tuple[str, tuple[str, ...], bool]
] = [
    (
        "전투력",
        ("전투력",),
        False,
    ),
    (
        "최대 스탯 공격력",
        ("최대 스탯 공격력",),
        False,
    ),
    (
        "데미지",
        ("데미지",),
        True,
    ),
    (
        "최종 데미지",
        ("최종 데미지",),
        True,
    ),
    (
        "보스 몬스터 데미지",
        ("보스 몬스터 데미지",),
        True,
    ),
    (
        "몬스터 방어율 무시",
        (
            "몬스터 방어율 무시",
            "방어율 무시",
        ),
        True,
    ),
    (
        "크리티컬 확률",
        ("크리티컬 확률",),
        True,
    ),
    (
        "크리티컬 데미지",
        ("크리티컬 데미지",),
        True,
    ),
]


def render_core_stats(
    stat_data: dict[str, Any] | None,
) -> None:

    st.subheader(
        "핵심 능력치"
    )

    st.markdown(
        (
            "<div class='section-description'>"
            "RAG 분석에서 캐릭터 성장 상태를 판단할 때 "
            "활용할 가능성이 높은 전투 지표입니다."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    stat_map = build_stat_map(
        stat_data
    )

    if not stat_map:

        st.info(
            "능력치 정보를 불러오지 못했습니다."
        )

        return

    for start in range(
        0,
        len(CORE_STATS),
        4,
    ):

        columns = st.columns(4)

        current_stats = CORE_STATS[
            start:start + 4
        ]

        for (
            column,
            (
                label,
                aliases,
                is_percent,
            ),
        ) in zip(
            columns,
            current_stats,
        ):

            value = find_stat(
                stat_map,
                aliases,
            )

            if is_percent:
                display_value = (
                    format_percent(value)
                )

            else:
                display_value = (
                    format_number(value)
                )

            column.metric(
                label,
                display_value,
            )

    with st.expander(
        "전체 능력치 보기"
    ):

        stat_rows = [
            {
                "능력치": stat_name,
                "값": stat_value,
            }
            for (
                stat_name,
                stat_value,
            ) in stat_map.items()
        ]

        st.dataframe(
            stat_rows,
            hide_index=True,
            use_container_width=True,
        )


# ============================================================
# 10. 심볼 출력
# ============================================================

def render_symbols(
    symbol_data: dict[str, Any] | None,
) -> None:

    st.subheader(
        "심볼"
    )

    st.markdown(
        (
            "<div class='section-description'>"
            "심볼명·레벨·포스를 먼저 보여주고, "
            "성장치는 클릭해서 확인합니다."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    if not symbol_data:

        st.info(
            "심볼 정보를 불러오지 못했습니다."
        )

        return

    symbols = symbol_data.get(
        "symbol",
        [],
    )

    if (
        not isinstance(symbols, list)
        or not symbols
    ):

        st.info(
            "현재 장착된 심볼이 없습니다."
        )

        return

    for start in range(
        0,
        len(symbols),
        3,
    ):

        columns = st.columns(3)

        for (
            column,
            symbol,
        ) in zip(
            columns,
            symbols[start:start + 3],
        ):

            if not isinstance(
                symbol,
                dict,
            ):
                continue

            with column:

                with st.container(
                    border=True
                ):

                    icon_col, info_col = (
                        st.columns(
                            [1, 3]
                        )
                    )

                    with icon_col:

                        symbol_icon = (
                            symbol.get(
                                "symbol_icon"
                            )
                        )

                        if symbol_icon:

                            st.image(
                                symbol_icon,
                                width=54,
                            )

                    with info_col:

                        st.markdown(
                            f"**{safe_text(symbol.get('symbol_name'))}**"
                        )

                        st.caption(
                            f"Lv. "
                            f"{format_number(symbol.get('symbol_level'))} "
                            f"· 포스 "
                            f"{format_number(symbol.get('symbol_force'))}"
                        )

                    current_growth = to_int(
                        symbol.get(
                            "symbol_growth_count"
                        )
                    )

                    required_growth = to_int(
                        symbol.get(
                            "symbol_require_growth_count"
                        )
                    )

                    progress = (
                        calculate_symbol_progress(
                            symbol
                        )
                    )

                    if required_growth > 0:

                        st.progress(
                            progress
                        )

                        st.caption(
                            f"성장치 "
                            f"{current_growth:,} / "
                            f"{required_growth:,}"
                        )

                    with st.expander(
                        "심볼 세부 정보"
                    ):

                        st.write(
                            "심볼명:",
                            safe_text(
                                symbol.get(
                                    "symbol_name"
                                )
                            ),
                        )

                        st.write(
                            "심볼 레벨:",
                            format_number(
                                symbol.get(
                                    "symbol_level"
                                )
                            ),
                        )

                        st.write(
                            "심볼 포스:",
                            format_number(
                                symbol.get(
                                    "symbol_force"
                                )
                            ),
                        )

                        st.write(
                            "현재 성장치:",
                            format_number(
                                symbol.get(
                                    "symbol_growth_count"
                                )
                            ),
                        )

                        st.write(
                            "필요 성장치:",
                            format_number(
                                symbol.get(
                                    "symbol_require_growth_count"
                                )
                            ),
                        )


# ============================================================
# 11. 유니온 출력
# ============================================================

def render_union(
    union_data: dict[str, Any] | None,
) -> None:

    st.subheader(
        "유니온"
    )

    if not union_data:

        st.info(
            "유니온 정보를 불러오지 못했거나 "
            "유니온 정보가 없습니다."
        )

        return

    with st.container(
        border=True
    ):

        union_cols = st.columns(2)

        union_cols[0].metric(
            "유니온 레벨",
            format_number(
                union_data.get(
                    "union_level"
                )
            ),
        )

        union_cols[1].metric(
            "유니온 등급",
            safe_text(
                union_data.get(
                    "union_grade"
                )
            ),
        )

        st.caption(
            f"조회 기준일: "
            f"{safe_text(union_data.get('date'))}"
        )


# ============================================================
# 12. 장비 출력
# ============================================================

def render_equipment(
    equipment_data: dict[str, Any] | None,
) -> None:

    st.subheader(
        "장비 및 장비 성장"
    )

    st.markdown(
        (
            "<div class='section-description'>"
            "현재 적용 중인 장비만 표시합니다. "
            "스타포스와 잠재능력 등급은 카드에서 확인하고, "
            "세부 정보는 클릭해서 확인할 수 있습니다."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    if not equipment_data:

        st.info(
            "장비 정보를 불러오지 못했습니다."
        )

        return

    equipment_items = (
        equipment_data.get(
            "item_equipment",
            [],
        )
    )

    if (
        not isinstance(
            equipment_items,
            list,
        )
        or not equipment_items
    ):

        st.info(
            "현재 장착된 장비 정보가 없습니다."
        )

        return

    st.caption(
        f"적용 프리셋: "
        f"{safe_text(equipment_data.get('preset_no'))} · "
        f"장비 수: {len(equipment_items)}개 · "
        f"조회 기준일: "
        f"{safe_text(equipment_data.get('date'))}"
    )

    for start in range(
        0,
        len(equipment_items),
        3,
    ):

        columns = st.columns(3)

        for (
            column,
            item,
        ) in zip(
            columns,
            equipment_items[
                start:start + 3
            ],
        ):

            if not isinstance(
                item,
                dict,
            ):
                continue

            with column:

                with st.container(
                    border=True
                ):

                    icon_col, info_col = (
                        st.columns(
                            [1, 3]
                        )
                    )

                    with icon_col:

                        item_icon = item.get(
                            "item_icon"
                        )

                        if item_icon:

                            st.image(
                                item_icon,
                                width=56,
                            )

                    with info_col:

                        st.markdown(
                            f"**{safe_text(item.get('item_name'))}**"
                        )

                        st.caption(
                            f"{safe_text(item.get('item_equipment_part'))} · "
                            f"{safe_text(item.get('item_equipment_slot'))}"
                        )

                    starforce = safe_text(
                        item.get(
                            "starforce"
                        ),
                        "0",
                    )

                    potential_grade = safe_text(
                        item.get(
                            "potential_option_grade"
                        ),
                        "없음",
                    )

                    additional_grade = safe_text(
                        item.get(
                            "additional_potential_option_grade"
                        ),
                        "없음",
                    )

                    st.write(
                        f"⭐ **{starforce}성**"
                    )

                    st.caption(
                        f"잠재 {potential_grade} · "
                        f"에디셔널 {additional_grade}"
                    )

                    with st.expander(
                        "장비 세부 정보"
                    ):

                        st.write(
                            "장비 부위:",
                            safe_text(
                                item.get(
                                    "item_equipment_part"
                                )
                            ),
                        )

                        st.write(
                            "장착 슬롯:",
                            safe_text(
                                item.get(
                                    "item_equipment_slot"
                                )
                            ),
                        )

                        st.write(
                            "아이템명:",
                            safe_text(
                                item.get(
                                    "item_name"
                                )
                            ),
                        )

                        st.write(
                            "스타포스:",
                            f"{starforce}성",
                        )

                        st.write(
                            "잠재능력 등급:",
                            potential_grade,
                        )

                        st.write(
                            "에디셔널 잠재능력 등급:",
                            additional_grade,
                        )


# ============================================================
# 13. RAG 전달용 컨텍스트 생성
# ============================================================

def build_rag_context(
    profile: dict[str, Any],
) -> dict[str, Any]:

    basic = profile.get(
        "basic"
    ) or {}

    union = profile.get(
        "union"
    ) or {}

    symbol_data = profile.get(
        "symbols"
    ) or {}

    equipment_data = profile.get(
        "equipment"
    ) or {}

    level = to_int(
        basic.get(
            "character_level"
        )
    )

    union_level = to_int(
        union.get(
            "union_level"
        )
    )

    symbols = symbol_data.get(
        "symbol",
        [],
    )

    equipment = equipment_data.get(
        "item_equipment",
        [],
    )

    if not isinstance(symbols, list):
        symbols = []

    if not isinstance(equipment, list):
        equipment = []

    symbol_summary = [
        {
            "name": symbol.get(
                "symbol_name"
            ),
            "level": symbol.get(
                "symbol_level"
            ),
            "force": symbol.get(
                "symbol_force"
            ),
        }
        for symbol in symbols
        if isinstance(symbol, dict)
    ]

    equipment_summary = [
        {
            "part": item.get(
                "item_equipment_part"
            ),
            "slot": item.get(
                "item_equipment_slot"
            ),
            "name": item.get(
                "item_name"
            ),
            "starforce": item.get(
                "starforce"
            ),
            "potential_grade": item.get(
                "potential_option_grade"
            ),
            "additional_potential_grade": item.get(
                "additional_potential_option_grade"
            ),
        }
        for item in equipment
        if isinstance(item, dict)
    ]

    return {
        "character_name": basic.get(
            "character_name"
        ),
        "world": basic.get(
            "world_name"
        ),
        "job": basic.get(
            "character_class"
        ),
        "level": level,
        "level_band": get_level_band(
            level
        ),
        "recently_active": parse_access_flag(
            basic.get(
                "access_flag"
            )
        ),
        "union_level": union_level,
        "union_grade": union.get(
            "union_grade"
        ),
        "union_band": get_union_band(
            union_level
        ),
        "symbol_count": len(
            symbols
        ),
        "equipment_count": len(
            equipment
        ),
        "symbols": symbol_summary,
        "equipment": equipment_summary,
    }


# ============================================================
# 14. RAG 영역 출력
# ============================================================

def render_rag_section(
    profile: dict[str, Any],
) -> None:

    rag_context = build_rag_context(
        profile
    )

    st.markdown("---")

    st.markdown(
        """
        <div class="rag-box">
            <h3 style="margin-top: 0;">
                다음 단계: 캐릭터 맞춤형 RAG 분석
            </h3>

            <p style="margin-bottom: 0;">
                현재 화면은 캐릭터 정보 확인 단계입니다.
                이후에는 아래 캐릭터 정보를 검색 조건으로 사용해
                같은 직업·레벨·유니온·장비 성장 구간의
                커뮤니티 문서를 검색합니다.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    context_cols = st.columns(5)

    context_cols[0].metric(
        "직업",
        safe_text(
            rag_context.get(
                "job"
            )
        ),
    )

    context_cols[1].metric(
        "레벨 구간",
        safe_text(
            rag_context.get(
                "level_band"
            )
        ),
    )

    context_cols[2].metric(
        "유니온 구간",
        safe_text(
            rag_context.get(
                "union_band"
            )
        ),
    )

    context_cols[3].metric(
        "심볼 수",
        format_number(
            rag_context.get(
                "symbol_count"
            )
        ),
    )

    context_cols[4].metric(
        "장비 수",
        format_number(
            rag_context.get(
                "equipment_count"
            )
        ),
    )

    st.text_input(
        "이 캐릭터에 대해 궁금한 점",
        placeholder=(
            "예: 현재 장비와 심볼 중 "
            "무엇을 먼저 성장시키는 게 좋을까요?"
        ),
        disabled=True,
    )

    st.button(
        "RAG 맞춤 분석 시작",
        disabled=True,
        use_container_width=True,
    )

    st.caption(
        "질문 입력·벡터 검색·근거 답변은 "
        "다음 구현 단계에서 연결합니다."
    )

    with st.expander(
        "RAG 전달 컨텍스트 미리보기"
    ):

        st.json(
            rag_context
        )


# ============================================================
# 15. 전체 프로필 화면 출력
# ============================================================

def render_profile(
    profile: dict[str, Any],
) -> None:

    render_profile_header(
        profile
    )

    render_partial_errors(
        profile.get(
            "errors",
            {},
        )
    )

    st.markdown("---")

    render_core_stats(
        profile.get(
            "stat"
        )
    )

    st.markdown("---")

    symbol_col, union_col = st.columns(
        [2, 1]
    )

    with symbol_col:

        render_symbols(
            profile.get(
                "symbols"
            )
        )

    with union_col:

        render_union(
            profile.get(
                "union"
            )
        )

    st.markdown("---")

    render_equipment(
        profile.get(
            "equipment"
        )
    )

    render_rag_section(
        profile
    )


# ============================================================
# 16. 메인 실행
# ============================================================

def main() -> None:

    st.title(
        "🍁 메이플 캐릭터 맞춤 가이드"
    )

    st.markdown(
        (
            "<div class='page-description'>"
            "캐릭터 정보를 확인하고, "
            "이후 해당 정보를 RAG 검색 조건으로 활용합니다."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    api_key = get_api_key()

    with st.form(
        "character_search_form"
    ):

        character_name = st.text_input(
            "캐릭터명",
            placeholder=(
                "조회할 메이플스토리 "
                "캐릭터명을 입력하세요"
            ),
        )

        submitted = st.form_submit_button(
            "캐릭터 조회",
            type="primary",
            use_container_width=True,
        )

    if submitted:

        normalized_name = (
            character_name.strip()
        )

        if not api_key:

            st.error(
                "NEXON Open API Key를 입력하거나 "
                ".streamlit/secrets.toml에 설정해 주세요."
            )

        elif not normalized_name:

            st.warning(
                "캐릭터명을 입력해 주세요."
            )

        else:

            try:

                client = NexonClient(
                    api_key=api_key
                )

                with st.spinner(
                    "캐릭터 정보를 불러오는 중입니다..."
                ):

                    profile = (
                        load_character_profile(
                            client,
                            normalized_name,
                        )
                    )

                st.session_state[
                    "character_profile"
                ] = profile

            except NexonApiError as error:

                st.session_state.pop(
                    "character_profile",
                    None,
                )

                st.error(
                    getattr(
                        error,
                        "user_message",
                        str(error),
                    )
                )

                with st.expander(
                    "오류 상세 정보"
                ):

                    st.write(
                        "NEXON 오류 코드:",
                        safe_text(
                            getattr(
                                error,
                                "error_code",
                                None,
                            )
                        ),
                    )

                    st.write(
                        "HTTP 상태 코드:",
                        safe_text(
                            getattr(
                                error,
                                "status_code",
                                None,
                            )
                        ),
                    )

                    st.write(
                        "원본 메시지:",
                        safe_text(
                            getattr(
                                error,
                                "original_message",
                                None,
                            )
                        ),
                    )

            except ValueError as error:

                st.session_state.pop(
                    "character_profile",
                    None,
                )

                st.warning(
                    str(error)
                )

            except Exception as error:

                st.session_state.pop(
                    "character_profile",
                    None,
                )

                st.error(
                    "예상하지 못한 오류가 발생했습니다."
                )

                with st.expander(
                    "개발용 오류 확인"
                ):

                    st.exception(
                        error
                    )

    profile = st.session_state.get(
        "character_profile"
    )

    if profile:

        render_profile(
            profile
        )

    else:

        st.info(
            "캐릭터명을 입력하고 조회하면 "
            "기본 정보·활동 여부·능력치·심볼·유니온·장비가 표시됩니다."
        )

    st.markdown("---")

    st.caption(
        "Data based on NEXON Open API"
    )


if __name__ == "__main__":
    main()