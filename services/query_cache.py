"""
Persistent cache for query-builder results (table query_cache, migration 009).

Keyed by sha256(normalized query params + data_version). The nightly load bumps
app_meta.data_version, so new data invalidates every cached result without a sweep; old versions
are pruned by prune(). Shared by the website, the connector and embeds, and it survives restarts.

The cache must never break a query: any error reading or writing it falls through to running the
query. Results are stored exactly as FastAPI would serialize them (jsonable_encoder), so a cache
hit returns the same JSON a fresh run would.
"""
import hashlib
import json
import logging
import os
import time
from datetime import date, datetime
from typing import Any, Callable, Dict, Optional

from fastapi.encoders import jsonable_encoder
from sqlalchemy import text

logger = logging.getLogger(__name__)

MAX_RESULT_BYTES = 1_000_000
_VERSION_TTL_SECONDS = 300
_version_cache: Dict[str, Any] = {"value": None, "at": 0.0}


def enabled() -> bool:
    return os.getenv("QUERY_CACHE", "1") != "0"


def data_version(db) -> str:
    now = time.time()
    if _version_cache["value"] and now - _version_cache["at"] < _VERSION_TTL_SECONDS:
        return _version_cache["value"]
    try:
        value = db.execute(text("SELECT value FROM app_meta WHERE key = 'data_version'")).scalar() or "0"
    except Exception:
        db.rollback()
        value = "0"
    _version_cache.update(value=value, at=now)
    return value


def normalize(params: Dict[str, Any]) -> Dict[str, Any]:
    """Drop empty values, sort lists, stringify dates: equal queries get equal keys."""
    out = {}
    for key, value in params.items():
        if value is None or value == [] or value == "":
            continue
        if isinstance(value, (date, datetime)):
            value = value.isoformat()
        elif isinstance(value, (list, tuple)):
            value = sorted(str(v) for v in value) if key != "group_by" else [str(v) for v in value]
        out[key] = value
    return out


def cache_key(params: Dict[str, Any], version: str) -> str:
    payload = json.dumps({"v": version, "p": normalize(params)}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def cached_run(db, params: Dict[str, Any], run: Callable[[], Any]) -> Any:
    if not enabled():
        return run()
    try:
        version = data_version(db)
        key = cache_key(params, version)
        row = db.execute(text("SELECT result FROM query_cache WHERE key = :k"), {"k": key}).first()
        if row is not None and isinstance(row[0], dict):
            _write("UPDATE query_cache SET hits = hits + 1 WHERE key = :k", {"k": key})
            return row[0]
    except Exception as exc:
        logger.warning("query cache read failed: %r", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return run()

    result = run()
    try:
        encoded = jsonable_encoder(result)
        blob = json.dumps(encoded)
        if len(blob) <= MAX_RESULT_BYTES:
            _write("""
                INSERT INTO query_cache (key, params, result, data_version)
                VALUES (:k, CAST(:p AS jsonb), CAST(:r AS json), :v)
                ON CONFLICT (key) DO NOTHING
            """, {"k": key, "p": json.dumps(normalize(params), default=str), "r": blob, "v": version})
        return encoded
    except Exception as exc:
        logger.warning("query cache encode failed: %r", exc)
        return result


def _write(sql: str, params: Dict[str, Any]) -> None:
    """Cache writes use their own short transaction: callers may hold a read-only session (the
    connector does), and a failed write must never disturb the caller's transaction."""
    try:
        from database import engine

        with engine.begin() as conn:
            conn.execute(text(sql), params)
    except Exception as exc:
        logger.warning("query cache write failed: %r", exc)


def bump_data_version(db) -> str:
    """Called after the nightly load: every cached result is stale from here on."""
    value = datetime.utcnow().strftime("%Y-%m-%dT%H:%M")
    db.execute(text("""
        INSERT INTO app_meta (key, value, updated_at) VALUES ('data_version', :v, now())
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
    """), {"v": value})
    db.commit()
    _version_cache.update(value=None, at=0.0)
    return value


def prune(db, keep_versions: int = 1) -> int:
    """Delete cached results from older data versions."""
    current = data_version(db)
    result = db.execute(text("DELETE FROM query_cache WHERE data_version <> :v"), {"v": current})
    db.commit()
    return result.rowcount or 0
