from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import plotly.graph_objects as go
import streamlit as st

STREAMLIT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STREAMLIT_DIR))

from dashboard_utils import format_value, get_active_ability_options, get_hyper_stat_rows
from nexon_client import NexonApiError, NexonClient


st.markdown(
    """
    <style>
    .stApp { background: #0e1117; }
    .block-container { max-width: 1600px; padding-top: 2rem; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(145deg, #1b222d, #151b24);
        border-color: rgba(255,255,255,.09);
        box-shadow: 0 8px 24px rgba(0,0,0,.16);
    }
    .dashboard-title { color: #f5f7fa; font-size: 2rem; font-weight: 800; }
    .card-title { font-size: 1.05rem; font-weight: 800; margin-bottom: .35rem; }
    .cyan { color: #55d6ff; } .pink { color: #ff4f9a; }
    .yellow { color: #ffd452; } .purple { color: #c78cff; }
    .muted { color: #9aa4b2; font-size: .86rem; }
    .badge { display: inline-block; padding: .35rem .55rem; margin: .15rem;
             border-radius: 6px; background: #29351c; color: #d9f99d; font-size: .82rem; }
    .hero-name { font-size: 1.65rem; font-weight: 800; color: #f5f7fa; }
    .hero-meta { color: #b8c1cd; margin-top: .25rem; }
    .hero-power { color: #f7df74; font-size: 1.55rem; font-weight: 800; }
    .stat-label { color: #9aa4b2; font-size: .82rem; }
    .stat-value { color: #f5f7fa; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)


def safe_call(callable_: Any, default: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        value = callable_()
        return value if isinstance(value, dict) else (default or {})
    except (NexonApiError, TypeError, AttributeError):
        return default or {}


def card_title(title: str, accent: str) -> None:
    st.markdown(f'<div class="card-title {accent}">{title}</div>', unsafe_allow_html=True)


def empty_card(message: str) -> None:
    st.markdown(f'<div class="muted">{message}</div>', unsafe_allow_html=True)


def render_stat_grid(stat: dict[str, Any]) -> None:
    stat_list = stat.get("final_stat", [])
    if not isinstance(stat_list, list) or not stat_list:
        empty_card("능력치 데이터가 없습니다.")
        return
    columns = st.columns(3)
    for index, item in enumerate(stat_list):
        if not isinstance(item, dict):
            continue
        with columns[index % 3]:
            st.markdown(
                f'<div class="stat-label">{item.get("stat_name", "정보 없음")}</div>'
                f'<div class="stat-value">{format_value(item.get("stat_value"))}</div>',
                unsafe_allow_html=True,
            )


def render_equipment(equipment: dict[str, Any]) -> None:
    items = equipment.get("item_equipment", [])
    if not isinstance(items, list) or not items:
        empty_card("장비 데이터가 없습니다.")
        return
    visible_items = items[:6]
    for item in visible_items:
        if not isinstance(item, dict):
            continue
        left, right = st.columns([1, 5])
        with left:
            if item.get("item_icon"):
                st.image(item["item_icon"], width=42)
        with right:
            st.markdown(f"**{item.get('item_name', '정보 없음')}**")
    if len(items) > len(visible_items):
        with st.expander("더 많은 장비 보기"):
            for item in items[len(visible_items):]:
                if isinstance(item, dict):
                    st.write(item.get("item_name", "정보 없음"))


def render_symbols(symbols: dict[str, Any]) -> None:
    symbol_list = symbols.get("symbol", [])
    if not isinstance(symbol_list, list) or not symbol_list:
        empty_card("심볼 데이터가 없습니다.")
        return
    for symbol in symbol_list[:4]:
        if isinstance(symbol, dict):
            st.markdown(
                f"**{symbol.get('symbol_name', '정보 없음')}** · "
                f"Lv.{format_value(symbol.get('symbol_level'))} · "
                f"힘 {format_value(symbol.get('symbol_force'))}"
            )
    if len(symbol_list) > 4:
        with st.expander("전체 심볼 보기"):
            for symbol in symbol_list[4:]:
                if isinstance(symbol, dict):
                    st.write(symbol.get("symbol_name", "정보 없음"))


def render_radar(propensity: dict[str, Any]) -> None:
    field_map = {
        "카리스마": "charisma_level", "감성": "sensibility_level",
        "통찰력": "insight_level", "의지": "willingness_level",
        "손재주": "handicraft_level", "매력": "charm_level",
    }
    values = [propensity.get(field) for field in field_map.values()]
    if any(value is None for value in values):
        empty_card("성향 데이터가 없습니다.")
        return
    labels = list(field_map.keys())
    fig = go.Figure(go.Scatterpolar(r=values + [values[0]], theta=labels + [labels[0]], fill="toself"))
    fig.update_traces(line_color="#54c7f7", fillcolor="rgba(84,199,247,.25)")
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], gridcolor="#384352"), angularaxis=dict(color="#9aa4b2")),
        margin=dict(l=18, r=18, t=10, b=10), height=245,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f5f7fa"), showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def load_character(client: NexonClient, character_name: str) -> dict[str, dict[str, Any]]:
    ocid = client.get_ocid(character_name)
    basic = client.get_basic(ocid)
    result = {
        "basic": basic,
        "stat": client.get_stat(ocid),
        "equipment": client.get_equipment(ocid),
        "symbols": client.get_symbols(ocid),
        "union": safe_call(lambda: client.get_union(ocid)),
        "popularity": safe_call(lambda: client.get_popularity(ocid)),
        "hyper_stat": safe_call(lambda: client.get_hyper_stat(ocid)),
        "propensity": safe_call(lambda: client.get_propensity(ocid)),
        "ability": safe_call(lambda: client.get_ability(ocid)),
        "guild": {},
    }
    guild_name = basic.get("character_guild_name")
    world_name = basic.get("world_name") or ""
    if guild_name and world_name:
        guild_id = safe_call(
            lambda: {
                "oguild_id": client.get_guild_id(
                    guild_name,
                    world_name,
                )
            }
        ).get("oguild_id")
        if guild_id:
            result["guild"] = safe_call(lambda: client.get_guild_basic(guild_id))
    return result


def render_dashboard() -> None:
    st.markdown("<div class='dashboard-title'>🍁 메이플스토리 캐릭터 정보</div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("**캐릭터명을 입력하세요**")
        query_col, button_col = st.columns([6, 1])
        with query_col:
            name = st.text_input("캐릭터명", placeholder="캐릭터명을 입력하세요", label_visibility="collapsed", key="character_query")
        with button_col:
            submitted = st.button("조회", use_container_width=True, type="primary")
    if submitted:
        if not name.strip():
            st.warning("캐릭터명을 입력해주세요.")
            return
        api_key = st.secrets.get("NEXON_API_KEY")
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

    basic, popularity = data["basic"], data["popularity"]
    with st.container(border=True):
        card_title("CHARACTER SUMMARY", "pink")
        image_col, info_col, power_col = st.columns([1, 4, 2])
        with image_col:
            if basic.get("character_image"):
                st.image(basic["character_image"], width=120)
            else:
                st.markdown("🧙")
        with info_col:
            st.markdown(f'<div class="hero-name">{basic.get("character_name", "정보 없음")}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="hero-meta">Lv.{format_value(basic.get("character_level"))} · '
                f'{basic.get("world_name", "정보 없음")} · {basic.get("character_class", "정보 없음")}</div>',
                unsafe_allow_html=True,
            )
            st.caption(f"길드 · {basic.get('character_guild_name') or '정보 없음'}")
        with power_col:
            st.caption("인기도")
            st.markdown(f'<div class="hero-power">{format_value(popularity.get("popularity"))}</div>', unsafe_allow_html=True)

    left, right = st.columns([2, 1])
    with left:
        with st.container(border=True):
            card_title("전투력 / 종합 능력치", "cyan")
            render_stat_grid(data["stat"])
    with right:
        with st.container(border=True):
            card_title("ABILITY", "yellow")
            options = get_active_ability_options(data["ability"])
            if options:
                for option in options:
                    st.markdown(f'<span class="badge">{option}</span>', unsafe_allow_html=True)
            else:
                empty_card("어빌리티 정보 없음")
        with st.container(border=True):
            card_title("HYPER STAT", "cyan")
            rows = get_hyper_stat_rows(data["hyper_stat"])
            if rows:
                for stat_name, level in rows[:10]:
                    st.write(f"{stat_name} · Lv.{format_value(level)}")
            else:
                empty_card("하이퍼 스탯 정보 없음")

    equipment_col, symbol_col = st.columns([1, 1])
    with equipment_col:
        with st.container(border=True):
            card_title("장착 장비", "yellow")
            render_equipment(data["equipment"])
    with symbol_col:
        with st.container(border=True):
            card_title("심볼 정보", "purple")
            render_symbols(data["symbols"])

    propensity_col, exp_col = st.columns([1, 1])
    with propensity_col:
        with st.container(border=True):
            card_title("성향", "cyan")
            render_radar(data["propensity"])
    with exp_col:
        with st.container(border=True):
            card_title("EXP HISTORY", "pink")
            empty_card("경험치 히스토리 데이터가 없습니다.")

    union_col, guild_col = st.columns([1, 1])
    with union_col:
        with st.container(border=True):
            card_title("유니온", "purple")
            if data["union"]:
                st.metric("유니온 레벨", format_value(data["union"].get("union_level")))
                st.write(f"등급 · {data['union'].get('union_grade', '정보 없음')}")
                st.write(f"공격대원 · {len(data['union'].get('union_raider', []))}명")
            else:
                empty_card("유니온 정보를 불러오지 못했습니다.")
    with guild_col:
        with st.container(border=True):
            card_title("길드 정보", "yellow")
            if data["guild"]:
                st.metric("길드 레벨", format_value(data["guild"].get("guild_level")))
                st.write(data["guild"].get("guild_name", basic.get("character_guild_name", "정보 없음")))
                st.write(f"길드 인원 · {format_value(data['guild'].get('guild_member_count'))}")
            else:
                st.write(f"길드명 · {basic.get('character_guild_name') or '정보 없음'}")
                empty_card("길드 상세 정보가 없습니다.")


render_dashboard()
