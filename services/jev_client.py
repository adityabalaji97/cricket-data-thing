"""
Thin client for TypeSafe's Jev ("System One" model): typed judgments with probabilities.

Jev never produces Hindsight's numbers. It judges text we wrote and picks between candidates
(see services/typed_preview.py). Every call is best-effort: with no TYPESAFE_API_KEY, or on any
failure, ask() returns None and the caller keeps its non-Jev behaviour.

API: https://docs.typesafe.ai/api.md
"""
import logging
import os
import time
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = os.getenv("TYPESAFE_MODEL", "jev-latest")
RETRY_STATUSES = {429, 529}


def api_key() -> Optional[str]:
    return os.getenv("TYPESAFE_API_KEY") or None


def enabled() -> bool:
    return api_key() is not None


def ask(state: Any, questions: Dict[str, Dict[str, Any]], timeout: float = 3.0) -> Optional[Dict[str, Any]]:
    """POST one fan-out request; returns the `answers` map, or None if Jev is off or failed."""
    key = api_key()
    if not key or not questions:
        return None
    payload = {"model": MODEL, "state": state, "questions": questions}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    started = time.monotonic()
    for attempt in range(2):
        try:
            response = httpx.post(API_URL, json=payload, headers=headers, timeout=timeout)
            if response.status_code in RETRY_STATUSES and attempt == 0:
                time.sleep(0.5)
                continue
            response.raise_for_status()
            body = response.json()
            usage = body.get("usage") or {}
            logger.info(
                "jev_call questions=%d ms=%d in_tokens=%s out_tokens=%s",
                len(questions), int((time.monotonic() - started) * 1000),
                usage.get("input_tokens"), usage.get("output_tokens"),
            )
            return body.get("answers") or None
        except Exception as exc:  # network, HTTP or JSON: never fail the caller
            logger.warning("jev_call failed (%s): %r", type(exc).__name__, exc)
            return None
    return None
