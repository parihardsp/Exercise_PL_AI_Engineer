"""
Application Views (Chat Copilot, Sector Exposure Explorer, Benchmark Suite) for Streamlit UI.
"""

from datetime import datetime
import time
from typing import Any
from uuid import uuid4

import markdown as _md
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from tests.evaluator import json_to_markdown
from ui.api_client import AsyncAPIClient, run_async
from ui.components import render_exposure_charts, custom_spinner


PORTFOLIOS = [
    "Tech Innovation Fund",
    "Growth Equity Fund",
    "Balanced Portfolio",
    "ESG Sustainable Fund",
    "Conservative Income Fund",
    "Small Cap Value Fund",
    "International Equity Fund",
    "Dividend Aristocrats Fund",
    "Emerging Markets Fund",
    "Total Stock Market Index Fund",
    "Total International Index Fund",
    "Total Bond Market Index Fund",
]

TOOL_ICONS = {
    "sql_query": "🔍 SQL Query",
    "exposure_calculator": "📊 Exposure",
    "hybrid_exposure_tool": "⚡ Hybrid",
    "conversational": "💬 Conversational",
}


def render_sidebar(api_client: AsyncAPIClient) -> tuple[bool, dict[str, Any]]:
    """Render the sidebar status cards and active tools."""
    health = run_async(api_client.check_health())
    is_online = health.get("status") == "healthy"

    # Card 1: Backend & Model Status
    if is_online:
        model_name = health.get("model_name", "N/A")
        st.sidebar.markdown(
            f"""
            <div class="sidebar-card">
                <div class="card-header">
                    <span class="status-dot-green"></span>
                    <span>Backend Online</span>
                </div>
                <div class="card-subtext">
                    <b>Model:</b> {model_name}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            """
            <div class="sidebar-card">
                <div class="card-header">
                    <span class="status-dot-red"></span>
                    <span>Backend Offline</span>
                </div>
                <div class="card-subtext">
                    Run <code>python -m api.app</code> on port 8000
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Card 2: Database & Tracing Stats
    if is_online:
        tables_count = health.get("database_tables", 9)
        tracing_status = "Active" if health.get("langsmith_tracing") else "Off"
        st.sidebar.markdown(
            f"""
            <div class="sidebar-card">
                <div class="card-row">
                    <span class="card-label">Database</span>
                    <span class="card-val">{tables_count} tables</span>
                </div>
                <div class="card-row" style="margin-top: 0.4rem;">
                    <span class="card-label">LangSmith</span>
                    <span class="card-val" style="color: {'#10B981' if tracing_status == 'Active' else '#94A3B8'};">{tracing_status}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Card 3: Active Tools Collapsible
    tools_list = run_async(api_client.fetch_tools()) if is_online else []
    if tools_list:
        with st.sidebar.expander("🛠️ Active Tools", expanded=False):
            for tool in tools_list:
                st.markdown(f"**`{tool['name']}`**")
                st.caption(tool["description"].strip()[:100] + "...")

    st.sidebar.markdown("---")
    st.sidebar.caption("Portfolio Analytics AI Copilot")
    return is_online, health


# --- 1. View 1: AI Query Agent (Chat) ---
def render_chat_view(api_client: AsyncAPIClient) -> None:
    """Render the Interactive AI Copilot Chat view."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"user_{uuid4().hex[:8]}"

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Hello! I am your **Portfolio Analytics Assistant**. "
                    "Ask me any question regarding your portfolios, holdings, benchmarks, or sector exposure."
                ),
                "tool": "conversational",
                "time_ms": 120.0,
                "tool_result": None,
                "timestamp": datetime.now().strftime("%I:%M:%S %p"),
            }
        ]

    # Quick prompt chips
    st.markdown(
        "<div style='font-size: 0.85rem; font-weight: 600; color: #94A3B8; margin-bottom: 0.5rem;'>⚡ Quick Questions</div>",
        unsafe_allow_html=True,
    )
    sample_queries = [
        "How many portfolios do we have in total?",
        "What is sector exposure for Balanced Fund?",
        "Which portfolios have High target risk?",
        "Top 3 portfolios sector exposure?",
    ]

    cols = st.columns(len(sample_queries))
    selected_sample = None
    for idx, prompt_text in enumerate(sample_queries):
        if cols[idx].button(prompt_text, key=f"chip_{idx}"):
            selected_sample = prompt_text

    st.write("")

    def _bubble(
        role: str,
        content: str,
        tool: str = "",
        t_ms: float = 0.0,
        timestamp: str = "",
    ) -> None:
        is_user = role == "user"
        bg = "#0D1F3C" if is_user else "#0F172A"
        border = "#2563EB" if is_user else "#334155"
        color = "#DBEAFE" if is_user else "#E2E8F0"
        av_bg = "#1E3A5F" if is_user else "#1E293B"
        av_brd = "#2563EB" if is_user else "#475569"
        avatar = "🧑‍💼" if is_user else "🤖"
        lbl = "You" if is_user else "AI Agent"
        t_str = timestamp if timestamp else datetime.now().strftime("%I:%M:%S %p")

        time_badge = (
            f'<span style="display:inline-flex;align-items:center;gap:4px;'
            f'padding:2px 8px;border-radius:12px;font-size:0.68rem;font-weight:500;'
            f'color:#94A3B8;background:#1E293B;border:1px solid #334155;">'
            f'🕒 {t_str}</span>'
        )

        if not is_user and tool:
            lat = f"{t_ms/1000:.2f}s" if t_ms >= 1000 else f"{t_ms:.0f}ms"
            icon = TOOL_ICONS.get(tool, tool)
            badge = (
                f'<div style="display:flex;justify-content:flex-end;margin-top:8px;">'
                f'<span style="display:inline-flex;align-items:center;gap:6px;'
                f'padding:3px 10px;border-radius:20px;font-size:0.72rem;font-weight:500;'
                f'color:#94A3B8;background:#1E293B;border:1px solid #334155;">'
                f'{icon} &bull; {lat}</span></div>'
            )
        else:
            badge = ""

        html_content = _md.markdown(
            content.strip(),
            extensions=["nl2br", "tables", "fenced_code"],
        )

        card_html = (
            f'<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:10px;">'
            f'<div style="font-size:1.5rem;width:38px;min-width:38px;height:38px;'
            f'display:flex;align-items:center;justify-content:center;border-radius:50%;'
            f'background:{av_bg};border:1px solid {av_brd};">{avatar}</div>'
            f'<div style="flex:1;background:{bg};border:1px solid {border};'
            f'border-radius:10px;padding:8px 14px;color:{color};font-size:0.88rem;line-height:1.5;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
            f'<div style="font-size:0.72rem;font-weight:600;color:#94A3B8;">{lbl}</div>'
            f'{time_badge}'
            f'</div>'
            f'<div>{html_content}</div>'
            f'{badge}'
            f'</div>'
            f'</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

    for msg in st.session_state.messages:
        _bubble(
            msg["role"],
            msg["content"],
            msg.get("tool", ""),
            msg.get("time_ms", 0.0),
            msg.get("timestamp", ""),
        )
        if msg["role"] == "assistant":
            tool_res = msg.get("tool_result")
            if msg.get("tool") in {"exposure_calculator", "hybrid_exposure_tool"} and tool_res:
                _, chart_area = st.columns([1, 17])
                with chart_area:
                    render_exposure_charts(tool_res, title="Sector Exposure")

    user_input = st.chat_input("Ask a question about portfolios...")
    query_to_send = selected_sample if selected_sample else user_input

    if query_to_send:
        user_now_str = datetime.now().strftime("%I:%M:%S %p")
        st.session_state.messages.append({
            "role": "user",
            "content": query_to_send,
            "timestamp": user_now_str,
        })
        _bubble("user", query_to_send, timestamp=user_now_str)

        with custom_spinner("Generating... (this may take a while)"):
            start_time = time.time()
            res = run_async(api_client.query(query_to_send, session_id=st.session_state.session_id))
            elapsed_ms = res.get("execution_time_ms", (time.time() - start_time) * 1000)
            content = res.get("answer") or res.get("response") or "No response received."
            tool_used = res.get("tool_name") or "conversational"
            tool_result = res.get("tool_result")

        asst_now_str = datetime.now().strftime("%I:%M:%S %p")
        _bubble("assistant", content, tool_used, elapsed_ms, timestamp=asst_now_str)

        if tool_used in {"exposure_calculator", "hybrid_exposure_tool"} and tool_result:
            _, chart_area = st.columns([1, 17])
            with chart_area:
                render_exposure_charts(tool_result, title="Sector Exposure")

        st.session_state.messages.append({
            "role": "assistant",
            "content": content,
            "tool": tool_used,
            "time_ms": elapsed_ms,
            "tool_result": tool_result,
            "timestamp": asst_now_str,
        })


# --- 2. View 2: Sector Exposure Explorer ---
def render_explorer_view(api_client: AsyncAPIClient) -> None:
    """Render the Sector Exposure Explorer & side-by-side comparison."""
    st.markdown("#### 📊 Sector Exposure Explorer")
    st.caption("Analyse and compare equity sector breakdowns across portfolios.")

    def _fetch_exposure(portfolio_name: str) -> tuple[dict | None, str, float]:
        res = run_async(api_client.query(f"What are the sector exposures for {portfolio_name}?"))
        return (res.get("tool_result"), str(res.get("answer", "")), float(res.get("execution_time_ms", 0.0)))

    def _latency_badge(lat_ms: float, label: str = "📊 Exposure Calculator") -> None:
        lat_str = f"{lat_ms/1000:.2f}s" if lat_ms >= 1000 else f"{lat_ms:.0f}ms"
        st.markdown(
            f"""<div style="display:flex;justify-content:flex-end;margin-bottom:10px;">
                <span style="display:inline-flex;align-items:center;gap:6px;
                    padding:3px 12px;border-radius:20px;font-size:0.74rem;
                    font-weight:500;color:#94A3B8;background:#1E293B;border:1px solid #334155;">
                    {label} &bull; {lat_str}
                </span></div>""",
            unsafe_allow_html=True,
        )

    tab_single, tab_compare = st.tabs(["🔍 Single Portfolio", "⚖️ Compare Two Portfolios"])

    with tab_single:
        col_sel, col_btn = st.columns([3, 1], vertical_alignment="bottom")
        with col_sel:
            selected_portfolio = st.selectbox("Choose Portfolio", PORTFOLIOS, index=0, key="single_sel")
        with col_btn:
            run_single = st.button("Calculate", type="primary", key="single_btn")

        if run_single:
            with custom_spinner(f"Generating exposures for {selected_portfolio}..."):
                tool_result, answer, lat_ms = _fetch_exposure(selected_portfolio)
            _latency_badge(lat_ms)
            st.markdown(answer)
            if tool_result:
                render_exposure_charts(tool_result, title=selected_portfolio)
            elif answer:
                st.info(answer)

    with tab_compare:
        c1, c2, c3 = st.columns([5, 5, 2], vertical_alignment="bottom")
        with c1:
            port_a = st.selectbox("Portfolio A", PORTFOLIOS, index=0, key="cmp_a")
        with c2:
            port_b = st.selectbox("Portfolio B", PORTFOLIOS, index=1, key="cmp_b")
        with c3:
            run_compare = st.button("Compare", type="primary", key="cmp_btn")

        if run_compare:
            if port_a == port_b:
                st.warning("Please select two different portfolios to compare.")
            else:
                with custom_spinner(f"Generating exposures for both portfolios concurrently..."):
                    res_a, res_b = run_async(api_client.fetch_both_exposures(port_a, port_b))
                    tr_a, ans_a, lat_a = (res_a.get("tool_result"), str(res_a.get("answer", "")), float(res_a.get("execution_time_ms", 0.0)))
                    tr_b, ans_b, lat_b = (res_b.get("tool_result"), str(res_b.get("answer", "")), float(res_b.get("execution_time_ms", 0.0)))

                _latency_badge(lat_a + lat_b, f"⚖️ {port_a} vs {port_b}")
                st.write("")

                def _extract_rows(tool_res) -> list[dict]:
                    if not tool_res:
                        return []
                    data = tool_res
                    if isinstance(data, dict):
                        data = data.get("exposures") or data.get("result", {})
                        if isinstance(data, dict):
                            data = data.get("exposures", [])
                    rows = []
                    for item in (data if isinstance(data, list) else []):
                        if isinstance(item, dict):
                            s = item.get("sector") or item.get("Sector")
                            v = item.get("exposure_pct") or item.get("exposure") or item.get("weight")
                            if s and v is not None:
                                try:
                                    rows.append({"Sector": str(s), "Exposure (%)": float(v)})
                                except (ValueError, TypeError):
                                    pass
                    return rows

                rows_a = _extract_rows(tr_a)
                rows_b = _extract_rows(tr_b)

                if rows_a or rows_b:
                    col_a, col_b = st.columns(2)
                    COLORS = px.colors.qualitative.Prism

                    for col, rows, name, ans in [(col_a, rows_a, port_a, ans_a), (col_b, rows_b, port_b, ans_b)]:
                        with col:
                            st.markdown(f"**{name}**")
                            if rows:
                                df = pd.DataFrame(rows).sort_values("Exposure (%)", ascending=False)
                                fig = px.pie(df, names="Sector", values="Exposure (%)", hole=0.42,
                                             color_discrete_sequence=COLORS)
                                fig.update_traces(textposition="inside", textinfo="percent+label")
                                fig.update_layout(showlegend=False, height=280, margin=dict(t=10,b=10,l=10,r=10),
                                                  paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#F8FAFC"))
                                st.plotly_chart(fig, width='stretch', key=f"cmp_pie_{name}_{uuid4().hex[:8]}")
                            else:
                                st.info(ans or "No equity exposure data found.")

                    st.write("")
                    st.markdown("##### 📊 Side-by-Side Sector Comparison")

                    if rows_a and rows_b:
                        df_a = pd.DataFrame(rows_a).rename(columns={"Exposure (%)": port_a})
                        df_b = pd.DataFrame(rows_b).rename(columns={"Exposure (%)": port_b})
                        df_merged = pd.merge(df_a, df_b, on="Sector", how="outer").fillna(0)
                        df_melted = df_merged.melt(id_vars="Sector", var_name="Portfolio", value_name="Exposure (%)")

                        FLOOR = 0.8
                        df_melted["Label"] = df_melted["Exposure (%)"].apply(lambda v: f"{v:.1f}%")
                        df_melted["Display"] = df_melted["Exposure (%)"].apply(lambda v: max(v, FLOOR))

                        portfolios_order = [port_a, port_b]
                        bar_colors = ["#3B82F6", "#10B981"]

                        fig_bar = go.Figure()
                        for i, (pname, color) in enumerate(zip(portfolios_order, bar_colors)):
                            subset = df_melted[df_melted["Portfolio"] == pname]
                            fig_bar.add_trace(go.Bar(
                                name=pname,
                                x=subset["Sector"],
                                y=subset["Display"],
                                text=subset["Label"],
                                textposition="outside",
                                textfont=dict(size=12, color="#F8FAFC"),
                                marker=dict(
                                    color=color,
                                    opacity=0.85,
                                    line=dict(color="#F8FAFC", width=1.2),
                                ),
                                hovertemplate="%{x}<br>%{text}<extra>" + pname + "</extra>",
                            ))

                        fig_bar.update_layout(
                            font=dict(color="#F8FAFC"), legend=dict(orientation="h", yanchor="bottom", y=1.02),
                            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, title="Exposure (%)"),
                            margin=dict(t=30, b=10, l=10, r=10),
                        )
                        st.plotly_chart(fig_bar, width='stretch', key=f"cmp_bar_{uuid4().hex[:8]}")
                else:
                    st.warning("Could not retrieve exposure data for one or both portfolios.")


# --- 3. View 3: Evaluation Benchmark Suite ---
def render_benchmark_view(api_client: AsyncAPIClient) -> None:
    """Render the Benchmark Evaluation tab."""
    st.markdown("#### 🧪 Benchmark Evaluation Suite")
    st.caption("Automated testing against the official ground truth Q&A dataset.")

    if st.button("▶️ Run Evaluation Suite (12 Questions)", type="primary"):
        with custom_spinner("Generating evaluation benchmark across all test cases..."):
            eval_data = run_async(api_client.run_benchmark())

            if "error" in eval_data:
                st.error(eval_data["error"])
            else:
                st.success("Benchmark completed!")

                # Minimalist Scorecards
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Questions", eval_data.get("total_questions", 0))
                c2.metric("Routing Accuracy", f"{eval_data.get('correct_routing_pct', 0):.0f}%")
                c3.metric("SQL Similarity", f"{eval_data.get('sql_similarity_pct', 100):.0f}%")
                c4.metric("Result Match", f"{eval_data.get('correct_matches_pct', 0):.0f}%")
                c5.metric("Avg Latency", f"{eval_data.get('avg_latency_seconds', 0):.2f}s")

                results = eval_data.get("results", [])
                if results:
                    st.write("")
                    df_results = pd.DataFrame(results)
                    if "sql_similarity_pct" in df_results.columns:
                        df_results["sql_similarity_pct"] = df_results["sql_similarity_pct"].apply(
                            lambda v: f"{v:.0f}%" if pd.notnull(v) else "100%"
                        )
                    display_cols = [
                        "id",
                        "question",
                        "expected_tool",
                        "actual_tool",
                        "routing_correct",
                        "sql_similarity_pct",
                        "result_correct",
                        "latency_seconds",
                    ]
                    available_cols = [c for c in display_cols if c in df_results.columns]
                    st.dataframe(
                        df_results[available_cols].rename(
                            columns={
                                "id": "ID",
                                "question": "Question",
                                "expected_tool": "Expected Tool",
                                "actual_tool": "Actual Tool",
                                "routing_correct": "Tool Match",
                                "sql_similarity_pct": "SQL Similarity",
                                "result_correct": "Data Match",
                                "latency_seconds": "Latency (s)",
                            }
                        ),
                        hide_index=True,
                    )

                    try:
                        md_text = json_to_markdown(eval_data)
                        st.write("")
                        st.download_button(
                            label="📥 Download Full Evaluation Report (EVALUATION_REPORT.md)",
                            data=md_text,
                            file_name="EVALUATION_REPORT.md",
                            mime="text/markdown",
                        )
                    except Exception as err:
                        st.warning(f"Could not prepare Markdown export: {err}")
