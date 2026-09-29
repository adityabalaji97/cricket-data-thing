"""
Fact-check GPT-written text against the data it was written from, before users see it.

Two checks per line:
  1. Numbers, in code: every number in the line must match a number in the source data
     (to the precision shown). Small integers are allowed as over numbers and positions.
  2. Claims, by Jev (Noul): "every claim in this line is supported by the data", which catches
     misattribution a number check cannot ("33% of his RUNS" when the data says 33% of BALLS).
A line failing either is replaced by the deterministic line for the same topic (same emoji), or
dropped. Without Jev only the number check runs.
"""
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from services import jev_client

NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?")
SMALL_INTS = set(range(0, 21))  # over numbers ("overs 16-20"), batting positions
SUPPORT_THRESHOLD = 0.5


def _walk_numbers(obj: Any) -> Iterable[float]:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield float(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_numbers(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _walk_numbers(v)
    elif isinstance(obj, str):
        for m in NUMBER.findall(obj):
            yield float(m)


def numbers_supported(line: str, known: List[float]) -> Tuple[bool, List[str]]:
    bad = []
    for token in NUMBER.findall(line):
        value = float(token)
        if value.is_integer() and int(value) in SMALL_INTS:
            continue
        decimals = len(token.split(".")[1]) if "." in token else 0
        tolerance = 0.5 * 10 ** -decimals + 1e-9
        if not any(abs(value - k) <= tolerance or abs(abs(value) - abs(k)) <= tolerance for k in known):
            bad.append(token)
    return not bad, bad


def _emoji_key(line: str) -> str:
    return line.strip()[:2]


def verify_lines(text: str, data: Dict[str, Any], fallback_text: Optional[str] = None,
                 subject: str = "this player") -> Tuple[str, Dict[str, Any]]:
    lines = [l for l in (text or "").split("\n") if l.strip()]
    if not lines:
        return text, {"checked": 0}
    known = list(_walk_numbers(data))
    fallback = {_emoji_key(l): l for l in (fallback_text or "").split("\n") if l.strip()}

    number_ok = [numbers_supported(l, known) for l in lines]
    support: List[Optional[float]] = [None] * len(lines)
    if jev_client.enabled():
        state = {"subject": subject, "data": json.dumps(data, default=str)[:12000]}
        answers = jev_client.ask(state, {
            f"l{i}": {
                "type": "noul",
                "instructions": f"Is every claim in this line stated in, or directly calculated from, the data? Line: \"{line}\"",
                "criteria": {
                    "true": "All numbers and what they measure match the data (wording may differ)",
                    "false": "A number, what it measures, or a context (phase, opponent type, frequency) is not in the data",
                },
            }
            for i, line in enumerate(lines)
        })
        for i in range(len(lines)):
            value = ((answers or {}).get(f"l{i}") or {}).get("noul")
            support[i] = float(value) if isinstance(value, (int, float)) else None

    out, report = [], {"checked": len(lines), "replaced": [], "dropped": [], "jev": jev_client.enabled()}
    for i, line in enumerate(lines):
        ok_numbers, bad = number_ok[i]
        ok_claims = support[i] is None or support[i] >= SUPPORT_THRESHOLD
        if ok_numbers and ok_claims:
            out.append(line)
            continue
        reason = {"line": line, "bad_numbers": bad, "support": support[i]}
        replacement = fallback.get(_emoji_key(line))
        if replacement:
            out.append(replacement)
            report["replaced"].append(reason)
        else:
            report["dropped"].append(reason)
    return "\n".join(out), report
