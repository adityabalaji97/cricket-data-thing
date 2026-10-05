"""
Shot families: one name per shot across the two tagging schemes in delivery_details.shot.

The feed changed its shot vocabulary. Older tagging (ODIs 2001-2018, T20s 2015-2024) splits by foot
("PULL_HOOK_ON_BACK_FOOT", "OFF_SIDE_DRIVE_ON_FRONT_FOOT", "CUT_SHOT_ON_BACK_FOOT") and has catch-alls
("SWEEP", "NO_SHOT", "VERTICAL_FORWARD_ATTACK"); newer tagging splits by shot ("PULL", "HOOK",
"COVER_DRIVE", "SLOG_SWEEP"). A filter on PULL/HOOK misses every older pull, so career questions
("pull and hook sixes in ODIs") came out short: Rohit 152, not 170, and AB de Villiers absent.

A family holds every label either scheme used for the same shot. Where the older scheme had one
label for what the newer one splits (old SWEEP covered what is now SWEEP_SHOT, SLOG_SWEEP and
PADDLE_SWEEP), the family is the older, wider one, so a family means the same thing in 2005 and
2025. Labels as stored on production, Oct 2026.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

#: family -> (label shown to people, member shot labels)
FAMILIES: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "PULL_HOOK": ("Pull / hook", ("PULL", "HOOK", "PULL_HOOK_ON_BACK_FOOT", "PULL_HOOK_ON_FRONT_FOOT")),
    "CUT": ("Cut", ("CUT_SHOT", "CUT_SHOT_ON_BACK_FOOT", "CUT_SHOT_ON_FRONT_FOOT", "LATE_CUT", "UPPER_CUT")),
    "DRIVE": ("Drive", ("COVER_DRIVE", "SQUARE_DRIVE", "STRAIGHT_DRIVE", "ON_DRIVE",
                        "OFF_SIDE_DRIVE_ON_BACK_FOOT", "OFF_SIDE_DRIVE_ON_FRONT_FOOT",
                        "ON_SIDE_DRIVE_ON_BACK_FOOT", "ON_SIDE_DRIVE_ON_FRONT_FOOT", "VERTICAL_FORWARD_ATTACK")),
    "FLICK_GLANCE": ("Flick / glance", ("FLICK", "LEG_GLANCE")),
    "SWEEP": ("Sweep", ("SWEEP", "SWEEP_SHOT", "SLOG_SWEEP", "PADDLE_SWEEP")),
    "REVERSE": ("Reverse sweep / scoop", ("REVERSE_SWEEP", "REVERSE_SCOOP", "REVERSE_PULL")),
    "RAMP_SCOOP": ("Ramp / scoop", ("RAMP", "PADDLE_AWAY")),
    "SLOG": ("Slog", ("SLOG_SHOT",)),
    "WORK_PUSH": ("Push / dab / steer", ("PUSH", "PUSH_SHOT", "DAB", "STEERED", "DROP_AND_RUN")),
    "DEFENCE": ("Defence", ("DEFENDED", "FORWARD_DEFENCE", "BACK_DEFENCE")),
    "LEAVE": ("Leave / no shot", ("LEFT_ALONE", "NO_SHOT", "PADDED_AWAY")),
}

FAMILY_OF: Dict[str, str] = {shot: fam for fam, (_, shots) in FAMILIES.items() for shot in shots}


class UnknownShotFamily(ValueError):
    pass


def shots_for(families: Iterable[str]) -> List[str]:
    """Every stored shot label in these families (for a WHERE ... = ANY filter)."""
    out: List[str] = []
    for fam in families or ():
        key = str(fam).strip().upper()
        if key not in FAMILIES:
            raise UnknownShotFamily(f"Unknown shot_family {fam!r}; use one of {', '.join(FAMILIES)}.")
        out.extend(s for s in FAMILIES[key][1] if s not in out)
    return out


def family_case_sql(column: str) -> str:
    """SQL mapping a shot column to its family; NULL stays NULL (untagged), unknown labels 'OTHER'."""
    whens = " ".join(f"WHEN {column} IN ({', '.join(repr(s) for s in shots)}) THEN '{fam}'"
                     for fam, (_, shots) in FAMILIES.items())
    return f"(CASE WHEN {column} IS NULL THEN NULL {whens} ELSE 'OTHER' END)"


def describe(families: Iterable[str]) -> str:
    """'Pull / hook = PULL, HOOK, PULL_HOOK_ON_BACK_FOOT, PULL_HOOK_ON_FRONT_FOOT' for footers."""
    parts = []
    for fam in families or ():
        label, shots = FAMILIES[str(fam).upper()]
        parts.append(f"{label} = {', '.join(shots)}")
    return "; ".join(parts)


def families_for_shots(shots: Iterable[str]) -> List[str]:
    """The families these shot labels belong to, in FAMILIES order (graphics default to families)."""
    fams = {FAMILY_OF.get(str(s).upper()) for s in shots or ()}
    return [f for f in FAMILIES if f in fams]
