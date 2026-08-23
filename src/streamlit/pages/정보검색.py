from __future__ import annotations

import os
import sys
import tomllib
from datetime import date, timedelta
from html import escape
from pathlib import Path
from typing import Any

os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import plotly.graph_objects as go
import streamlit as st

STREAMLIT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STREAMLIT_DIR))

from dashboard_utils import format_value, get_hyper_stat_rows
from nexon_client import NexonApiError, NexonClient

PROJECT_ROOT = STREAMLIT_DIR.parents[1]


def get_api_key() -> str | None:
    """실행 위치와 무관하게 NEXON API KEY를 찾는다."""
    try:
        key = st.secrets.get("NEXON_API_KEY")
    except Exception:
        key = None
    if key:
        return key
    key = os.environ.get("NEXON_API_KEY")
    if key:
        return key
    for secrets_path in (
        PROJECT_ROOT / ".streamlit" / "secrets.toml",
        STREAMLIT_DIR / ".streamlit" / "secrets.toml",
    ):
        if secrets_path.is_file():
            with secrets_path.open("rb") as file:
                key = tomllib.load(file).get("NEXON_API_KEY")
            if key:
                return key
    return None


st.markdown(
    """
    <style>
    .stApp { background: #0d1420; }
    .block-container { max-width: 1500px; padding-top: 1.5rem; }
    .dashboard-title { color: #f5f7fa; font-size: 1.8rem; font-weight: 800; margin-bottom: .6rem; }

    /* ===== 공통 패널 ===== */
    .mp-panel { background: linear-gradient(180deg, #1c3d55 0%, #16293c 100%); border: 2px solid #3d87ab;
        border-radius: 10px; padding: 9px 11px 11px; margin-bottom: 12px; }
    .mp-head { display: flex; align-items: center; justify-content: space-between;
        color: #ffd83d; font-size: 15px; font-weight: 800; margin-bottom: 8px; }
    .mp-head small { color: #b9dced; font-size: 11.5px; font-weight: 600; }
    .mp-block { background: rgba(6, 18, 32, .45); border-radius: 8px; padding: 8px 10px; margin-top: 8px; }

    /* ===== CHARACTER INFO ===== */
    .ci-body { display: grid; grid-template-columns: 118px 1fr 132px; gap: 8px; align-items: center;
        background: linear-gradient(135deg, #3a2a6d 0%, #6b3f8f 55%, #2c2b63 100%); border-radius: 8px; padding: 10px; }
    .ci-col { display: flex; flex-direction: column; gap: 6px; }
    .ci-col.right { align-items: flex-end; }
    .ci-pill { display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%;
        background: rgba(11, 22, 40, .72); border-radius: 14px; padding: 4px 10px; color: #dfe9f5; font-size: 12px; }
    .ci-pill b { color: #ffffff; font-weight: 700; }
    .ci-pill .k { color: #a8c4dc; }
    .ci-avatar { display: flex; align-items: center; justify-content: center; min-height: 116px; }
    .ci-avatar img { max-height: 130px; }
    .ci-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
    .ci-class { background: rgba(11,22,40,.72); border-radius: 14px; padding: 4px 16px; color: #eaf2fb; font-size: 12.5px; font-weight: 700; }
    .ci-level { background: rgba(11,22,40,.72); border-radius: 8px; padding: 4px 12px; color: #ffffff; font-size: 12.5px; font-weight: 800; }
    .ci-name { background: #17a2c9; border-radius: 6px; padding: 3px 12px; color: #fff; font-weight: 800; font-size: 13px; text-align: center; }
    .ci-exp { background: #c8e83c; border-radius: 6px; padding: 2px 12px; color: #1d2a12; font-weight: 800; font-size: 12px; text-align: center; margin-top: 3px; }

    /* ===== 장비 / 심볼 목록 ===== */
    .mp-purple { background: linear-gradient(135deg, #3a2a6d 0%, #6b3f8f 55%, #2c2b63 100%);
        border-radius: 8px; padding: 10px; display: flex; flex-direction: column; gap: 6px; }
    .eq-row { display: flex; align-items: center; gap: 10px; background: rgba(11, 22, 40, .72);
        border-radius: 8px; padding: 5px 10px; color: #eaf2fb; font-size: 12.5px; }
    .eq-row img { width: 32px; height: 32px; object-fit: contain; flex: none; }
    .eq-name { flex: 1; min-width: 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-weight: 700; }
    .eq-meta { flex: none; color: #a8c4dc; font-size: 11.5px; }
    .eq-scroll { max-height: 420px; overflow-y: auto; }
    [data-testid="stPlotlyChart"] { background: linear-gradient(135deg, #3a2a6d 0%, #6b3f8f 55%, #2c2b63 100%);
        border-radius: 8px; padding: 6px 4px; margin-top: 8px; }

    /* ===== 전투력 ===== */
    .mp-power { background: linear-gradient(180deg, #2f6f92, #24506d); border: 1px solid #4e9cc0; border-radius: 8px;
        padding: 10px; text-align: center; color: #ffffff; font-size: 21px; font-weight: 800; }

    /* ===== 스탯 표 ===== */
    .mp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 18px; }
    .mp-cell { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; padding: 2px 0; font-size: 13px; }
    .mp-cell .k { color: #a9c6db; }
    .mp-cell .v { color: #ffffff; font-weight: 700; }

    /* ===== ABILITY ===== */
    .ab-line { border-radius: 6px; padding: 6px 10px; margin-bottom: 5px; color: #fff; font-size: 12.5px; font-weight: 700; }
    .ab-legendary { background: #2f9e46; } .ab-unique { background: #e8901c; }
    .ab-epic { background: #7b4fc4; } .ab-rare { background: #2f7ec4; } .ab-none { background: #4a5a6b; }
    .ab-grade { border: 2px solid #ffd83d; }
    .mp-preset { display: flex; align-items: center; gap: 6px; margin-top: 8px; }
    .mp-preset .lab { color: #cfe6f4; font-size: 12px; font-weight: 700; }
    .mp-preset .num { background: rgba(6,18,32,.5); color: #b9d5e8; border-radius: 4px; padding: 2px 8px; font-size: 12px; font-weight: 700; }
    .mp-preset .num.on { background: #ffffff; color: #14293c; }
    .mp-preset .fill { flex: 1; text-align: center; background: rgba(6,18,32,.5); border-radius: 4px; padding: 3px 8px;
        color: #eaf4fb; font-size: 12px; font-weight: 700; }

    /* ===== HYPER STAT ===== */
    .hs-row { display: flex; align-items: center; justify-content: space-between; padding: 2.5px 2px; font-size: 12.5px; }
    .hs-row .k { color: #a9c6db; } .hs-row .v { color: #7f97ab; font-weight: 700; }
    .hs-row.on .k { color: #eaf4fb; } .hs-row.on .v { color: #ffd83d; }

    /* ===== PROPENSITY ===== */
    .pr-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
    .pr-chip { display: flex; align-items: center; justify-content: space-between; gap: 6px;
        background: rgba(6,18,32,.5); border: 1px solid #3d87ab; border-radius: 6px; padding: 5px 9px; font-size: 12px; }
    .pr-chip .k { color: #7fd4f5; font-weight: 700; } .pr-chip .v { color: #ffffff; font-weight: 700; }

    .mp-empty { color: #8ba7bd; font-size: 12.5px; padding: 6px 2px; }
    /* st.container(border=True)로 만든 패널(PROPENSITY / EXP HISTORY)도 .mp-panel과 같은 파란 패널로 */
    div[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .panel-anchor) {
        background: linear-gradient(180deg, #1c3d55 0%, #16293c 100%);
        border: 2px solid #3d87ab; border-radius: 10px; padding: 9px 11px 11px; margin-bottom: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

PERCENT_STATS = {
    "데미지", "최종 데미지", "보스 몬스터 데미지", "일반 몬스터 데미지", "방어율 무시",
    "크리티컬 확률", "크리티컬 데미지", "버프 지속시간", "속성 내성 무시", "상태이상 추가 데미지",
    "소환수 지속시간 증가", "메소 획득량", "아이템 드롭률", "추가 경험치 획득", "상태이상 내성",
    "재사용 대기시간 감소 (%)",
}

ABILITY_GRADE_CLASS = {
    "레전드리": "ab-legendary", "유니크": "ab-unique", "에픽": "ab-epic", "레어": "ab-rare",
}

PROPENSITY_FIELDS = {
    "카리스마": "charisma_level", "감성": "sensibility_level", "통찰력": "insight_level",
    "의지": "willingness_level", "손재주": "handicraft_level", "매력": "charm_level",
}


def safe_call(callable_: Any, default: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        value = callable_()
        return value if isinstance(value, dict) else (default or {})
    except (NexonApiError, TypeError, AttributeError):
        return default or {}


def panel_head(title: str, note: str = "", anchor: bool = False) -> str:
    """anchor=True는 st.container로 감싼 패널임을 CSS에 알려 주는 표시."""
    css_class = "mp-head panel-anchor" if anchor else "mp-head"
    return f'<div class="{css_class}">{escape(title)}<small>{escape(note)}</small></div>'


def format_korean(value: Any) -> str:
    """77960948 -> '7796만 948' 형태로 표시."""
    try:
        number = int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return format_value(value)
    if number >= 10**8:
        eok, rest = divmod(number, 10**8)
        man, ones = divmod(rest, 10**4)
        parts = [f"{eok}억"]
        if man:
            parts.append(f"{man}만")
        if ones:
            parts.append(f"{ones:,}")
        return " ".join(parts)
    if number >= 10**4:
        man, ones = divmod(number, 10**4)
        return f"{man}만 {ones:,}" if ones else f"{man}만"
    return f"{number:,}"


def stat_map(stat: dict[str, Any]) -> dict[str, Any]:
    rows = stat.get("final_stat", [])
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("stat_name")): row.get("stat_value")
        for row in rows
        if isinstance(row, dict) and row.get("stat_name")
    }


def stat_text(stats: dict[str, Any], name: str, korean: bool = False) -> str:
    value = stats.get(name)
    if value in (None, ""):
        return "-"
    text = format_korean(value) if korean else format_value(value)
    if name in PERCENT_STATS and not text.endswith("%"):
        text = f"{text}%"
    return text


def cells(pairs: list[tuple[str, str]]) -> str:
    return "".join(
        f'<div class="mp-cell"><span class="k">{escape(label)}</span><span class="v">{escape(value)}</span></div>'
        for label, value in pairs
    )


def preset_row(active: Any, fill: str) -> str:
    numbers = "".join(
        f'<span class="num{" on" if str(active) == str(number) else ""}">{number}</span>'
        for number in (1, 2, 3)
    )
    return (
        f'<div class="mp-preset"><span class="lab">PRESET</span>{numbers}'
        f'<span class="fill">{escape(fill)}</span></div>'
    )


def render_character_info(
    basic: dict[str, Any],
    popularity: dict[str, Any],
    union: dict[str, Any],
    dojang: dict[str, Any],
    guild: dict[str, Any],
) -> str:
    image = basic.get("character_image") or ""
    avatar = f'<img src="{escape(image)}" alt="캐릭터">' if image else "🧙"
    union_level = union.get("union_level")
    floor = dojang.get("dojang_best_floor")
    guild_name = guild.get("guild_name") or basic.get("character_guild_name") or "-"
    exp_rate = basic.get("character_exp_rate")
    left = "".join(
        f'<div class="ci-pill"><span class="k">{key}</span><b>{escape(value)}</b></div>'
        for key, value in (
            ("유니온", format_value(union_level) if union_level else "-"),
            ("무릉도장", f"{format_value(floor)}층" if floor not in (None, "") else "-"),
            ("인기도", format_value(popularity.get("popularity")) if popularity else "-"),
        )
    )
    right = "".join(
        f'<div class="ci-pill"><span class="k">{key}</span><b>{escape(value)}</b></div>'
        for key, value in (
            ("월드", basic.get("world_name") or "-"),
            ("길드", guild_name),
        )
    )
    return (
        '<div class="mp-panel">'
        + panel_head("CHARACTER INFO", "갱신 시간: 실시간")
        + '<div class="ci-top">'
        + f'<span class="ci-class">{escape(basic.get("character_class") or "-")}</span>'
        + f'<span class="ci-level">Lv. {format_value(basic.get("character_level"))}</span></div>'
        + '<div class="ci-body">'
        + f'<div class="ci-col">{left}</div>'
        + f'<div class="ci-avatar">{avatar}</div>'
        + f'<div class="ci-col right">{right}'
        + f'<div class="ci-name">{escape(basic.get("character_name") or "-")}</div>'
        + (f'<div class="ci-exp">{escape(str(exp_rate))}%</div>' if exp_rate not in (None, "") else "")
        + "</div></div></div>"
    )


def render_stat_panel(stat: dict[str, Any]) -> str:
    stats = stat_map(stat)
    power = stats.get("전투력")
    cooldown = (
        f'{stat_text(stats, "재사용 대기시간 감소 (초)")}초 / '
        f'{stat_text(stats, "재사용 대기시간 감소 (%)")}'
    )
    base = cells([
        ("HP", stat_text(stats, "HP")), ("MP", stat_text(stats, "MP")),
        ("STR", stat_text(stats, "STR")), ("DEX", stat_text(stats, "DEX")),
        ("INT", stat_text(stats, "INT")), ("LUK", stat_text(stats, "LUK")),
    ])
    detail = cells([
        ("스탯 공격력", stat_text(stats, "최대 스탯공격력", korean=True)), ("데미지", stat_text(stats, "데미지")),
        ("최종 데미지", stat_text(stats, "최종 데미지")), ("보스 몬스터 데미지", stat_text(stats, "보스 몬스터 데미지")),
        ("방어율 무시", stat_text(stats, "방어율 무시")), ("일반 몬스터 데미지", stat_text(stats, "일반 몬스터 데미지")),
        ("공격력", stat_text(stats, "공격력")), ("크리티컬 확률", stat_text(stats, "크리티컬 확률")),
        ("마력", stat_text(stats, "마력")), ("크리티컬 데미지", stat_text(stats, "크리티컬 데미지")),
        ("재사용 대기시간 감소", cooldown), ("버프 지속시간", stat_text(stats, "버프 지속시간")),
        ("재사용 대기시간 미적용", stat_text(stats, "재사용 대기시간 미적용")), ("속성 내성 무시", stat_text(stats, "속성 내성 무시")),
        ("상태이상 추가 데미지", stat_text(stats, "상태이상 추가 데미지")), ("소환수 지속시간 증가", stat_text(stats, "소환수 지속시간 증가")),
    ])
    extra = cells([
        ("메소 획득량", stat_text(stats, "메소 획득량")), ("스타포스", stat_text(stats, "스타포스")),
        ("아이템 드롭률", stat_text(stats, "아이템 드롭률")), ("아케인포스", stat_text(stats, "아케인포스")),
        ("추가 경험치 획득", stat_text(stats, "추가 경험치 획득")), ("어센틱포스", stat_text(stats, "어센틱포스")),
    ])
    power_text = format_korean(power) if power not in (None, "") else "-"
    return (
        '<div class="mp-panel">'
        + f'<div class="mp-power">전투력 {escape(power_text)}</div>'
        + f'<div class="mp-block"><div class="mp-grid">{base}</div></div>'
        + f'<div class="mp-block"><div class="mp-grid">{detail}</div></div>'
        + f'<div class="mp-block"><div class="mp-grid">{extra}</div></div>'
        + "</div>"
    )


def render_ability_panel(ability: dict[str, Any]) -> str:
    grade = ability.get("ability_grade") or ""
    grade_class = ABILITY_GRADE_CLASS.get(grade, "ab-none")
    options = ability.get("ability_info", [])
    if not isinstance(options, list):
        options = []
    lines = [
        f'<div class="ab-line {ABILITY_GRADE_CLASS.get(option.get("ability_grade") or grade, "ab-none")}">'
        f'{escape(str(option.get("ability_value") or "-"))}</div>'
        for option in options
        if isinstance(option, dict)
    ]
    if not lines:
        lines = ['<div class="mp-empty">어빌리티 정보가 없습니다.</div>']
    fame = ability.get("remain_fame")
    return (
        '<div class="mp-panel">'
        + panel_head("ABILITY")
        + f'<div class="ab-line ab-grade {grade_class}">🏳 {escape(grade or "어빌리티")} 어빌리티</div>'
        + "".join(lines)
        + preset_row(
            ability.get("preset_no"),
            f"명성치 {format_value(fame)}" if fame not in (None, "") else "명성치 -",
        )
        + "</div>"
    )


def render_hyper_stat_panel(hyper_stat: dict[str, Any]) -> str:
    rows = get_hyper_stat_rows(hyper_stat)
    if rows:
        body = "".join(
            f'<div class="hs-row{" on" if level else ""}">'
            f'<span class="k">{escape(stat_name)}</span>'
            f'<span class="v">Lv. {format_value(level) if level else 0}</span></div>'
            for stat_name, level in rows
        )
    else:
        body = '<div class="mp-empty">하이퍼 스탯 정보가 없습니다.</div>'
    point = hyper_stat.get("use_available_hyper_stat")
    return (
        '<div class="mp-panel">'
        + panel_head("HYPER STAT")
        + body
        + preset_row(
            hyper_stat.get("use_preset_no"),
            f"POINT {format_value(point)}" if point not in (None, "") else "POINT -",
        )
        + "</div>"
    )


def propensity_chips(propensity: dict[str, Any]) -> str:
    if not propensity:
        return '<div class="mp-empty">성향 정보가 없습니다.</div>'
    return (
        '<div class="mp-purple"><div class="pr-grid">'
        + "".join(
            f'<div class="pr-chip"><span class="k">{label}</span>'
            f'<span class="v">Lv.{format_value(propensity.get(field))}</span></div>'
            for label, field in PROPENSITY_FIELDS.items()
        )
        + "</div></div>"
    )


def render_radar(propensity: dict[str, Any]) -> None:
    values = [propensity.get(field) for field in PROPENSITY_FIELDS.values()]
    if any(value is None for value in values):
        st.markdown('<div class="mp-empty">성향 그래프를 그릴 데이터가 없습니다.</div>', unsafe_allow_html=True)
        return
    labels = list(PROPENSITY_FIELDS.keys())
    fig = go.Figure(go.Scatterpolar(r=values + [values[0]], theta=labels + [labels[0]], fill="toself"))
    fig.update_traces(line_color="#7fd4f5", fillcolor="rgba(79,168,214,.45)")
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor="#3d6c8c", linecolor="#3d6c8c"),
            angularaxis=dict(color="#bfe0f2", gridcolor="#3d6c8c", linecolor="#3d6c8c"),
        ),
        margin=dict(l=30, r=30, t=14, b=14), height=250,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#eaf4fb", size=11), showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_exp_history(history: list[tuple[str, float]]) -> None:
    if not history:
        st.markdown('<div class="mp-empty">경험치 히스토리 데이터가 없습니다.</div>', unsafe_allow_html=True)
        return
    labels = [f"{int(day[5:7])}월 {int(day[8:10])}일" for day, _ in history]
    fig = go.Figure(go.Bar(x=labels, y=[rate for _, rate in history], marker_color="#c8e83c"))
    fig.update_layout(
        margin=dict(l=8, r=8, t=10, b=8), height=205,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#bfe0f2", size=11), showlegend=False,
        yaxis=dict(range=[0, 100], ticksuffix="%", gridcolor="#2c4a63", zerolinecolor="#2c4a63"),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_equipment_panel(equipment: dict[str, Any]) -> str:
    items = equipment.get("item_equipment", [])
    if not isinstance(items, list) or not items:
        body = '<div class="mp-empty">장비 데이터가 없습니다.</div>'
    else:
        body = '<div class="mp-purple eq-scroll">' + "".join(
            f'<div class="eq-row">'
            f'<img src="{escape(str(item.get("item_icon") or ""))}" alt="">'
            f'<span class="eq-name">{escape(str(item.get("item_name") or "정보 없음"))}</span>'
            f'<span class="eq-meta">{escape(str(item.get("item_equipment_slot") or ""))}</span>'
            "</div>"
            for item in items
            if isinstance(item, dict)
        ) + "</div>"
    return '<div class="mp-panel">' + panel_head("장착 장비", f"{len(items) if isinstance(items, list) else 0}종") + body + "</div>"


def render_symbol_panel(symbols: dict[str, Any]) -> str:
    symbol_list = symbols.get("symbol", [])
    if not isinstance(symbol_list, list) or not symbol_list:
        body = '<div class="mp-empty">심볼 데이터가 없습니다.</div>'
    else:
        body = '<div class="mp-purple eq-scroll">' + "".join(
            f'<div class="eq-row">'
            f'<img src="{escape(str(symbol.get("symbol_icon") or ""))}" alt="">'
            f'<span class="eq-name">{escape(str(symbol.get("symbol_name") or "정보 없음"))}</span>'
            f'<span class="eq-meta">Lv.{format_value(symbol.get("symbol_level"))} · '
            f'힘 {format_value(symbol.get("symbol_force"))}</span>'
            "</div>"
            for symbol in symbol_list
            if isinstance(symbol, dict)
        ) + "</div>"
    count = len(symbol_list) if isinstance(symbol_list, list) else 0
    return '<div class="mp-panel">' + panel_head("심볼 정보", f"{count}개") + body + "</div>"


def load_exp_history(client: NexonClient, ocid: str, days: int = 8) -> list[tuple[str, float]]:
    """최근 며칠간의 경험치 비율. 데이터가 없는 날은 건너뛴다."""
    history: list[tuple[str, float]] = []
    for offset in range(days, 0, -1):
        day = (date.today() - timedelta(days=offset)).isoformat()
        snapshot = safe_call(lambda current=day: client.get_basic(ocid, date=current))
        rate = snapshot.get("character_exp_rate")
        if rate in (None, ""):
            continue
        try:
            history.append((day, float(rate)))
        except (TypeError, ValueError):
            continue
    return history


def load_character(client: NexonClient, character_name: str) -> dict[str, Any]:
    ocid = client.get_ocid(character_name)
    basic = client.get_basic(ocid)
    result: dict[str, Any] = {
        "basic": basic,
        "stat": client.get_stat(ocid),
        "equipment": client.get_equipment(ocid),
        "symbols": client.get_symbols(ocid),
        "union": safe_call(lambda: client.get_union(ocid)),
        "popularity": safe_call(lambda: client.get_popularity(ocid)),
        "hyper_stat": safe_call(lambda: client.get_hyper_stat(ocid)),
        "propensity": safe_call(lambda: client.get_propensity(ocid)),
        "ability": safe_call(lambda: client.get_ability(ocid)),
        "dojang": safe_call(lambda: client.get_dojang(ocid)),
        "exp_history": load_exp_history(client, ocid),
        "guild": {},
    }
    guild_name = basic.get("character_guild_name")
    world_name = basic.get("world_name") or ""
    if guild_name and world_name:
        guild_id = safe_call(
            lambda: {"oguild_id": client.get_guild_id(guild_name, world_name)}
        ).get("oguild_id")
        if guild_id:
            result["guild"] = safe_call(lambda: client.get_guild_basic(guild_id))
    return result


def render_dashboard() -> None:
    st.markdown("<div class='dashboard-title'>🍁 메이플스토리 캐릭터 정보</div>", unsafe_allow_html=True)
    pending_name = st.session_state.pop("pending_character_name", None)
    if pending_name:
        st.session_state["character_query"] = pending_name
    with st.container(border=True):
        st.markdown("**캐릭터명을 입력하세요**")
        query_col, button_col = st.columns([6, 1])
        with query_col:
            name = st.text_input(
                "캐릭터명",
                placeholder="캐릭터명을 입력하세요",
                label_visibility="collapsed",
                key="character_query",
            )
        with button_col:
            submitted = st.button("조회", use_container_width=True, type="primary") or bool(pending_name)
    if submitted:
        if not name.strip():
            st.warning("캐릭터명을 입력해주세요.")
            return
        api_key = get_api_key()
        if not api_key:
            st.error("NEXON API KEY가 설정되지 않았습니다.")
            return
        try:
            with st.spinner("캐릭터 정보를 불러오는 중입니다..."):
                st.session_state.character_dashboard = load_character(NexonClient(api_key=api_key), name)
        except (NexonApiError, ValueError) as error:
            st.error(getattr(error, "user_message", str(error)))
            return

    data = st.session_state.get("character_dashboard")
    if not data:
        st.info("캐릭터명을 입력하고 조회하면 상세 정보가 표시됩니다.")
        return

    info_col, equipment_col = st.columns([1.15, 1.0], gap="small")

    with info_col:
        st.markdown(
            render_character_info(
                data["basic"], data["popularity"], data["union"], data["dojang"], data["guild"]
            ),
            unsafe_allow_html=True,
        )
        st.markdown(render_stat_panel(data["stat"]), unsafe_allow_html=True)

    with equipment_col:
        st.markdown(render_equipment_panel(data["equipment"]), unsafe_allow_html=True)
        st.markdown(render_symbol_panel(data["symbols"]), unsafe_allow_html=True)

    ability_col, side_col = st.columns(2, gap="small")

    with ability_col:
        st.markdown(render_ability_panel(data["ability"]), unsafe_allow_html=True)
        st.markdown(render_hyper_stat_panel(data["hyper_stat"]), unsafe_allow_html=True)

    with side_col:
        with st.container(border=True):
            st.markdown(panel_head("PROPENSITY", anchor=True), unsafe_allow_html=True)
            st.markdown(propensity_chips(data["propensity"]), unsafe_allow_html=True)
            render_radar(data["propensity"])
        with st.container(border=True):
            st.markdown(panel_head("EXP HISTORY", anchor=True), unsafe_allow_html=True)
            render_exp_history(data["exp_history"])


render_dashboard()
