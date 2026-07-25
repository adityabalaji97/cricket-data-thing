#!/usr/bin/env python3
"""Extract a small, complete-match slice of a ball-by-ball CSV for local testing.

The full datasets are large (the shared Dropbox folder is ~11 GB) and downloading one just to
exercise the loader wastes hours. This streams only the first N bytes of the folder's zip and
decompresses the leading part of the requested CSV, then keeps whole matches so innings and
ball sequences stay internally consistent.

    # from the shared Dropbox folder (streams, never downloads the whole archive)
    python scripts/dev/make_csv_slice.py --dropbox-url "<folder share url>" \
        --member odi_bbb.csv --out data/slices/odi_slice.csv

    # from a CSV already on disk
    python scripts/dev/make_csv_slice.py --csv /path/to/t20_bbb.csv \
        --out data/slices/t20_slice.csv --matches 200

Slices live in data/slices/ and are gitignored -- regenerate rather than commit them.
"""

from __future__ import annotations

import argparse
import csv
import io
import struct
import sys
import urllib.request
import zlib
from pathlib import Path


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
    source.add_argument("--dropbox-url", help="Shared folder URL (dl=1 is applied automatically)")
    source.add_argument("--csv", help="Path to a CSV already on disk")
    parser.add_argument("--member", default="odi_bbb.csv", help="File to pull out of the zip")
    parser.add_argument("--out", required=True, help="Destination slice path")
    parser.add_argument("--matches", type=int, default=None, help="Cap on matches kept")
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=60_000_000,
        help="How much of the zip stream to read (default 60 MB)",
    )
    args = parser.parse_args()

    if args.dropbox_url:
        url = args.dropbox_url.replace("dl=0", "dl=1")
        if "dl=" not in url:
            url += ("&" if "?" in url else "?") + "dl=1"
        print(f"Streaming up to {args.max_bytes:,} bytes for {args.member}...")
        text = stream_member_from_zip(url, args.member, args.max_bytes)
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
