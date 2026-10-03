"""
Run every hypothesis and write analysis/hypotheses/results/<slug>.json.

    DATABASE_URL=postgresql://localhost:5432/hindsight_analysis python -m analysis.hypotheses.run_all
    python -m analysis.hypotheses.run_all h0 h6        # a subset

The results are only meaningful on a database holding the full men's T20 history (2015 onward):
build one with scripts/dev/setup_analysis_db.sh. hindsight_local (2024 onward) is fine for checking
that the scripts run, not for the findings; set HYPOTHESIS_RESULTS_DIR to keep those runs out of
the repo.
"""
from __future__ import annotations

import importlib
import sys
import time

MODULES = {
    "h0": "h0_varun_first_over", "h1": "h1_impact_player", "h2": "h2_varun_figured_out", "h3": "h3_iyer_anchor",
    "h4": "h4_india_openers", "h5": "h5_anchor_dead", "h6": "h6_bumrah_death", "h7": "h7_toss_india",
    "h8": "h8_matchups",
}


def main(selected=None) -> int:
    for key in selected or MODULES:
        started = time.time()
        module = importlib.import_module(f"analysis.hypotheses.{MODULES[key]}")
        result = module.run()
        path = result.save()
        print(f"{result.hypothesis}: {result.verdict} ({time.time() - started:.0f}s) -> {path}")
        print(f"    {result.headline}")
        for part, verdict in result.parts.items():
            print(f"    {part}: {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or None))
