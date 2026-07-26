#!/usr/bin/env python3
"""RETIRED -- this script is no longer safe to run.

It used to delete any match with more than 260 deliveries, on the assumption that a longer
match could only be bad data, since a T20 innings tops out around 240 balls.

That assumption stopped being true when this app gained ODIs, women's T20s and Tests. Every
ODI (~600 balls) and every Test (~1,700 balls, and up to 197 overs in a single innings) trips
the old threshold, so running the original script against the current database would delete
essentially all non-T20 cricket, along with the derived batting and bowling stats hanging off
those matches.

Format is now an explicit column rather than something inferred from match length -- see
`format_config.py` and `scripts/migrations/001_multi_format_columns.sql`. If you need to remove
data for one format, filter on `format` and `gender` directly and write the deletion for that
specific case, with a backup taken first.

The file is kept rather than deleted because its name appears in older documentation, in shell
history and in the sync READMEs; a loud refusal is more useful than "command not found", which
would invite someone to reconstruct it from git history.

Context: MULTI_FORMAT_PLAN.md, decision D4. The original implementation is in git history at
the commit that retired it.
"""

import sys


def main() -> int:
    print(__doc__, file=sys.stderr)
    print(
        "REFUSING TO RUN: this would delete every ODI and every Test in the database.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
