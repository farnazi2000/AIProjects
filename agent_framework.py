"""Small CLI entry point for the Incident AI LangGraph workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from incident_ai.graph import build_investigation_graph
from incident_ai.ingestion import read_submission
from incident_ai.repository import IncidentRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an incident investigation")
    parser.add_argument("incident", nargs="?", help="Incident text or email content")
    parser.add_argument("--file", type=Path, help="Path to a .pdf or .txt incident submission")
    parser.add_argument("--source", default="text", choices=["text", "email", "pdf"])
    parser.add_argument("--db", default="data/incidents.db", help="Path to the SQLite database")
    parser.add_argument("--seed-demo", action="store_true", help="Add example incidents, evidence, and runbooks")
    parser.add_argument("--list", action="store_true", help="List incident IDs and summary fields")
    parser.add_argument("--show", type=int, metavar="ID", help="Show one incident, its history, and evidence")
    parser.add_argument("--add-evidence", type=int, metavar="ID", help="Attach evidence to an incident ID")
    parser.add_argument("--evidence-source", default="manual", help="Evidence source label")
    parser.add_argument("--evidence-content", help="Evidence content to store")
    args = parser.parse_args()

    repository = IncidentRepository(Path(args.db))
    if args.seed_demo:
        repository.seed_demo_data()
        print("Demo data added. Run with --list to view incident IDs.")
        return
    if args.list:
        print(json.dumps(repository.list_incidents(), indent=2))
        return
    if args.show is not None:
        record = repository.get_incident(args.show)
        if record is None:
            parser.error(f"incident ID {args.show} does not exist")
        print(json.dumps(record, indent=2))
        return
    if args.add_evidence is not None:
        if not args.evidence_content:
            parser.error("--evidence-content is required with --add-evidence")
        if repository.get_incident(args.add_evidence) is None:
            parser.error(f"incident ID {args.add_evidence} does not exist")
        repository.add_evidence(args.add_evidence, args.evidence_source, args.evidence_content)
        print(f"Evidence stored for incident ID {args.add_evidence}.")
        return
    if bool(args.incident) == bool(args.file):
        parser.error("provide exactly one incident argument or --file")

    graph = build_investigation_graph(repository)
    raw_input, source_type = read_submission(args.incident, args.file, args.source)
    result = graph.invoke({"raw_input": raw_input, "source_type": source_type})
    print(result["report"])


if __name__ == "__main__":
    main()
