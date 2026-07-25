from __future__ import annotations

from typing import Any, TypedDict


class InvestigationState(TypedDict, total=False):
    raw_input: str
    source_type: str
    incident: dict[str, Any]
    incident_id: int
    is_existing: bool
    history: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    knowledge: list[dict[str, Any]]
    similar_cases: list[dict[str, Any]]
    plan: list[str]
    analysis: str
    missing_information: list[str]
    iteration: int
    report: str
