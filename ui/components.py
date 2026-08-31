"""
UI Styling, Charts, and Reusable Widgets for Portfolio Analytics Dashboard.
"""

from typing import Any
from uuid import uuid4
import contextlib
import pandas as pd
import plotly.express as px
import streamlit as st

@contextlib.contextmanager
def custom_spinner(text: str):
    """A pure CSS animated spinner that won't freeze when Streamlit blocks the event loop."""
    spinner_html = f"""
    <style>
    .custom-spinner {{
        border: 3px solid #1E293B;
        border-top: 3px solid #2563EB;
        border-radius: 50%;
        width: 18px;
        height: 18px;
        animation: spin 1s linear infinite;
        display: inline-block;
    }}
    @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    </style>
    <div style="display: flex; align-items: center; gap: 12px; color: #94A3B8; font-size: 0.9rem; padding: 10px 0;">
        <div class="custom-spinner"></div>
        <span>{text}</span>
    </div>
    """
    loader = st.empty()
    loader.markdown(spinner_html, unsafe_allow_html=True)
    try:
        yield
    finally:
        loader.empty()

ELEGANT_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Clean Header */
    .app-title {
        font-size: 1.55rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        color: #F8FAFC;
        margin-bottom: 0.15rem;
    }
    .app-subtitle {
        font-size: 0.88rem;
        color: #94A3B8;
        margin-bottom: 1.25rem;
    }

    /* Sidebar Rectangular Cards */
    .sidebar-card {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 0.8rem 0.95rem;
        margin-bottom: 0.75rem;
    }
    .card-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.86rem;
        font-weight: 600;
        color: #F8FAFC;
        margin-bottom: 0.35rem;
    }
    .card-subtext {
        font-size: 0.78rem;
        color: #94A3B8;
        line-height: 1.4;
    }
    .card-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.8rem;
    }
    .card-label {
        color: #94A3B8;
        font-weight: 500;
    }
    .card-val {
        color: #F8FAFC;
        font-weight: 600;
    }
    .status-dot-green {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10B981;
        box-shadow: 0 0 8px rgba(16, 185, 129, 0.7);
        display: inline-block;
    }
    .status-dot-red {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #EF4444;
        box-shadow: 0 0 8px rgba(239, 68, 68, 0.7);
        display: inline-block;
    }

    /* Tool & Latency Badge */
    .chat-meta-footer {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        margin-top: 0.75rem;
        padding-right: 0.1rem;
        width: 100%;
    }
    .chat-meta-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-size: 0.73rem;
        font-weight: 500;
        color: #94A3B8;
        background: #1E293B;
        border: 1px solid #334155;
    }
    .chat-meta-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #3B82F6;
        display: inline-block;
    }

    /* Quick Question Buttons - Equal Shape & Size */
    div[data-testid="column"] div.stButton > button {
        width: 100% !important;
        min-height: 58px !important;
        height: 58px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        line-height: 1.3 !important;
        border-radius: 10px !important;
        background: #1E293B !important;
        border: 1px solid #334155 !important;
        color: #E2E8F0 !important;
        padding: 0.5rem 0.75rem !important;
        transition: all 0.15s ease-in-out !important;
    }
    div[data-testid="column"] div.stButton > button:hover {
        border-color: #3B82F6 !important;
        background: #1E3A8A !important;
        color: #FFFFFF !important;
    }
</style>
"""


def render_exposure_charts(exposure_data: Any, title: str = "Sector Breakdown") -> None:
    """Render sleek Plotly charts for sector exposures."""
    if not exposure_data:
        return

    # Handle multi-portfolio list (e.g. from hybrid multi-portfolio queries)
    if isinstance(exposure_data, dict):
        p_list = exposure_data.get("portfolios")
        if not p_list and isinstance(exposure_data.get("result"), dict):
            p_list = exposure_data["result"].get("portfolios")
        if isinstance(p_list, list) and p_list:
            for p in p_list:
                p_name = p.get("portfolio_name", "Portfolio")
                p_exps = p.get("exposures", [])
                if p_exps:
                    st.markdown(f"**{p_name}**")
                    render_exposure_charts(p_exps, title=p_name)
            return

    rows: list[dict[str, Any]] = []

    # Unwrap nested exposures if present
    if isinstance(exposure_data, dict):
        if "exposures" in exposure_data:
            exposure_data = exposure_data["exposures"]
        elif "result" in exposure_data and isinstance(exposure_data["result"], dict) and "exposures" in exposure_data["result"]:
            exposure_data = exposure_data["result"]["exposures"]

    if isinstance(exposure_data, list):
        for item in exposure_data:
            if isinstance(item, dict):
                sector = item.get("sector") or item.get("Sector")
                pct = item.get("exposure_pct") or item.get("exposure") or item.get("weight") or item.get("percentage")
                if sector and pct is not None:
                    try:
                        val = float(pct)
                        if val > 0:
                            rows.append({"Sector": str(sector), "Exposure (%)": val})
                    except (ValueError, TypeError):
                        pass

    elif isinstance(exposure_data, dict):
        for k, v in exposure_data.items():
            try:
                val = float(v)
                if val > 0:
                    rows.append({"Sector": str(k), "Exposure (%)": val})
            except (ValueError, TypeError):
                pass

    if not rows or sum(r["Exposure (%)"] for r in rows) <= 0:
        return

    df = pd.DataFrame(rows).sort_values(by="Exposure (%)", ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        fig_pie = px.pie(
            df,
            names="Sector",
            values="Exposure (%)",
            hole=0.45,
            title=f"🍩 {title}",
            color_discrete_sequence=px.colors.qualitative.Prism,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(
            margin=dict(t=35, b=10, l=10, r=10),
            showlegend=False,
            height=280,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#F8FAFC"),
        )
        st.plotly_chart(fig_pie, key=f"pie_{title}_{uuid4().hex[:8]}")

    with col2:
        fig_bar = px.bar(
            df.sort_values(by="Exposure (%)", ascending=True),
            x="Exposure (%)",
            y="Sector",
            orientation="h",
            title=f"📊 {title} Distribution",
            text="Exposure (%)",
            color="Exposure (%)",
            color_continuous_scale="Blues",
        )
        fig_bar.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_bar.update_layout(
            margin=dict(t=35, b=10, l=10, r=10),
            coloraxis_showscale=False,
            height=280,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#F8FAFC"),
            xaxis=dict(range=[0, max(df["Exposure (%)"].max() * 1.25, 10)], showgrid=False),
            yaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig_bar, key=f"bar_{title}_{uuid4().hex[:8]}")


def render_tool_chip_footer(tool_name: str, latency_ms: float) -> None:
    """Render clean tool & latency badge at the bottom right of the assistant bubble."""
    tool_icons = {
        "sql_query": "🔍 SQL Query",
        "exposure_calculator": "📊 Exposure Calculator",
        "hybrid_exposure_tool": "⚡ Hybrid Tool",
        "conversational": "💬 Conversational",
    }
    label = tool_icons.get(tool_name, tool_name)
    latency_str = f"{latency_ms / 1000:.2f}s" if latency_ms >= 1000 else f"{latency_ms:.0f}ms"

    st.markdown(
        f"""
        <div class="chat-meta-footer">
            <div class="chat-meta-badge">
                <span class="chat-meta-dot"></span>
                <span>{label}</span>
                <span>&bull;</span>
                <span>{latency_str}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
