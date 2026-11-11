#!/usr/bin/env python3
"""Write the XI engine's shared test cases (src/utils/__tests__/xi_vectors.json): real squads' payloads from the
server and services/xi_engine.score on them, so the browser's scorer (src/utils/xiEngine.js) is checked against the
server's on the same inputs. Re-run when the scoring rules change.

    python scripts/xi_engine_vectors.py
"""
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
logging.disable(logging.INFO)


def main() -> int:
    from database import get_session
    from services.xi_engine import limits_state, payload, score

    db = next(get_session())
    cases = []
    for code in ("PBKS",):
        d = payload(db, code)
        squads = {"as is": d["squad"], "first 15": d["squad"][:15], "plus the pool": d["squad"] + d["pool"]}
        for label, players in squads.items():
            s = score(players, d["bench"])
            cases.append({"label": f"{code} {label}", "players": players, "roles": d["roles"], "bench": d["bench"],
                          "limits": d["limits"], "expect": {"roles": [{"key": r["key"], "status": r["status"],
                                                                       "holders": r["holders"],
                                                                       "value": None if r["value"] is None else round(r["value"], 6)}
                                                                      for r in s["roles"]], "at_level": s["at_level"]},
                          "expect_limits": limits_state(players, d["limits"])})
    out = ROOT / "src/utils/__tests__/xi_vectors.json"
    out.write_text(json.dumps(cases))
    print(f"{len(cases)} cases -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
