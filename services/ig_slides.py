"""
Rendered Instagram slides (migration 018): PNGs of /ig/<carousel>/<n>, made by scripts/render_ig_slides.mjs.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


def save(conn, carousel_id: str, n: int, png: bytes) -> None:
    conn.execute(text("""
        INSERT INTO ig_slide_images (carousel_id, n, png) VALUES (:c, :n, :p)
        ON CONFLICT (carousel_id, n) DO UPDATE SET png = EXCLUDED.png, rendered_at = now()
    """), {"c": carousel_id, "n": n, "p": png})


def load(db: Session, carousel_id: str, n: int) -> Optional[bytes]:
    row = db.execute(text("SELECT png FROM ig_slide_images WHERE carousel_id = :c AND n = :n"),
                     {"c": carousel_id, "n": n}).first()
    return bytes(row[0]) if row else None


#: ig_slide_images n = 0 is the Reel cover (9:16, services/ig_reel_v2.save_cover); slides are 1..N.
COVER_N = 0


def count(db: Session, carousel_id: str) -> int:
    return db.execute(text("SELECT COUNT(*) FROM ig_slide_images WHERE carousel_id = :c AND n >= 1"),
                      {"c": carousel_id}).scalar() or 0


ROOT = Path(__file__).resolve().parents[1]
SITE = os.getenv("SITE_URL", "https://hindsightcricket.com")


#: Warnings from the drawn slide end with this, so a re-render replaces them and leaves the lint's alone.
DRAWN = " (as drawn)"


def layout_warnings(warnings: List[str], layout: Dict[str, list]) -> List[str]:
    """The pack's warnings with the drawn slides' findings (scripts/lib/slide_layout.mjs) in place of the last
    render's: "Slide n: <message> (as drawn)"."""
    kept = [w for w in warnings or [] if not w.endswith(DRAWN)]
    return kept + [f"Slide {n}: {f['message']}{DRAWN}" for n, fs in sorted(layout.items(), key=lambda kv: int(kv[0]))
                   for f in fs]


def record_layout(conn, carousel_id: str, layout: Dict[str, list]) -> None:
    """Store what the render measured on every pack showing this carousel: facts.layout ([{rule, slide, message}],
    what the audit and the gate read) and the admin's warnings."""
    rows = conn.execute(text("""SELECT id, rule_warnings FROM content_packs WHERE facts->>'carousel_id' = :c"""),
                        {"c": carousel_id}).all()
    found = [{"rule": f["rule"], "slide": int(n), "message": f["message"]} for n, fs in layout.items() for f in fs]
    for pid, warnings in rows:
        conn.execute(text("""
            UPDATE content_packs SET rule_warnings = CAST(:w AS jsonb),
                   facts = jsonb_set(COALESCE(facts, '{}'::jsonb), '{layout}', CAST(:l AS jsonb))
            WHERE id = :id
        """), {"id": pid, "w": json.dumps(layout_warnings(warnings or [], layout)), "l": json.dumps(found)})


def render(carousel_id: str, slide_count: int, base: str = SITE) -> Dict[str, list]:
    """Screenshot each slide of /ig/<carousel>/<n> (scripts/render_ig_slides.mjs) and store the PNGs. The page must be
    deployed at `base` (or a dev server) and read the same database the carousel was written to."""
    from database import engine

    with tempfile.TemporaryDirectory() as out:
        for attempt in range(2):  # a browser that fails to start gets one more go
            proc = subprocess.run(["node", str(ROOT / "scripts" / "render_ig_slides.mjs"), carousel_id, str(slide_count),
                                   out, "--base", base], capture_output=True, text=True, timeout=90 + 30 * slide_count,
                                  cwd=ROOT)
            lines = [l for l in proc.stdout.splitlines() if l.startswith("{")]
            if proc.returncode == 0 and lines:
                break
        if proc.returncode != 0 or not lines:
            return {"ok": [], "failed": [{"reason": (proc.stderr or proc.stdout)[-500:]}]}
        result = json.loads(lines[-1])
        with engine.begin() as conn:
            for file in result["ok"]:
                save(conn, carousel_id, int(Path(file).stem), Path(file).read_bytes())
            if result["ok"]:
                record_layout(conn, carousel_id, result.get("layout") or {})
        reel = None
        if not result["failed"] and len(result["ok"]) == slide_count:
            # The post's Reel as it should go out: voiced (v2) when that's on and the post's kind takes it, else the
            # slideshow, from the slides just stored.
            reel = reel_from_stored(carousel_id, slide_count)
        if (Path(out) / "1.png").exists():
            from services.ig_reel_v2 import make_short, save_cover

            save_cover(carousel_id, Path(out) / "1.png")
            if reel:
                make_short(carousel_id)
    return {"ok": [int(Path(f).stem) for f in result["ok"]], "failed": result["failed"], "reel": reel,
            "layout": result.get("layout") or {}}


