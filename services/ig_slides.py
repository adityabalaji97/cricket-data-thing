"""
Rendered Instagram slides (migration 018): PNGs of /ig/<carousel>/<n>, made by scripts/render_ig_slides.mjs.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional

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
        proc = subprocess.run(["node", str(ROOT / "scripts" / "render_ig_slides.mjs"), carousel_id, str(slide_count), out,
                               "--base", base], capture_output=True, text=True, timeout=60 + 30 * slide_count, cwd=ROOT)
        lines = [l for l in proc.stdout.splitlines() if l.startswith("{")]
        if proc.returncode != 0 or not lines:
            return {"ok": [], "failed": [{"reason": (proc.stderr or proc.stdout)[-500:]}]}
        result = json.loads(lines[-1])
        with engine.begin() as conn:
            for file in result["ok"]:
                save(conn, carousel_id, int(Path(file).stem), Path(file).read_bytes())
    return {"ok": [int(Path(f).stem) for f in result["ok"]], "failed": result["failed"]}
