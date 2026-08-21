import os
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st


# ===================
# 분석 대시보드
# ===================
st.divider()
st.header("메이플스토리 유저 질문 분석")
