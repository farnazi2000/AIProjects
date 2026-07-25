"""Streamlit command centre for the Incident AI LangGraph workflow."""

from __future__ import annotations

from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any

import streamlit as st
from pypdf import PdfReader

from incident_ai.graph import build_investigation_graph
from incident_ai.repository import IncidentRepository


DATABASE_PATH = Path("data/incidents.db")


@st.cache_resource
def services() -> tuple[IncidentRepository, object]:
    repository = IncidentRepository(DATABASE_PATH)
    return repository, build_investigation_graph(repository)


def read_upload(uploaded_file) -> tuple[str, str]:
    """Return extracted content and the matching source type for a Streamlit upload."""
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".pdf":
        content = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(uploaded_file.getvalue())).pages).strip()
        if not content:
            raise ValueError("This PDF has no extractable text. Run OCR on scanned PDFs before uploading.")
        return content, "pdf"
    return uploaded_file.getvalue().decode("utf-8"), "text"


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
        :root { --ink:#eef5ff; --muted:#8d9ab0; --panel:#121c2d; --panel2:#17243a; --line:#25354e; --blue:#63b3ff; --cyan:#43e1cf; --orange:#ffb45b; --red:#ff6b7a; }
        .stApp { background: radial-gradient(circle at 78% -8%, #1a4565 0, transparent 30%), #09111e; color:var(--ink); font-family:'Manrope',sans-serif; }
        #MainMenu, footer, header { visibility:hidden; }
        .block-container { max-width: 1440px; padding: 1.25rem 2.8rem 3.5rem; }
        [data-testid="stSidebar"] { background:#0c1524; border-right:1px solid var(--line); }
        [data-testid="stSidebar"] > div:first-child { padding:1.4rem 1rem; }
        h1,h2,h3 { color:var(--ink)!important; font-family:'Manrope',sans-serif!important; letter-spacing:-.035em; }
        h2 { font-size:1.35rem!important; margin-top:.35rem!important; }
        p, label, .stMarkdown { color:#c6d2e2; }
        [data-testid="stMetric"] { background:linear-gradient(145deg,rgba(28,44,67,.96),rgba(16,27,44,.96)); border:1px solid var(--line); border-radius:12px; padding:1rem; }
        [data-testid="stMetricLabel"] { color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; }
        [data-testid="stMetricValue"] { color:var(--ink); font-size:1.5rem; }
        .stButton > button { border-radius:8px; border:1px solid #355777; background:#1b314a; color:var(--ink); font-weight:700; min-height:2.55rem; }
        .stButton > button[kind="primary"] { background:linear-gradient(110deg,#2e8bef,#42b4e6); border:0; box-shadow:0 7px 22px rgba(42,139,239,.22); }
        .stTextArea textarea, .stTextInput input, [data-baseweb="select"] > div { background:#0d1727!important; border-color:#31445d!important; color:var(--ink)!important; border-radius:8px!important; }
        .stTabs [data-baseweb="tab-list"] { gap:1.5rem; border-bottom:1px solid var(--line); }
        .stTabs [data-baseweb="tab"] { color:var(--muted); font-weight:700; padding:.75rem .1rem; }
        .stTabs [aria-selected="true"] { color:#80c8ff!important; border-bottom-color:#64b7ff!important; }
        [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:10px; overflow:hidden; }
        .hero { padding:1.7rem 0 1.6rem; border-bottom:1px solid var(--line); margin-bottom:1.3rem; }
        .eyebrow { color:var(--cyan); font-family:'DM Mono',monospace; font-size:.7rem; font-weight:500; letter-spacing:.13em; text-transform:uppercase; }
        .hero h1 { font-size:2.1rem!important; margin:.32rem 0!important; }
        .hero p { color:var(--muted); margin:0; max-width:690px; }
        .brand { display:flex; gap:.65rem; align-items:center; margin:0 .35rem 1.6rem; font-weight:800; color:#eef5ff; letter-spacing:-.03em; }
        .brand-mark { display:grid; place-items:center; width:30px; height:30px; border-radius:8px; background:linear-gradient(135deg,#50b5ff,#506bff); box-shadow:0 0 20px rgba(80,181,255,.35); }
        .side-label { color:#71829a; font-size:.66rem; font-family:'DM Mono',monospace; text-transform:uppercase; letter-spacing:.12em; margin:1.4rem .35rem .55rem; }
        .sidebar-note { background:#111e31; border:1px solid var(--line); border-radius:10px; padding:.85rem; color:var(--muted); font-size:.76rem; line-height:1.55; margin-top:1rem; }
        .section-card { background:linear-gradient(135deg,rgba(22,35,55,.94),rgba(13,23,39,.94)); border:1px solid var(--line); border-radius:13px; padding:1.2rem 1.25rem; margin:.5rem 0 1rem; }
        .section-title { color:#eef5ff; font-weight:800; font-size:1rem; margin-bottom:.15rem; }
        .section-copy { color:var(--muted); font-size:.84rem; margin-bottom:1rem; }
        .badge { display:inline-block; padding:.23rem .55rem; border-radius:999px; font-family:'DM Mono',monospace; font-size:.67rem; font-weight:500; letter-spacing:.04em; text-transform:uppercase; }
        .badge-open { background:#193c50; color:#79d7ff; }.badge-resolved { background:#183d37; color:#72e5cb; }.badge-critical { background:#542333; color:#ff8b99; }.badge-high { background:#55361f; color:#ffc276; }.badge-medium { background:#273957; color:#94c8ff; }.badge-low { background:#293c37; color:#a0d8ba; }
        .incident-heading { display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; margin:.2rem 0 1.1rem; }.incident-heading h3 { margin:0!important; font-size:1.35rem!important; }.incident-meta { color:var(--muted); font-family:'DM Mono',monospace; font-size:.72rem; margin-top:.35rem; }
        .timeline { border-left:1px solid #34516d; margin:.5rem 0 .2rem .35rem; padding-left:1.15rem; }.timeline-item { position:relative; padding:0 0 1.1rem; }.timeline-item:before { content:''; position:absolute; width:8px; height:8px; border-radius:50%; background:var(--cyan); left:-1.42rem; top:.34rem; box-shadow:0 0 0 4px #142539; }.timeline-type { color:#84c9ff; text-transform:uppercase; font:500 .65rem 'DM Mono',monospace; letter-spacing:.08em; }.timeline-note { color:#d8e3ef; font-size:.85rem; margin:.22rem 0; }.timeline-date { color:var(--muted); font-size:.7rem; }
        .report-box { background:#0d1726; border:1px solid #2f5e79; border-radius:12px; padding:1.2rem; margin-top:1rem; }
        .empty-state { text-align:center; color:var(--muted); padding:2.4rem 1rem; border:1px dashed #30445d; border-radius:12px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def badge(value: str, prefix: str = "") -> str:
    clean = value.lower().replace(" ", "-")
    return f'<span class="badge badge-{escape(clean)}">{escape(prefix)}{escape(value)}</span>'


def readable_time(value: str) -> str:
    return value.replace("T", " ").replace("+00:00", " UTC") if value else "—"


def show_report(report: str) -> None:
    st.markdown('<div class="report-box"><div class="section-title">Generated investigation report</div>', unsafe_allow_html=True)
    st.markdown(report)
    st.markdown("</div>", unsafe_allow_html=True)
    st.download_button("Download report (.md)", report, file_name="investigation-report.md", mime="text/markdown")


def show_timeline(history: list[dict[str, Any]]) -> None:
    if not history:
        st.caption("No events recorded yet.")
        return
    rows = "".join(
        f'<div class="timeline-item"><div class="timeline-type">{escape(item["event_type"])}</div><div class="timeline-note">{escape(item["note"])}</div><div class="timeline-date">{escape(readable_time(item["created_at"]))}</div></div>'
        for item in history
    )
    st.markdown(f'<div class="timeline">{rows}</div>', unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title="Incident Command", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
    inject_styles()
    repository, graph = services()
    counts = repository.table_counts()
    incidents = repository.list_incidents()
    open_count = sum(item["status"].lower() != "resolved" for item in incidents)
    critical_count = sum(item["severity"].lower() == "critical" for item in incidents)

    with st.sidebar:
        st.markdown('<div class="brand"><div class="brand-mark">◈</div><div>incident<span style="color:#65b9ff">.ai</span></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="side-label">Operations</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="Name"> Developed by: Farnaz Mozhgani</div>'
            '<hr style="margin-top: 10px; margin-bottom: 10px; border: none; height: 1px; background-color: rgba(150, 150, 150, 0.2);">',
            unsafe_allow_html=True,
        )
        st.markdown("**Investigation command center**")
        st.caption("AI-assisted triage, evidence collection, and incident reporting.")
        st.markdown('<div class="side-label">Workspace</div>', unsafe_allow_html=True)
        st.metric("Tracked incidents", counts["incidents"])
        st.metric("Evidence items", counts["evidence"])
        if st.button("Load demo workspace", use_container_width=True):
            repository.seed_demo_data()
            st.rerun()
        st.markdown('<div class="sidebar-note">Local workspace<br><span style="color:#b9c9dc">SQLite · LangGraph workflow</span><br><span style="color:#70839b">' + str(DATABASE_PATH) + "</span></div>", unsafe_allow_html=True)

    st.markdown(
        """<div class="hero"><div class="eyebrow">Operations / Investigation workspace</div><h1>Incident command center</h1><p>Bring signals, evidence, and institutional knowledge together to investigate production issues with confidence.</p></div>""",
        unsafe_allow_html=True,
    )
    metric_cols = st.columns(4)
    metric_cols[0].metric("Total incidents", counts["incidents"])
    metric_cols[1].metric("Active investigations", open_count)
    metric_cols[2].metric("Critical severity", critical_count)
    metric_cols[3].metric("Evidence collected", counts["evidence"])

    investigate_tab, incidents_tab, knowledge_tab = st.tabs(["Start investigation", "Incident queue", "Runbooks & knowledge"])

    with investigate_tab:
        left, right = st.columns([1.55, .9], gap="large")
        with left:
            st.markdown('<div class="section-card"><div class="section-title">Open a new investigation</div><div class="section-copy">Submit an alert, incident note, email body, or text-based PDF. The investigation workflow checks for related records before creating a case.</div>', unsafe_allow_html=True)
            text_input = st.text_area("Incident narrative", height=220, placeholder="Title\n, Severity\n, System\n, Details\n\nExample: Payments API — critical — checkout requests timing out after the 10:30 deployment. Error rate is 18% and increasing…")
            input_cols = st.columns(2)
            with input_cols[0]:
                source_type = st.selectbox("Source type", ["text", "email"], help="PDF is detected automatically for PDF uploads.")
            with input_cols[1]:
                uploaded_file = st.file_uploader("Attach PDF or TXT", type=["pdf", "txt"], label_visibility="visible")
            start = st.button("Start AI investigation", type="primary", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            if start:
                if text_input.strip() and uploaded_file is not None:
                    st.error("Use either pasted content or an attachment, not both.")
                elif not text_input.strip() and uploaded_file is None:
                    st.error("Add incident details or upload a file to begin.")
                else:
                    try:
                        raw_input, actual_source = read_upload(uploaded_file) if uploaded_file else (text_input.strip(), source_type)
                        with st.spinner("Checking history, retrieving evidence, and building the investigation report…"):
                            result = graph.invoke({"raw_input": raw_input, "source_type": actual_source})
                        st.session_state["last_report"] = result["report"]
                        st.session_state["last_incident_id"] = result["incident_id"]
                    except (ValueError, UnicodeDecodeError) as error:
                        st.error(str(error))
                    except Exception as error:
                        st.error(f"The investigation could not complete: {error}")
            if report := st.session_state.get("last_report"):
                st.success(f"Investigation saved to case #{st.session_state['last_incident_id']}.")
                show_report(report)
        with right:
            st.markdown('<div class="section-card"><div class="section-title">Investigation workflow</div><div class="section-copy">Every submission follows a documented review path.</div>', unsafe_allow_html=True)
            for number, title, copy in [("01", "Parse & normalize", "Extract system, severity, and incident context."), ("02", "Find related signals", "Search prior incidents, evidence, and runbooks."), ("03", "Analyze & report", "Create an evidence-backed investigation summary.")]:
                st.markdown(f'<div style="display:flex;gap:.75rem;margin:0 0 1rem"><span class="badge badge-medium">{number}</span><div><div style="color:#e9f2ff;font-weight:700;font-size:.85rem">{title}</div><div style="color:#8d9ab0;font-size:.76rem;margin-top:.15rem">{copy}</div></div></div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            if incidents:
                st.markdown('<div class="section-card"><div class="section-title">Latest activity</div>', unsafe_allow_html=True)
                for item in incidents[:4]:
                    st.markdown(f'<div style="padding:.5rem 0;border-bottom:1px solid #24364e"><div style="display:flex;justify-content:space-between;gap:.4rem"><span style="color:#dce9f7;font-size:.8rem;font-weight:700">#{item["id"]} · {escape(item["title"])}</span>{badge(item["severity"])}</div><div class="incident-meta">{escape(item["system_name"])} · {escape(readable_time(item["created_at"]))}</div></div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

    with incidents_tab:
        st.markdown('<div class="section-card"><div class="section-title">Incident queue</div><div class="section-copy">Review stored cases, timelines, evidence, and the full operational context.</div>', unsafe_allow_html=True)
        if not incidents:
            st.markdown('<div class="empty-state">No incidents in this workspace yet.<br>Load the demo workspace or start a new investigation.</div>', unsafe_allow_html=True)
        else:
            queue_rows = [{"ID": f"#{item['id']}", "Title": item["title"], "Severity": item["severity"].upper(), "System": item["system_name"], "Status": item["status"].upper(), "Opened": readable_time(item["created_at"])} for item in incidents]
            st.dataframe(queue_rows, use_container_width=True, hide_index=True, column_config={"ID": st.column_config.TextColumn(width="small"), "Title": st.column_config.TextColumn(width="large")})
            selected_id = st.selectbox("Open incident", [record["id"] for record in incidents], format_func=lambda incident_id: f"#{incident_id} — {next(item['title'] for item in incidents if item['id'] == incident_id)}")
            incident = repository.get_incident(selected_id)
            if incident:
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown(f'<div class="incident-heading"><div><h3>{escape(incident["title"])}</h3><div class="incident-meta">CASE #{incident["id"]} · {escape(incident["system_name"])} · OPENED {escape(readable_time(incident["created_at"]))}</div></div><div>{badge(incident["severity"])} {badge(incident["status"])}</div></div>', unsafe_allow_html=True)
                details_col, context_col = st.columns([1.3, 1], gap="large")
                with details_col:
                    st.markdown('<div class="section-card"><div class="section-title">Incident narrative</div>', unsafe_allow_html=True)
                    st.write(incident["details"])
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown('<div class="section-card"><div class="section-title">Case timeline</div>', unsafe_allow_html=True)
                    show_timeline(incident["history"])
                    st.markdown("</div>", unsafe_allow_html=True)
                with context_col:
                    st.markdown(f'<div class="section-card"><div class="section-title">Evidence locker <span style="color:#7f91a8;font-weight:500">({len(incident["evidence"])})</span></div>', unsafe_allow_html=True)
                    if incident["evidence"]:
                        for evidence in incident["evidence"]:
                            st.markdown(f'<div style="padding:.65rem 0;border-bottom:1px solid #263952"><div class="timeline-type">{escape(evidence["source"])}</div><div style="color:#d5e1ed;font-size:.8rem;margin:.25rem 0">{escape(evidence["content"])}</div><div class="timeline-date">{escape(readable_time(evidence["created_at"]))}</div></div>', unsafe_allow_html=True)
                    else:
                        st.caption("No evidence stored for this case.")
                    st.markdown("</div>", unsafe_allow_html=True)
                    with st.expander("+ Add evidence to this case"):
                        with st.form(f"evidence-{selected_id}"):
                            evidence_source = st.text_input("Source", placeholder="Datadog, application logs, customer support")
                            evidence_content = st.text_area("Evidence", placeholder="Relevant log, metric, or observation")
                            if st.form_submit_button("Store evidence", type="primary"):
                                if not evidence_source.strip() or not evidence_content.strip():
                                    st.error("Both source and evidence are required.")
                                else:
                                    repository.add_evidence(selected_id, evidence_source.strip(), evidence_content.strip())
                                    st.rerun()

    with knowledge_tab:
        st.markdown('<div class="section-card"><div class="section-title">Operational knowledge base</div><div class="section-copy">Runbooks are included in the investigation workflow when they are relevant to the submitted incident.</div>', unsafe_allow_html=True)
        knowledge = repository.list_knowledge()
        if knowledge:
            for entry in knowledge:
                tags = " · ".join(tag.strip() for tag in entry["tags"].split(",") if tag.strip())
                with st.expander(f"{entry['title']}  ·  {tags}"):
                    st.write(entry["content"])
        else:
            st.markdown('<div class="empty-state">No runbooks available. Load the demo workspace to populate operational knowledge.</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
