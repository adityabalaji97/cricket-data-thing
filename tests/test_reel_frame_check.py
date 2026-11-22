"""scripts/reel_frame_check.py: a number voiced over a captions-off scene must be in that scene's own text."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("reel_frame_check", ROOT / "scripts" / "reel_frame_check.py")
rfc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rfc)
GATE = ROOT / "tests" / "fixtures" / "reel_gate"


def test_round3_close_misses_dhulls_59():
    misses = rfc.uncovered(json.loads((GATE / "smat_r3_placed.json").read_text()))
    assert {m["number"] for m in misses} >= {"59"}
    assert all(m["kind"] == "pick_one" and m["line"] == 3 for m in misses)


def test_rana_reel_is_covered():
    assert rfc.uncovered(json.loads((GATE / "rana_placed.json").read_text())) == []
