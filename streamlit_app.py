"""
Portfolio Analytics AI Agent — Streamlit Web Dashboard Entry Point.
"""

import os
import streamlit as st

from ui.api_client import AsyncAPIClient
from ui.components import ELEGANT_CSS
from ui.views import (
    render_benchmark_view,
    render_chat_view,
    render_explorer_view,
    render_sidebar,
)

# 1. Page Configuration & Theme
st.set_page_config(
    page_title="Portfolio AI Copilot",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(ELEGANT_CSS, unsafe_allow_html=True)

# 2. Initialize API Client & Render Sidebar
default_api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
api_base_url = st.sidebar.text_input("API URL", value=default_api_url, label_visibility="collapsed")
api_client = AsyncAPIClient(api_base_url)

is_online, health_info = render_sidebar(api_client)

# 3. Main Header & Mode Selector
col_header, col_mode = st.columns([3, 2], vertical_alignment="bottom")

with col_header:
    st.markdown('<div class="app-title">💼 Portfolio Analytics AI Copilot</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">Natural language queries, SQL execution & sector exposure metrics</div>', unsafe_allow_html=True)

with col_mode:
    selected_mode = st.selectbox(
        "Workspace View",
        [
            "💬 AI Query Agent (Chat)",
            "📊 Sector Exposure Explorer",
            "🧪 Evaluation Benchmark Suite",
        ],
        index=0,
        label_visibility="collapsed",
    )

st.markdown("---")

# 4. Route to Selected View
if selected_mode == "💬 AI Query Agent (Chat)":
    render_chat_view(api_client)
elif selected_mode == "📊 Sector Exposure Explorer":
    render_explorer_view(api_client)
elif selected_mode == "🧪 Evaluation Benchmark Suite":
    render_benchmark_view(api_client)
