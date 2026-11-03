"""
Pages too slow to build inside a request (TEAM_VENUE_PLAN.md: a cold venue page is 20-30 seconds, Heroku cuts a request
at 30). A cache miss starts the build on a background thread and raises PageBuilding at once; the site shows the page's
skeleton and asks again (the API answers 503 with Retry-After). One build at a time per web process, as the player
cards: several at once starved the database pool on 29 Oct 2026. Finished pages go to the query cache, and to a small
in-process store so a page still arrives when the query cache is off (local development).
"""
from __future__ import annotations

import json
import logging
import threading
from collections import OrderedDict
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)

_SLOT = threading.BoundedSemaphore(1)
_LOCK = threading.Lock()
_BUILDING: set = set()
_DONE: "OrderedDict[str, Any]" = OrderedDict()
_DONE_MAX = 64


class PageBuilding(RuntimeError):
    """The page is being built; ask again in a few seconds."""


def _key_str(key: Dict[str, Any]) -> str:
    return json.dumps(key, sort_keys=True, default=str)


def _build(key: Dict[str, Any], build: Callable[[Any], Any]) -> None:
    from database import SessionLocal
    from services.query_cache import cached_run

    ks = _key_str(key)
    db = SessionLocal()
    try:
        with _SLOT:
            result = cached_run(db, key, lambda: build(db))
        with _LOCK:
            _DONE[ks] = result
            while len(_DONE) > _DONE_MAX:
                _DONE.popitem(last=False)
    except Exception:  # pragma: no cover - logged; the next request starts a fresh build
        logger.exception("page build failed: %s", ks)
    finally:
        db.close()
        with _LOCK:
            _BUILDING.discard(ks)


def get_or_build(db, key: Dict[str, Any], build: Callable[[Any], Any], wait: bool = False) -> Any:
    """The cached page, or start building it (PageBuilding). wait=True builds inline (the nightly warm job)."""
    from services.query_cache import cached_get, cached_run

    hit = cached_get(db, key)
    if hit is not None:
        return hit
    ks = _key_str(key)
    with _LOCK:
        if ks in _DONE:
            return _DONE[ks]
    if wait:
        with _SLOT:
            return cached_run(db, key, lambda: build(db))
    db.rollback()  # give the request's connection back while the build runs
    with _LOCK:
        if ks not in _BUILDING:
            _BUILDING.add(ks)
            threading.Thread(target=_build, args=(key, build), daemon=True).start()
    raise PageBuilding(ks)
