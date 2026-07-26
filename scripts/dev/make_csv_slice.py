#!/usr/bin/env python3
"""Extract a small, complete-match slice of a ball-by-ball CSV for local testing.

The full datasets run to hundreds of megabytes each and downloading one just to exercise the
loader wastes time, so this reads only the leading bytes of a file and keeps whole matches, so
innings and ball sequences stay internally consistent.

    # normal use: the URL comes from .env, never from the command line
    python scripts/dev/make_csv_slice.py --url-env DROPBOX_ODI_URL \
        --out data/slices/odi_slice.csv --matches 300

    # from a CSV already on disk
    python scripts/dev/make_csv_slice.py --csv /path/to/t20_bbb.csv \
        --out data/slices/t20_slice.csv --matches 200

    # legacy: pull a member out of the whole-folder zip (no longer needed for the four
    # ball-by-ball datasets, which have direct per-file links)
    python scripts/dev/make_csv_slice.py --url-env DROPBOX_FOLDER_URL \
        --member odi_bbb.csv --out data/slices/odi_slice.csv

The URLs live in `.env` (gitignored) because this repository is **public** and each Dropbox
share link embeds an `rlkey` that grants access to the data. `--url-env` names the variable so
no link is ever typed on a command line or left in shell history; there is deliberately no
`--url` flag.

Slices live in data/slices/ and are gitignored -- regenerate rather than commit them.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import struct
import sys
import urllib.request
import zlib
from pathlib import Path

try:  # optional: lets the script pick up .env without the caller exporting anything
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


def read_leading_bytes(url: str, max_bytes: int) -> str:
    """Download the first `max_bytes` of a plain CSV URL and decode them as text."""
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request) as response:
        return response.read(max_bytes).decode("utf-8", "replace")


def stream_member_from_zip(url: str, member: str, max_bytes: int) -> str:
    """Download the first `max_bytes` of a zip stream and decompress `member` from it.

    Dropbox folder downloads do not honour range requests, so we read from the start and
    stop early. Entries appear in the archive in order, so this only works for members near
    the front -- which is enough for a slice.
    """
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request) as response:
        data = response.read(max_bytes)

    position = 0
    while True:
        position = data.find(b"PK\x03\x04", position)
        if position < 0:
            raise SystemExit(
                f"{member} not found in the first {max_bytes:,} bytes. "
                "Increase --max-bytes, or the member is too far into the archive."
            )
        name_len, extra_len = struct.unpack("<HH", data[position + 26 : position + 30])
        name = data[position + 30 : position + 30 + name_len].decode("utf-8", "replace")
        method = struct.unpack("<H", data[position + 8 : position + 10])[0]
        body_start = position + 30 + name_len + extra_len

        if name.endswith(member):
            raw = data[body_start:]
            if method == 8:  # deflate
                # The stream is truncated, so an incomplete final block is expected.
                return zlib.decompressobj(-15).decompress(raw, 500_000_000).decode("utf-8", "replace")
            return raw.decode("utf-8", "replace")

        position += 4


def slice_complete_matches(text: str, match_limit: int | None) -> tuple[list[dict], list[str]]:
    """Keep only whole matches, dropping the truncated tail."""
    lines = text.split("\n")[:-1]  # last line is cut mid-record
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    rows = list(reader)
    if not rows:
        raise SystemExit("No complete rows decoded -- try a larger --max-bytes.")

    order: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if row["p_match"] not in seen:
            seen.add(row["p_match"])
            order.append(row["p_match"])

    # The final match is almost certainly cut off by the truncated stream.
    order = order[:-1]
    if match_limit:
        order = order[:match_limit]

    keep = set(order)
    return [r for r in rows if r["p_match"] in keep], list(rows[0].keys())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--url-env",
        help="Name of the env var holding the download URL, e.g. DROPBOX_ODI_URL. "
        "There is no --url flag on purpose: links carry an access key and must not "
        "appear in shell history.",
    )
    source.add_argument("--csv", help="Path to a CSV already on disk")
    parser.add_argument(
        "--member",
        default=None,
        help="Only for a whole-folder zip URL: which file to extract from the archive",
    )
    parser.add_argument("--out", required=True, help="Destination slice path")
    parser.add_argument("--matches", type=int, default=None, help="Cap on matches kept")
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=60_000_000,
        help="How much of the stream to read (default 60 MB)",
    )
    args = parser.parse_args()

    if args.url_env:
        if load_dotenv is not None:
            load_dotenv()
        url = os.getenv(args.url_env)
        if not url:
            raise SystemExit(
                f"{args.url_env} is not set. Add it to .env (which is gitignored) — "
                "do not pass the URL on the command line."
            )
        url = url.replace("dl=0", "dl=1")
        if "dl=" not in url:
            url += ("&" if "?" in url else "?") + "dl=1"

        print(f"Reading up to {args.max_bytes:,} bytes from ${args.url_env}...")
        if args.member:
            text = stream_member_from_zip(url, args.member, args.max_bytes)
        else:
            text = read_leading_bytes(url, args.max_bytes)
    else:
        text = Path(args.csv).read_text(encoding="utf-8", errors="replace")

    rows, fieldnames = slice_complete_matches(text, args.matches)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    matches = {r["p_match"] for r in rows}
    dates = [r.get("date", "") for r in rows if r.get("date")]
    print(f"Wrote {out_path}: {len(rows):,} rows across {len(matches)} complete matches")
    if dates:
        print(f"  date range: {min(dates)} -> {max(dates)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
