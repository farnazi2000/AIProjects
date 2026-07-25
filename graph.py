from __future__ import annotations

import hashlib
import re
from typing import Literal

from langgraph.graph import END, START, StateGraph

from .llm import LLMClient
from .models import InvestigationState
from .repository import IncidentRepository
from .tools import IncidentTools


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def build_investigation_graph(repository: IncidentRepository):
    tools, llm = IncidentTools(repository), LLMClient()

    def intake(state: InvestigationState) -> dict:
        raw = state["raw_input"]
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        title = lines[0][:140] if lines else "Untitled incident"
        normalized = _normalize(raw)
        severity = next((level for level in ("critical", "high", "medium", "low") if level in normalized), "unknown")
        system_match = re.search(r"(?:system|service|application)\s*[:=-]\s*([^\n,.]+)", raw, re.I)
        system_name = system_match.group(1).strip() if system_match else "unclassified"
        fingerprint = hashlib.sha256(normalized.encode()).hexdigest()
        return {"incident": {"title": title, "severity": severity, "system_name": system_name, "details": raw, "fingerprint": fingerprint}}

    def lookup(state: InvestigationState) -> dict:
        existing = tools.incident_lookup(state["incident"]["fingerprint"])
        return {"is_existing": existing is not None, "incident_id": existing["id"] if existing else None}

    def route_incident(state: InvestigationState) -> Literal["existing", "new"]:
        return "existing" if state["is_existing"] else "new"

    def create(state: InvestigationState) -> dict:
        return {"incident_id": tools.create_incident_record(state["incident"]), "iteration": 0}

    def get_history(state: InvestigationState) -> dict:
        return {"history": tools.retrieve_history(state["incident_id"]), "iteration": state.get("iteration", 0)}

    def plan(state: InvestigationState) -> dict:
        incident = state["incident"]
        prompt = f"Incident: {incident['title']} on {incident['system_name']}. Plan evidence, history, knowledge and similar-case checks."
        llm.complete("You are an investigation planner.", prompt)
        return {"plan": ["Retrieve direct evidence", "Review incident history", "Search operational knowledge", "Compare similar incidents"]}

    def retrieve(state: InvestigationState) -> dict:
        incident = state["incident"]
        return {
            "evidence": tools.retrieve_evidence(state["incident_id"]),
            "knowledge": tools.search_knowledge(incident["system_name"]),
            "similar_cases": tools.search_similar_cases(incident["system_name"], state["incident_id"]),
        }

    def analyze(state: InvestigationState) -> dict:
        missing: list[str] = []
        if not state.get("evidence"):
            missing.append("Attach logs, screenshots, or monitoring evidence.")
        if state["incident"]["severity"] == "unknown":
            missing.append("Confirm business impact and severity.")
        summary = llm.complete("You are a cautious incident analyst.", f"Analyze: {state['incident']['details'][:2000]}")
        return {"analysis": summary, "missing_information": missing}

    def needs_more_information(state: InvestigationState) -> Literal["retrieve", "report"]:
        # One retrieval pass keeps automated executions bounded; callers can add evidence and rerun.
        return "retrieve" if state["missing_information"] and state.get("iteration", 0) < 1 else "report"

    def increment_iteration(state: InvestigationState) -> dict:
        return {"iteration": state.get("iteration", 0) + 1}

    def report(state: InvestigationState) -> dict:
        incident = state["incident"]
        report_text = "\n".join([
            f"# Investigation Report: {incident['title']}",
            f"- Incident ID: {state['incident_id']}",
            f"- Severity: {incident['severity']}",
            f"- System: {incident['system_name']}",
            "", "## Analysis", state["analysis"], "", "## Evidence", str(state.get("evidence", [])),
            "", "## Similar Cases", str(state.get("similar_cases", [])),
            "", "## Information Needed", "\n".join(f"- {item}" for item in state.get("missing_information", [])) or "- None",
        ])
        tools.persist_report(state["incident_id"], report_text)
        return {"report": report_text}
    # each node in the graph is a function that is the core of the agents reasoning and actions. 
    # The edges define the flow of the investigation process, with conditional edges allowing for branching based on the state of the investigation. (basically what node to go next)
    workflow = StateGraph(InvestigationState)
    workflow.add_node("intake", intake)
    workflow.add_node("lookup", lookup)
    workflow.add_node("create", create)
    workflow.add_node("history", get_history)
    workflow.add_node("plan", plan)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("analyze", analyze)
    workflow.add_node("increment", increment_iteration)
    workflow.add_node("report", report)
    workflow.add_edge(START, "intake")
    workflow.add_edge("intake", "lookup")
    workflow.add_conditional_edges("lookup", route_incident, {"existing": "history", "new": "create"})
    workflow.add_edge("create", "history")
    workflow.add_edge("history", "plan")
    workflow.add_edge("plan", "retrieve")
    workflow.add_edge("retrieve", "analyze")
    workflow.add_conditional_edges("analyze", needs_more_information, {"retrieve": "increment", "report": "report"})
    workflow.add_edge("increment", "retrieve")
    workflow.add_edge("report", END)
    return workflow.compile()
