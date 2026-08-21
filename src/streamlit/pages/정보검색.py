import os
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

# app.py와 nexon_client.py가 같은 폴더에 있음
STREAMLIT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(STREAMLIT_DIR))

from nexon_client import NexonApiError, NexonClient

# ===================
# 캐릭터 정보 검색
# ===================
api_key = st.secrets.get["NEXON_API_KEY"]

if not api_key:
    st.error("NEXON API KEY가 설정되지 않았습니다.")
    st.stop()

client = NexonClient(api_key=api_key)


character_name = input("캐릭터명을 입력하세요: ").strip()

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
        # 2. OCID로 기본 정보 조회
        # ==============================================

        basic = client.get_basic(ocid)

        # ==============================================
        # 3. 조회 성공 결과
        # ==============================================

        print("\n===== 조회 성공 =====")

        print("캐릭터명:", basic.get("character_name"))

        print("월드:", basic.get("world_name"))

        print("직업:", basic.get("character_class"))

        print("레벨:", basic.get("character_level"))

    except NexonApiError as e:
        print(f"API KEY가 등록되지 않았습니다 ({e})")