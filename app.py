"""
Streamlit frontend for the CyberSec AI Agent.

This module is pure UI: it imports all logic from `backend.py`.
Run with:  streamlit run app.py
"""

from datetime import datetime

import streamlit as st

from backend import (
    AGENT_INFO,
    LLM_MODEL,
    MissingCredentialsError,
    check_api_keys,
    md_to_pdf_bytes,
    run_pipeline,
)


# ============================================================
# PAGE CONFIG & STYLES
# ============================================================

st.set_page_config(
    page_title="CyberSec AI Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38bdf8, #a78bfa, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        backdrop-filter: blur(10px);
    }
    .metric-label {
        color: #94a3b8;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        color: #f8fafc;
        font-size: 1.6rem;
        font-weight: 700;
    }
    .report-card {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 14px;
        padding: 1.5rem 1.75rem;
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.35rem;
    }
    .badge-sky { background: rgba(56, 189, 248, 0.15); color: #7dd3fc; }
    .badge-violet { background: rgba(167, 139, 250, 0.15); color: #c4b5fd; }
    .badge-pink { background: rgba(244, 114, 182, 0.15); color: #f9a8d4; }
    .badge-emerald { background: rgba(52, 211, 153, 0.15); color: #6ee7b7; }
    .badge-amber { background: rgba(251, 191, 36, 0.15); color: #fcd34d; }
    section[data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.95);
        border-right: 1px solid rgba(148, 163, 184, 0.1);
    }
    div.stButton > button {
        background: linear-gradient(90deg, #38bdf8, #a78bfa);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: transform 0.1s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-1px);
        filter: brightness(1.1);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

st.session_state.setdefault("executive_report", None)
st.session_state.setdefault("technical_report", None)
st.session_state.setdefault("last_run", None)
st.session_state.setdefault("is_running", False)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("### 🛡️ CyberSec AI Agent")
    st.markdown("Multi-agent threat intelligence powered by CrewAI, Groq & Exa.")
    st.divider()

    st.markdown("#### Query Configuration")
    threat_query = st.text_input(
        "Threat search query",
        value="latest cybersecurity threats 2026",
        help="Query used by the Threat Intelligence Analyst agent.",
    )
    cve_query = st.text_input(
        "CVE search query",
        value="latest critical CVEs vulnerabilities 2026",
        help="Query used by the Vulnerability Researcher agent.",
    )

    st.divider()
    st.markdown("#### API Status")
    keys = check_api_keys()
    st.markdown(
        f"- Groq API: {'🟢 Connected' if keys['groq'] else '🔴 Missing'}\n"
        f"- Exa API: {'🟢 Connected' if keys['exa'] else '🔴 Missing'}"
    )

    st.divider()
    run_btn = st.button(
        "🚀 Run Full Analysis",
        use_container_width=True,
        disabled=st.session_state.is_running,
    )

    if st.session_state.last_run:
        st.caption(f"Last run: {st.session_state.last_run}")


# ============================================================
# HEADER
# ============================================================

st.markdown('<div class="main-title">🛡️ CyberSec AI Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Autonomous multi-agent pipeline for real-time threat intelligence, '
    'CVE research, and executive reporting.</div>',
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">Agents</div>'
        f'<div class="metric-value">{len(AGENT_INFO)}</div></div>',
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        '<div class="metric-card"><div class="metric-label">Tasks</div>'
        '<div class="metric-value">5</div></div>',
        unsafe_allow_html=True,
    )
with c3:
    if st.session_state.is_running:
        status = "Running"
    elif st.session_state.executive_report:
        status = "Complete"
    else:
        status = "Ready"
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">Status</div>'
        f'<div class="metric-value">{status}</div></div>',
        unsafe_allow_html=True,
    )
with c4:
    llm_label = LLM_MODEL.split("-")[0].title() + " 3.3"
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">LLM</div>'
        f'<div class="metric-value">{llm_label}</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("")

with st.expander("🤖 Meet the agents", expanded=False):
    for info in AGENT_INFO:
        st.markdown(
            f'<div style="margin-bottom:0.5rem;">'
            f'<span class="badge badge-{info["color"]}">{info["name"]}</span>'
            f'<span style="color:#cbd5e1;">{info["description"]}</span></div>',
            unsafe_allow_html=True,
        )


# ============================================================
# RUN PIPELINE
# ============================================================

if run_btn:
    if not (keys["groq"] and keys["exa"]):
        st.error("Missing API keys. Please add `GROQ_API_KEY` and `EXA_API_KEY` to your `.env` file.")
    else:
        st.session_state.is_running = True
        progress_bar = st.progress(0, text="Initializing agents...")

        def status_cb(agent_name: str, step: int) -> None:
            progress = min(step / 10, 0.95)
            progress_bar.progress(progress, text=f"Working: {agent_name}...")

        try:
            with st.spinner("🧠 Agents are collaborating... this can take a few minutes."):
                result = run_pipeline(threat_query, cve_query, status_cb=status_cb)
            st.session_state.executive_report = result.executive_report
            st.session_state.technical_report = result.technical_report
            st.session_state.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            progress_bar.progress(1.0, text="Complete")
            st.success("Analysis complete.")
        except MissingCredentialsError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Pipeline failed: {e}")
        finally:
            st.session_state.is_running = False
            st.rerun()


# ============================================================
# REPORTS
# ============================================================

def render_report(title: str, content: str | None, pdf_title: str, filename_stem: str) -> None:
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.markdown(f"### {title}")
    if content:
        st.markdown(content)
        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button(
                "⬇️ Download Markdown",
                content,
                file_name=f"{filename_stem}.md",
                mime="text/markdown",
                use_container_width=True,
                key=f"{filename_stem}_md",
            )
        with col_b:
            try:
                pdf_bytes = md_to_pdf_bytes(pdf_title, content)
                st.download_button(
                    "⬇️ Download PDF",
                    pdf_bytes,
                    file_name=f"{filename_stem}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"{filename_stem}_pdf",
                )
            except Exception as e:
                st.caption(f"PDF export unavailable: {e}")
    else:
        st.info("Run the pipeline to generate this report.")
    st.markdown("</div>", unsafe_allow_html=True)


if st.session_state.executive_report or st.session_state.technical_report:
    tab1, tab2 = st.tabs(["📊 Executive Brief", "🔧 Technical Report"])
    with tab1:
        render_report(
            "Executive Brief (C-Suite)",
            st.session_state.executive_report,
            "Executive Cybersecurity Brief",
            "executive_brief",
        )
    with tab2:
        render_report(
            "SOC Technical Report",
            st.session_state.technical_report,
            "SOC Technical Report",
            "technical_report",
        )
else:
    st.info("👈 Configure your queries in the sidebar and click **Run Full Analysis** to begin.")
