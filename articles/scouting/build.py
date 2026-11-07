"""
Scouting cards (services/scouting.py): "how to bowl to" a batter, or "how to bat against" a bowler, rendered as post
cards for a reply or a carousel.

    python articles/scouting/build.py --batter "Liam Livingstone" [--since 2024-01-01]
    python articles/scouting/build.py --bowler "Noor Ahmad"
"""
import argparse
import logging
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
logging.disable(logging.INFO)


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--batter")
    g.add_argument("--bowler")
    ap.add_argument("--since", default="2024-01-01")
    ap.add_argument("--base", default="https://hindsightcricket.com")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    from database import get_session
    from services import ig_carousel, ig_slides
    from services.scouting import Scout
    from services.social_rules import findings

    db = next(get_session())
    s = Scout(db, date.fromisoformat(args.since))
    out = s.bowl_to(args.batter) if args.batter else s.bat_against(args.bowler)
    slides = [{"type": "card", "card": c} for c in out["cards"]]
    for c in out["cards"]:
        print(f"[{c['visual']}] {c['title']} ({len(c['title'])})")
    print("facts:", {k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk in ('name', 'value', 'line', 'length', 'balls', 'strike_rate', 'runs', 'shot_family')}) for k, v in out["facts"].items()})
    problems = findings(slides, "spotlight")
    print("lint:", problems or "clean")
    if problems or args.dry:
        return 1 if problems else 0
    slug = re.sub(r"[^a-z0-9]+", "-", out["name"].lower()).strip("-") + ("-bowl-to" if args.batter else "-bat-against")
    car = ig_carousel.save(db, slides, out["name"], {"scouting": slug, "since": args.since}, "scouting")
    r = ig_slides.render(car["id"], len(slides), args.base)
    print(f"carousel {car['id']}: rendered {len(r['ok'])}/{len(slides)}; layout {r.get('layout') or 'clean'}")
    d = HERE / slug
    d.mkdir(exist_ok=True)
    for n in range(1, len(slides) + 1):
        png = ig_slides.load(db, car["id"], n)
        if png:
            (d / f"{n}.png").write_bytes(png)
    print("cards in", d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
