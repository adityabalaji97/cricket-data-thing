"""
Best-effort usage logging (tables from migration 004): MCP tool calls and website events, plus the
outcome of natural-language query runs (nl_query_log, migration 023).

Writes never run on the request path: callers enqueue a row and a single daemon thread
batch-inserts it. If the database is slow or the tables are missing, rows are dropped (and
counted in the log) rather than slowing or failing a request -- usage numbers are for trends,
not accounting. The queue is bounded so a flood cannot grow memory.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import queue
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("hindsight.usage")

_QUEUE: "queue.Queue[tuple]" = queue.Queue(maxsize=5000)
_WORKER: Optional[threading.Thread] = None
_LOCK = threading.Lock()
_BATCH = 200
_FLUSH_SECONDS = 2.0

_INSERTS = {
    "mcp": (
        "INSERT INTO mcp_call_log (tool, outcome, ms, client, caller_hash, session_hash, is_owner, args) "
        "VALUES (%(tool)s, %(outcome)s, %(ms)s, %(client)s, %(caller_hash)s, %(session_hash)s, %(is_owner)s, %(args)s)"
    ),
    "jev": (
        "INSERT INTO jev_usage_log (source, questions, input_tokens, output_tokens, ms, ok) "
        "VALUES (%(source)s, %(questions)s, %(input_tokens)s, %(output_tokens)s, %(ms)s, %(ok)s)"
    ),
    # Not an insert: the outcome of a parsed natural-language question, onto its nl_query_log row
    # (nl2query.record_nl_run). The first run's outcome is kept; re-runs only count.
    "nl_run": (
        "UPDATE nl_query_log SET run_count = run_count + 1, "
        "run_status = COALESCE(run_status, %(status)s), "
        "run_error = CASE WHEN run_status IS NULL THEN %(error)s ELSE run_error END, "
        "run_ms = CASE WHEN run_status IS NULL THEN %(ms)s ELSE run_ms END, "
        "run_at = CASE WHEN run_status IS NULL THEN now() ELSE run_at END, "
        "execution_success = CASE WHEN run_status IS NULL THEN %(ok)s ELSE execution_success END, "
        "result_row_count = CASE WHEN run_status IS NULL THEN COALESCE(%(rows)s, result_row_count) "
        "ELSE result_row_count END "
        "WHERE log_ref = %(log_ref)s"
    ),
    "event": (
        "INSERT INTO app_events (anon_id, session_id, event, path, props, referrer, country) "
        "VALUES (%(anon_id)s, %(session_id)s, %(event)s, %(path)s, %(props)s, %(referrer)s, %(country)s)"
    ),
}


def _hash(value: str) -> str:
    salt = os.environ.get("USAGE_HASH_SALT", "hindsight")
    return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()[:16]


def caller_hash(forwarded_for: Optional[str]) -> Optional[str]:
    """Short salted hash of the first X-Forwarded-For hop. Counts addresses, not people: every claude.ai call comes
    from Anthropic's servers. session_hash is the one to count conversations by."""
    if not forwarded_for:
        return None
    return _hash(forwarded_for.split(",")[0].strip())


def session_hash(session_id: Optional[str]) -> Optional[str]:
    """Short salted hash of the connector's Mcp-Session-Id: one per conversation (a client opens a session when it
    connects), identifies no one."""
    return _hash(session_id.strip()) if session_id and session_id.strip() else None


def _ensure_worker() -> None:
    global _WORKER
    if _WORKER and _WORKER.is_alive():
        return
    with _LOCK:
        if _WORKER and _WORKER.is_alive():
            return
        _WORKER = threading.Thread(target=_run, name="usage-log", daemon=True)
        _WORKER.start()
        import atexit

        atexit.register(flush)


def enqueue(kind: str, row: Dict[str, Any]) -> None:
    if os.environ.get("USAGE_LOGGING", "1") == "0":
        return
    try:
        _QUEUE.put_nowait((kind, row))
    except queue.Full:
        logger.warning("usage log queue full; dropping %s row", kind)
        return
    _ensure_worker()


def log_jev_call(questions: int, input_tokens: Optional[int], output_tokens: Optional[int], ms: int, ok: bool) -> None:
    """One Jev call (services/jev_client.ask), tagged with the process that made it."""
    import sys

    argv0 = os.path.basename(sys.argv[0] or "") if sys.argv else ""
    source = "web" if argv0 in ("uvicorn", "gunicorn", "") or "uvicorn" in argv0 else argv0
    enqueue("jev", {"source": source[:64], "questions": questions, "input_tokens": input_tokens,
                    "output_tokens": output_tokens, "ms": ms, "ok": ok})


def log_mcp_call(tool: str, outcome: str, ms: int, client: str, forwarded_for: Optional[str], args: Dict[str, Any],
                 session_id: Optional[str] = None, is_owner: bool = False) -> None:
    enqueue("mcp", {
        "tool": tool[:48], "outcome": outcome[:16], "ms": ms, "client": (client or "")[:80],
        "caller_hash": caller_hash(forwarded_for), "session_hash": session_hash(session_id), "is_owner": bool(is_owner),
        "args": json.dumps(args, default=str),
    })


def _write(batch) -> None:
    from database import engine

    try:
        raw = engine.raw_connection()
        try:
            cur = raw.cursor()
            for kind in _INSERTS:
                rows = [row for k, row in batch if k == kind]
                if rows:
                    cur.executemany(_INSERTS[kind], rows)
            raw.commit()
        finally:
            raw.close()
    except Exception as exc:  # never let logging take anything down
        logger.warning("usage log write failed (%s rows dropped): %r", len(batch), exc)


def flush() -> None:
    """Write whatever is queued now: at exit, so a short script (a nightly job) doesn't lose its last rows."""
    batch = []
    while True:
        try:
            batch.append(_QUEUE.get_nowait())
        except queue.Empty:
            break
    if batch:
        _write(batch)


def _run() -> None:
    while True:
        batch = []
        deadline = time.monotonic() + _FLUSH_SECONDS
        while len(batch) < _BATCH:
            try:
                batch.append(_QUEUE.get(timeout=max(0.05, deadline - time.monotonic())))
            except queue.Empty:
                break
        if batch:
            _write(batch)
