"""
Best-effort usage logging (tables from migration 004): MCP tool calls and website events.

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
        "INSERT INTO mcp_call_log (tool, outcome, ms, client, caller_hash, args) "
        "VALUES (%(tool)s, %(outcome)s, %(ms)s, %(client)s, %(caller_hash)s, %(args)s)"
    ),
    "jev": (
        "INSERT INTO jev_usage_log (source, questions, input_tokens, output_tokens, ms, ok) "
        "VALUES (%(source)s, %(questions)s, %(input_tokens)s, %(output_tokens)s, %(ms)s, %(ok)s)"
    ),
    "event": (
        "INSERT INTO app_events (anon_id, session_id, event, path, props, referrer, country) "
        "VALUES (%(anon_id)s, %(session_id)s, %(event)s, %(path)s, %(props)s, %(referrer)s, %(country)s)"
    ),
}


def caller_hash(forwarded_for: Optional[str]) -> Optional[str]:
    """Short salted hash of the first X-Forwarded-For hop: counts distinct callers, identifies no one."""
    if not forwarded_for:
        return None
    first = forwarded_for.split(",")[0].strip()
    salt = os.environ.get("USAGE_HASH_SALT", "hindsight")
    return hashlib.sha256(f"{salt}:{first}".encode()).hexdigest()[:16]


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


def log_mcp_call(tool: str, outcome: str, ms: int, client: str, forwarded_for: Optional[str], args: Dict[str, Any]) -> None:
    enqueue("mcp", {
        "tool": tool[:48], "outcome": outcome[:16], "ms": ms, "client": (client or "")[:80],
        "caller_hash": caller_hash(forwarded_for), "args": json.dumps(args, default=str),
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
