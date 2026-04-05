"""
AgentDNA Registry — SQLite Storage Layer

Replaces in-memory dicts with persistent SQLite storage.
Drop-in replacement: same API, survives restarts.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _get_registry_db_path() -> Path:
    """Get path to the registry SQLite database."""
    custom = os.environ.get("AGENTDNA_REGISTRY_DB_PATH")
    if custom:
        return Path(custom)
    return Path.home() / ".agentdna" / "registry.db"


def _get_conn() -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode."""
    path = _get_registry_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def _init_db(conn: sqlite3.Connection):
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            agent_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            registered_at TEXT NOT NULL,
            last_heartbeat TEXT,
            online INTEGER DEFAULT 1,
            verified INTEGER DEFAULT 0,
            total_submitted INTEGER DEFAULT 0,
            total_completed INTEGER DEFAULT 0,
            total_failed INTEGER DEFAULT 0,
            total_timed_out INTEGER DEFAULT 0,
            tasks_within_sla INTEGER DEFAULT 0,
            total_tasks_with_timing INTEGER DEFAULT 0,
            promised_latency_seconds REAL DEFAULT 0,
            uptime_checks INTEGER DEFAULT 0,
            uptime_successes INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT NOT NULL,
            task_id TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        );

        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        );

        CREATE TABLE IF NOT EXISTS verification_reports (
            agent_id TEXT PRIMARY KEY,
            report TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        );

        CREATE INDEX IF NOT EXISTS idx_reviews_agent ON reviews(agent_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent_id);
    """)


# --- Agent CRUD ---

def save_agent(agent_id: str, agent_data: dict) -> None:
    """Insert or update an agent."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO agents (agent_id, data, registered_at, last_heartbeat, online)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(agent_id) DO UPDATE SET
                data = excluded.data,
                last_heartbeat = excluded.last_heartbeat,
                online = 1
        """, (agent_id, json.dumps(agent_data), now, now))
        conn.commit()
    finally:
        conn.close()


def get_agent(agent_id: str) -> Optional[dict]:
    """Get an agent by ID."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT data FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
        if row:
            return json.loads(row["data"])
        return None
    finally:
        conn.close()


def list_agents(limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
    """List all agents with pagination."""
    conn = _get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        rows = conn.execute(
            "SELECT data FROM agents ORDER BY registered_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        return [json.loads(r["data"]) for r in rows], total
    finally:
        conn.close()


def get_all_agents() -> dict[str, dict]:
    """Get all agents as a dict (for search filtering)."""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT agent_id, data FROM agents").fetchall()
        return {r["agent_id"]: json.loads(r["data"]) for r in rows}
    finally:
        conn.close()


def update_heartbeat(agent_id: str) -> bool:
    """Update agent heartbeat. Returns False if agent not found."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "UPDATE agents SET last_heartbeat = ?, online = 1 WHERE agent_id = ?",
            (now, agent_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def set_verified(agent_id: str, verified: bool) -> None:
    """Update agent verification status."""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE agents SET verified = ? WHERE agent_id = ?",
            (1 if verified else 0, agent_id)
        )
        conn.commit()
    finally:
        conn.close()


# --- Reviews ---

def save_review(agent_id: str, review: dict) -> None:
    """Save a review for an agent."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO reviews (agent_id, rating, comment, task_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_id, review["rating"], review["comment"],
              review.get("task_id"), now))
        conn.commit()
    finally:
        conn.close()


def get_reviews(agent_id: str) -> list[dict]:
    """Get all reviews for an agent."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT rating, comment, task_id, created_at FROM reviews WHERE agent_id = ? ORDER BY created_at DESC",
            (agent_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# --- Tasks ---

def save_task(task_id: str, agent_id: str, task_data: dict) -> None:
    """Save a task."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO tasks (task_id, agent_id, data, created_at)
            VALUES (?, ?, ?, ?)
        """, (task_id, agent_id, json.dumps(task_data), now))
        conn.commit()
    finally:
        conn.close()


def get_task(task_id: str) -> Optional[dict]:
    """Get a task by ID."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT data FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if row:
            return json.loads(row["data"])
        return None
    finally:
        conn.close()


# --- Verification Reports ---

def save_verification_report(agent_id: str, report: dict) -> None:
    """Save a verification report."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO verification_reports (agent_id, report, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(agent_id) DO UPDATE SET
                report = excluded.report,
                updated_at = excluded.updated_at
        """, (agent_id, json.dumps(report), now))
        conn.commit()
    finally:
        conn.close()


def get_verification_report(agent_id: str) -> Optional[dict]:
    """Get the latest verification report for an agent."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT report FROM verification_reports WHERE agent_id = ?",
            (agent_id,)
        ).fetchone()
        if row:
            return json.loads(row["report"])
        return None
    finally:
        conn.close()


# --- Aggregate Stats ---

def get_registry_stats() -> dict:
    """Get overall registry statistics."""
    conn = _get_conn()
    try:
        agents = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        reviews = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        verified = conn.execute("SELECT COUNT(*) FROM agents WHERE verified = 1").fetchone()[0]
        online = conn.execute("SELECT COUNT(*) FROM agents WHERE online = 1").fetchone()[0]
        return {
            "agents_registered": agents,
            "agents_verified": verified,
            "agents_online": online,
            "tasks_created": tasks,
            "reviews_submitted": reviews,
        }
    finally:
        conn.close()
