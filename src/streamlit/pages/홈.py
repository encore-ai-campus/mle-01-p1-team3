import os
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st


st.title("🍁 메이플스토리 스타터 유저 가이드라인")
st.caption("뉴비들을 위한 가이드라인 챗봇")