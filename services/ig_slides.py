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


def count(db: Session, carousel_id: str) -> int:
    return db.execute(text("SELECT COUNT(*) FROM ig_slide_images WHERE carousel_id = :c"), {"c": carousel_id}).scalar() or 0


ROOT = Path(__file__).resolve().parents[1]
SITE = os.getenv("SITE_URL", "https://hindsightcricket.com")


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
        reel = None
        if not result["failed"] and len(result["ok"]) == slide_count:
            reel = make_reel(carousel_id, [Path(out) / f"{n}.png" for n in range(1, slide_count + 1)])
    return {"ok": [int(Path(f).stem) for f in result["ok"]], "failed": result["failed"], "reel": reel}


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


def load_reel(db: Session, carousel_id: str) -> Optional[bytes]:
    row = db.execute(text("SELECT mp4 FROM ig_reels WHERE carousel_id = :c"), {"c": carousel_id}).first()
    return bytes(row[0]) if row else None


def reel_from_stored(carousel_id: str, slide_count: int) -> Optional[float]:
    """make_reel from the slides already stored (carousels rendered before reels existed)."""
    from database import engine

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
