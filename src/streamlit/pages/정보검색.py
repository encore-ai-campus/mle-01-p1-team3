import os
import sys
from pathlib import Path

os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import streamlit as st

# app.py와 nexon_client.py가 같은 폴더에 있음
STREAMLIT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STREAMLIT_DIR))

from nexon_client import NexonApiError, NexonClient

# ===================
# 캐릭터 정보 검색
# ===================
st.title("🍁 메이플스토리 캐릭터 정보 검색")

api_key = st.secrets.get("NEXON_API_KEY")

if not api_key:
    st.error("NEXON API KEY가 설정되지 않았습니다.")
    st.stop()

client = NexonClient(api_key=api_key)


character_name = st.text_input("캐릭터명을 입력하세요", placeholder="캐릭터명을 입력하세요").strip()

if st.button("조회"):
    if not character_name.strip():
        st.warning("캐릭터명을 입력해주세요.")
        st.stop()

    try:
        # ==============================================
        # 1. 캐릭터명으로 OCID 조회
        # ==============================================

        ocid = client.get_ocid(character_name)

        # ==============================================
        # 3. 조회 성공 결과
        # ==============================================


        basic = client.get_basic(ocid)
        stat = client.get_stat(ocid)
        equipment = client.get_equipment(ocid)
        symbols = client.get_symbols(ocid)

        try:
            union = client.get_union(ocid)
            union_error = None
        except NexonApiError as error:
            union = {}
            union_error = error

        
        # 캐릭터 정보 한 줄 표시
        character_image = basic.get("character_image")

        col_image, col_name, col_world, col_class, col_level, col_guild = st.columns(
            [1, 2, 2, 2, 1, 2]
        )

        with col_image:
            if character_image:
                st.image(character_image, width=70)
            else:
                st.write("🧙")

        with col_name:
            st.caption("캐릭터명")
            st.markdown(f"**{basic.get('character_name', '-')}**")

        with col_world:
            st.caption("월드")
            st.markdown(f"**{basic.get('world_name', '-')}**")

        with col_class:
            st.caption("직업")
            st.markdown(f"**{basic.get('character_class', '-')}**")

        with col_level:
            st.caption("레벨")
            st.markdown(f"**{basic.get('character_level', '-')}**")

        with col_guild:
            st.caption("길드")
            st.markdown(f"**{basic.get('character_guild_name', '-')}**")

        st.divider()

        tab1, tab2, tab3, tab4 = st.tabs(
            ["능력치", "장비", "심볼", "유니온"]
        )

        # 능력치
        with tab1:
            st.subheader("종합 능력치")

            stat_list = stat.get("final_stat", [])

            if stat_list:
                stat_columns = st.columns(3)

                for index, item in enumerate(stat_list):
                    stat_name = item.get("stat_name", "-")
                    stat_value = item.get("stat_value", "-")

                    with stat_columns[index % 3]:
                        st.metric(stat_name, stat_value)
            else:
                st.info("능력치 데이터가 없습니다.")

        # 장비
        with tab2:
            st.subheader("장착 장비")

            equipment_list = equipment.get("item_equipment", [])

            if equipment_list:
                for item in equipment_list:
                    item_name = item.get("item_name", "-")
                    item_icon = item.get("item_icon")
                    item_description = item.get("item_description", "")

                    with st.container(border=True):
                        col1, col2 = st.columns([1, 5])

                        with col1:
                            if item_icon:
                                st.image(item_icon, width=70)

                        with col2:
                            st.markdown(f"### {item_name}")
                            if item_description:
                                st.caption(item_description)
            else:
                st.info("장비 데이터가 없습니다.")

        # 심볼
        with tab3:
            st.subheader("심볼 정보")

            symbol_list = symbols.get("symbol", [])

            if symbol_list:
                for symbol in symbol_list:
                    with st.container(border=True):
                        st.write(
                            f"**{symbol.get('symbol_name', '-')}**"
                        )
                        st.write(
                            f"레벨: {symbol.get('symbol_level', '-')}"
                        )
                        st.write(
                            f"힘: {symbol.get('symbol_force', '-')}"
                        )
            else:
                st.info("심볼 데이터가 없습니다.")

        # 유니온
        with tab4:
            st.subheader("유니온 정보")

            if union_error:
                st.warning(
                    f"유니온 정보를 불러오지 못했습니다: "
                    f"{union_error.user_message}"
                )
            else:
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("유니온 레벨", union.get("union_level", "-"))

                with col2:
                    st.metric("유니온 등급", union.get("union_grade", "-"))

                with col3:
                    st.metric(
                        "공격대원 수",
                        len(union.get("union_raider", [])),
                    )
    # ...existing code...

    except NexonApiError as error:
        st.error(f"API 오류: {error.user_message}")

        if error.error_code:
            st.caption(f"오류 코드: {error.error_code}")
        if error.status_code:
            st.caption(f"HTTP 상태 코드: {error.status_code}")

    except ValueError as error:
        st.warning(str(error))