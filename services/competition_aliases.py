"""
Competition name canonicalisation.

The feed writes the same competition under several names — "Big Bash League" and "BBL",
"Vitality Blast" and "T20 Blast", "Men's Hundred" and "Men's 100" — and nothing collapsed
them. Each variant became its own group, its own filter entry and its own query scope, so a
league filter silently returned part of its own data: "Vitality Blast" missed 49 matches,
"BBL" missed 621.

Canonicalised at query time rather than by rewriting `matches.competition`, matching the
decision taken for player aliases. The raw value stays as the feed supplied it, so a mapping
that turns out wrong is a one-line correction rather than another migration.

**Only unambiguous aliases belong here.** Merging two genuinely different competitions fuses
unrelated cricket into one record and is invisible afterwards — the same reasoning that kept
ambiguous player names split. Pairs that merely look similar are listed in AMBIGUOUS below
and deliberately left alone.
"""

from typing import Dict, List, Optional

#: variant (lowercased) -> canonical display name.
#: Abbreviations and full names both map to a single canonical key. The canonical form is the
#: one used for display, so it follows models.leagues_mapping where that already has an opinion
#: (Vitality Blast is shown as "T20 Blast").
_ALIASES: Dict[str, str] = {}

#: canonical -> the original-cased values as they appear in matches.competition. Kept
#: separately because filtering matches the raw column, and the lookup above is lowercased.
_VARIANTS: Dict[str, List[str]] = {}


def _register(canonical: str, *variants: str) -> None:
    _ALIASES[canonical.strip().lower()] = canonical
    _VARIANTS.setdefault(canonical, [canonical])
    for variant in variants:
        _ALIASES[variant.strip().lower()] = canonical
        if variant not in _VARIANTS[canonical]:
            _VARIANTS[canonical].append(variant)


# Franchise leagues: abbreviation and full name are the same competition.
_register("IPL", "Indian Premier League", "Indian Premier League (IPL)")
_register("BBL", "Big Bash League")
_register("BPL", "Bangladesh Premier League")
_register("CPL", "Caribbean Premier League")
_register("PSL", "Pakistan Super League")
_register("LPL", "Lanka Premier League")
_register("MLC", "Major League Cricket")
_register("ILT20", "International League T20")

# England's domestic T20, renamed by sponsor. leagues_mapping already displays these as
# "T20 Blast", so that is the canonical form.
_register("T20 Blast", "Vitality Blast", "NatWest T20 Blast")

# The Hundred. "Men's 100" covers only 2021 and "Men's Hundred" everything after, so this is a
# feed rename rather than two competitions.
_register("Men's Hundred", "Men's 100")

# India's domestic T20, which appears as the full name, an acronym, and a shouted variant.
_register("Syed Mushtaq Ali Trophy", "SMAT", "SMA TROPHY", "SMA TROPHY FINAL")

# Pure formatting difference: hyphenation and capitalisation only.
_register("Inter Pro T20", "INTER-PRO T20")


#: Pairs that look related but are NOT merged, because the names do not establish that they are
#: the same competition and the data cannot settle it. Left split on purpose — a wrong merge is
#: silent and permanent-feeling, a missed one is merely untidy. Resolve with someone who knows
#: the competitions, then move entries up into _register above.
AMBIGUOUS: List[tuple] = [
    ("National T20 Cup", "National T20"),          # plausibly different countries
    ("CSA T20", "CSA T20 Challenge", "CSA Provincial T20 Challenge", "Provincial T20"),
    ("SLC T20", "SLC T20 League", "SLC Twenty-20 Tournament", "Clubs T20 [SLC]"),
    ("Ram Slam T20 Challenge", "Ram Slam T20"),    # likely one, but both are RSA domestic
    ("GSL", "GSL 2024"),                           # season suffix, or a distinct edition?
]


def canonical_competition(competition: Optional[str]) -> Optional[str]:
    """The canonical name for a competition, or the input unchanged if it has no alias."""
    if not competition:
        return competition
    value = str(competition).strip()
    return _ALIASES.get(value.lower(), value)


def variants_for(canonical: Optional[str]) -> List[str]:
    """Every raw value that canonicalises to this name, for use in a SQL IN clause.

    Filtering has to match on the raw column, so asking for "T20 Blast" must also select rows
    stored as "Vitality Blast" — otherwise canonicalising the label alone would leave the
    filter returning the same partial data it always did.
    """
    if not canonical:
        return []
    target = canonical_competition(canonical)
    return list(_VARIANTS.get(target, [target]))


def canonical_sql(column: str = "m.competition") -> str:
    """A SQL CASE mapping the raw competition column to its canonical name.

    Generated from the same table as canonical_competition(), so the SQL grouping and the
    Python labelling cannot disagree — which is exactly how "BBL" and "Big Bash League" came
    to be separate groups while both displayed as "BBL".
    """
    whens = []
    for variant, canonical in sorted(_ALIASES.items()):
        safe_variant = variant.replace("'", "''")
        safe_canonical = canonical.replace("'", "''")
        whens.append(f"WHEN LOWER(TRIM({column})) = '{safe_variant}' THEN '{safe_canonical}'")
    return "CASE " + " ".join(whens) + f" ELSE {column} END"