#: Seconds on screen: the hook, each slide in between, the end card; crossfades overlap them.
REEL_HOOK, REEL_SLIDE, REEL_END, REEL_FADE = 2.5, 3.5, 2.0, 0.4


def make_reel(carousel_id: str, pngs: List[Path]) -> Optional[float]:
    """A 1080x1920 MP4 of the slides (each 1080x1350, centred on the brand background), crossfaded, stored in
    ig_reels. Returns its length in seconds, or None without ffmpeg (or if it fails): the carousel is unaffected."""
    import shutil

    from database import engine

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or len(pngs) < 2:
        return None
    durations = [REEL_HOOK] + [REEL_SLIDE] * (len(pngs) - 2) + [REEL_END]
    inputs: List[str] = []
    for png, d in zip(pngs, durations):
        inputs += ["-loop", "1", "-t", f"{d + REEL_FADE:.2f}", "-i", str(png)]
    # Each slide padded to 9:16 on the background colour, then chained crossfades.
    pads = ";".join(f"[{i}:v]scale=1080:1350,pad=1080:1920:0:285:color=0x0a0c11,setsar=1,fps=30,format=yuv420p[s{i}]"
                    for i in range(len(pngs)))
    chain, last, t = [], "s0", 0.0
    for i in range(1, len(pngs)):
        t += durations[i - 1]
        chain.append(f"[{last}][s{i}]xfade=transition=fade:duration={REEL_FADE}:offset={t:.2f}[x{i}]")
        last = f"x{i}"
    total = round(sum(durations) + REEL_FADE, 2)
    with tempfile.TemporaryDirectory() as tmp:
        mp4 = Path(tmp) / "reel.mp4"
        proc = subprocess.run([ffmpeg, "-y", "-loglevel", "error", *inputs, "-filter_complex", f"{pads};{';'.join(chain)}",
                               "-map", f"[{last}]", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                               "-movflags", "+faststart", str(mp4)], capture_output=True, text=True, timeout=300)
        if proc.returncode != 0 or not mp4.exists():
            return None
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO ig_reels (carousel_id, mp4, seconds) VALUES (:c, :m, :s)
                ON CONFLICT (carousel_id) DO UPDATE SET mp4 = EXCLUDED.mp4, seconds = EXCLUDED.seconds, made_at = now()
            """), {"c": carousel_id, "m": mp4.read_bytes(), "s": total})
    return total


def load_short(db: Session, carousel_id: str) -> Optional[bytes]:
    """The YouTube Shorts cut (the Reel ending on its cover), or the Reel itself until one is made."""
    try:
        row = db.execute(text("SELECT COALESCE(short_mp4, mp4) FROM ig_reels WHERE carousel_id = :c"),
                         {"c": carousel_id}).first()
    except Exception:  # before migration 021
        db.rollback()
        return load_reel(db, carousel_id)
    return bytes(row[0]) if row else None


def load_reel(db: Session, carousel_id: str) -> Optional[bytes]:
    row = db.execute(text("SELECT mp4 FROM ig_reels WHERE carousel_id = :c"), {"c": carousel_id}).first()
    return bytes(row[0]) if row else None


def reel_from_stored(carousel_id: str, slide_count: int) -> Optional[float]:
    """The post's Reel: v2 (services/ig_reel_v2: voiced, captioned, opening on the payoff chart) when it's switched on
    and the post's A/B day is v2; otherwise, or if v2 fails, make_reel from the slides already stored."""
    from database import engine

    if os.getenv("REEL_V2") == "1":
        from services import ig_reel_v2

        seconds = ig_reel_v2.for_carousel(carousel_id)
        if seconds:
            return seconds

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT n, png FROM ig_slide_images WHERE carousel_id = :c ORDER BY n"),
                            {"c": carousel_id}).all()
    if len(rows) < slide_count:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        files = []
        for n, png in rows[:slide_count]:
            f = Path(tmp) / f"{n}.png"
            f.write_bytes(bytes(png))
            files.append(f)
        return make_reel(carousel_id, files)
