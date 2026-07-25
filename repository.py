from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class IncidentRepository:
    """SQLite storage; free, local, and simple to replace with Postgres later."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  fingerprint TEXT NOT NULL UNIQUE,
                  title TEXT NOT NULL,
                  severity TEXT NOT NULL,
                  system_name TEXT NOT NULL,
                  details TEXT NOT NULL,
                  status TEXT NOT NULL DEFAULT 'open',
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS incident_history (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  incident_id INTEGER NOT NULL REFERENCES incidents(id),
                  event_type TEXT NOT NULL,
                  note TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evidence (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  incident_id INTEGER NOT NULL REFERENCES incidents(id),
                  source TEXT NOT NULL,
                  content TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS knowledge_base (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  content TEXT NOT NULL,
                  tags TEXT NOT NULL DEFAULT ''
                );
                """
            )

    @staticmethod
    def _rows(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        return [dict(row) for row in rows]

    def find_by_fingerprint(self, fingerprint: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM incidents WHERE fingerprint = ?", (fingerprint,)).fetchone()
        return dict(row) if row else None

    def create_incident(self, incident: dict[str, Any]) -> int:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO incidents (fingerprint,title,severity,system_name,details,status,created_at)
                   VALUES (:fingerprint,:title,:severity,:system_name,:details,:status,:created_at)""",
                {**incident, "status": incident.get("status", "open"), "created_at": now},
            )
            incident_id = int(cursor.lastrowid)
            conn.execute(
                "INSERT INTO incident_history (incident_id,event_type,note,created_at) VALUES (?,?,?,?)",
                (incident_id, "created", "Incident created by Intake / Parsing Agent", now),
            )
        return incident_id

    def history(self, incident_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT event_type, note, created_at FROM incident_history WHERE incident_id=? ORDER BY id", (incident_id,)
            ).fetchall()
        return self._rows(rows)

    def evidence_for(self, incident_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT source, content, created_at FROM evidence WHERE incident_id=?", (incident_id,)).fetchall()
        return self._rows(rows)

    def add_evidence(self, incident_id: int, source: str, content: str) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO evidence (incident_id,source,content,created_at) VALUES (?,?,?,?)",
                (incident_id, source, content, now),
            )

    def add_history(self, incident_id: int, event_type: str, note: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO incident_history (incident_id,event_type,note,created_at) VALUES (?,?,?,?)",
                (incident_id, event_type, note, datetime.now(UTC).isoformat()),
            )

    def list_incidents(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, title, severity, system_name, status, created_at FROM incidents ORDER BY id DESC"
            ).fetchall()
        return self._rows(rows)

    def list_knowledge(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id, title, content, tags FROM knowledge_base ORDER BY id").fetchall()
        return self._rows(rows)

    def table_counts(self) -> dict[str, int]:
        with self._connect() as conn:
            return {
                table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in ("incidents", "incident_history", "evidence", "knowledge_base")
            }

    def get_incident(self, incident_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            incident = conn.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if incident is None:
            return None
        record = dict(incident)
        record["history"] = self.history(incident_id)
        record["evidence"] = self.evidence_for(incident_id)
        return record

    def search_knowledge(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        term = f"%{query}%"
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT title, content, tags FROM knowledge_base WHERE title LIKE ? OR content LIKE ? OR tags LIKE ? LIMIT ?",
                (term, term, term, limit),
            ).fetchall()
        return self._rows(rows)

    def similar_cases(self, system_name: str, exclude_id: int | None = None) -> list[dict[str, Any]]:
        sql = "SELECT id, title, severity, status, details, created_at FROM incidents WHERE system_name = ?"
        params: list[Any] = [system_name]
        if exclude_id is not None:
            sql += " AND id != ?"
            params.append(exclude_id)
        sql += " ORDER BY id DESC LIMIT 5"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return self._rows(rows)

    def save_report(self, incident_id: int, report: str) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO incident_history (incident_id,event_type,note,created_at) VALUES (?,?,?,?)",
                (incident_id, "report_generated", report, now),
            )

    def seed_demo_data(self) -> None:
        """Add idempotent, realistic IT/software investigation data for local development."""
        knowledge = [
            ("API and product outage triage", "Confirm customer impact, inspect the error-rate and latency dashboards, compare the last deployment, then check upstream dependencies before rollback.", "api,outage,product,rollback"),
            ("Database connection exhaustion", "Inspect connection-pool saturation, slow queries, and application connection lifetime. Scale only after ruling out a connection leak.", "database,postgres,connections,performance"),
            ("Database failover response", "Confirm primary health, replication lag, quorum status, and application connection errors. Record the failover timeline and validate writes after recovery.", "database,outage,failover,replication"),
            ("Security credential exposure", "Revoke or rotate the exposed credential, review access logs, identify the blast radius, preserve evidence, and create a post-incident follow-up.", "security,credentials,incident,response"),
            ("Deployment regression checklist", "Compare release versions and feature flags, inspect application exceptions, canary metrics, and migration status. Roll back only after preserving diagnostic data.", "deployment,release,regression,feature-flag"),
            ("Queue backlog investigation", "Measure consumer lag, failed jobs, throughput, dead-letter volume, and downstream database latency. Scale consumers only if the dependency is healthy.", "queue,workers,backlog,performance"),
            ("DNS and network incident triage", "Check DNS resolution from multiple regions, recent record changes, TLS status, load-balancer health, and provider status before modifying records.", "dns,network,availability"),
        ]
        examples = [
            {
                "key": "payments-timeout-demo", "title": "Payments API timeout after release", "severity": "high", "system": "Payments",
                "details": "Version 2026.07.18 introduced a retry configuration change. Checkout requests timed out and the API 5xx rate reached 18%.", "status": "resolved",
                "history": [("detected", "Pager alert triggered for elevated Payments API latency."), ("mitigated", "Rolled back version 2026.07.18; error rate returned to baseline."), ("resolved", "Root cause: retry fan-out overloaded the payment-provider connection pool.")],
                "evidence": [("Datadog", "payments-api p95 latency rose from 240ms to 14.2s at 10:42 UTC."), ("Deployments", "Release 2026.07.18 completed 12 minutes before the alert."), ("Application logs", "Upstream payment-provider timeout after 3 retry attempts.")],
            },
            {
                "key": "orders-db-pool-demo", "title": "Orders database connection pool exhaustion", "severity": "critical", "system": "Orders",
                "details": "Order creation slowed significantly because application workers exhausted the PostgreSQL connection pool during a traffic increase.", "status": "resolved",
                "history": [("detected", "Database saturation alert triggered."), ("investigating", "Found workers retaining idle connections after a failed transaction."), ("resolved", "Patched connection cleanup and restarted affected workers.")],
                "evidence": [("PostgreSQL metrics", "Active connections: 200/200; waiting clients: 143."), ("Slow query log", "Inventory update query exceeded 35 seconds during the event."), ("Worker logs", "Transaction rollback path did not return a connection to the pool.")],
            },
            {
                "key": "postgres-failover-demo", "title": "Customer profile database failover", "severity": "critical", "system": "Customer Profile",
                "details": "The primary database node became unavailable after storage latency increased. Read and write requests failed during automatic failover.", "status": "resolved",
                "history": [("detected", "Primary health checks failed in us-west."), ("mitigated", "Promoted the healthy replica and redirected application traffic."), ("resolved", "Storage issue cleared; replication caught up with no confirmed data loss.")],
                "evidence": [("Database monitoring", "Primary disk latency sustained above 2.8 seconds."), ("Replication dashboard", "Replica lag peaked at 47 seconds before promotion."), ("Audit log", "Automatic failover completed at 03:18 UTC.")],
            },
            {
                "key": "github-token-demo", "title": "Exposed CI deployment token detected", "severity": "high", "system": "CI/CD",
                "details": "A repository scan found a deployment token committed to a branch. The token had access to the staging deployment environment.", "status": "resolved",
                "history": [("detected", "Secret-scanning alert opened a security incident."), ("contained", "Revoked token and disabled related pipeline credentials."), ("resolved", "Access review found no suspicious staging deployments; preventive secret scanning enabled.")],
                "evidence": [("Secret scanner", "Matched a token pattern in commit 4c21a9e."), ("Identity audit", "Token used only by expected CI runner in the preceding 30 days."), ("Git history", "Credential was removed from branch and repository history remediation was scheduled.")],
            },
            {
                "key": "search-release-demo", "title": "Search results missing after feature flag rollout", "severity": "medium", "system": "Search",
                "details": "A new ranking feature flag excluded documents without a recently populated metadata field, causing some customer searches to return no results.", "status": "resolved",
                "history": [("detected", "Support reported empty search results for multiple tenants."), ("mitigated", "Disabled the ranking feature flag globally."), ("resolved", "Backfilled metadata and added a flag validation check.")],
                "evidence": [("Feature flag audit", "ranking_v2 enabled to 100% at 14:05 UTC."), ("Search metrics", "Zero-result rate increased from 3% to 29%."), ("Query samples", "Affected documents lacked last_indexed_at metadata.")],
            },
            {
                "key": "notifications-queue-demo", "title": "Notification delivery queue backlog", "severity": "medium", "system": "Notifications",
                "details": "Email and push notifications were delayed after worker throughput dropped and the queue accumulated pending jobs.", "status": "resolved",
                "history": [("detected", "Queue lag alert fired after delivery delay exceeded 15 minutes."), ("mitigated", "Increased healthy worker capacity and paused low-priority campaigns."), ("resolved", "Removed malformed payloads that caused repeated retries.")],
                "evidence": [("Queue dashboard", "Pending jobs rose from 2,000 to 1,200,000."), ("Worker metrics", "Successful jobs per minute dropped 72%."), ("Dead-letter queue", "Malformed locale payloads retried more than 20 times.")],
            },
            {
                "key": "public-api-dns-demo", "title": "Public API unavailable from two regions", "severity": "high", "system": "Public API",
                "details": "Clients in two regions could not resolve the public API hostname after a DNS record change during a traffic-routing update.", "status": "resolved",
                "history": [("detected", "Synthetic checks failed in us-east and eu-west."), ("mitigated", "Restored the prior DNS record and reduced TTL for verification."), ("resolved", "Corrected routing automation validation and added multi-region DNS checks.")],
                "evidence": [("Synthetic monitoring", "DNS resolution failed in 2 of 6 probe regions."), ("DNS provider audit", "A CNAME target was removed at 09:31 UTC."), ("Load balancer", "No unhealthy targets or elevated request failures after DNS restoration.")],
            },
        ]
        with self._connect() as conn:
            for title, content, tags in knowledge:
                exists = conn.execute("SELECT 1 FROM knowledge_base WHERE title=?", (title,)).fetchone()
                if exists is None:
                    conn.execute("INSERT INTO knowledge_base (title,content,tags) VALUES (?,?,?)", (title, content, tags))
        for example in examples:
            fingerprint = hashlib.sha256(example["key"].encode()).hexdigest()
            existing = self.find_by_fingerprint(fingerprint)
            if existing is None:
                incident_id = self.create_incident({"fingerprint": fingerprint, "title": example["title"], "severity": example["severity"], "system_name": example["system"], "details": example["details"], "status": example["status"]})
                for event_type, note in example["history"]:
                    self.add_history(incident_id, event_type, note)
                for source, content in example["evidence"]:
                    self.add_evidence(incident_id, source, content)
