"""Team-name standardization (companion to venue_standardization.py).

Persists a single canonical full name per franchise across all six
team-bearing columns: dd.team_bat, dd.team_bowl, m.team1, m.team2,
m.winner, m.toss_winner. Same shape as standardize_venues(): batched
UPDATE via VALUES lookup, idempotent on re-run.

Once the data is canonical, get_team_canonical_sql() in
services/query_builder_v2.py can collapse from a per-row CASE expression
to a passthrough — that's the perf win for match_outcome / chase_outcome
queries.
"""

from database import get_database_connection
from sqlalchemy import text
from models import teams_mapping


# Canonical full name per franchise abbreviation. Defaults to the modern
# / current name where the franchise has rebranded.
CANONICAL_FULL_BY_ABBREV = {
    'CSK':  'Chennai Super Kings',
    'MI':   'Mumbai Indians',
    'KKR':  'Kolkata Knight Riders',
    'GT':   'Gujarat Titans',
    'LSG':  'Lucknow Super Giants',
    'PBKS': 'Punjab Kings',                # was: Kings XI Punjab
    'RCB':  'Royal Challengers Bengaluru', # was: Royal Challengers Bangalore
    'DC':   'Delhi Capitals',              # was: Delhi Daredevils
    'SRH':  'Sunrisers Hyderabad',
    'RR':   'Rajasthan Royals',
    'RPSG': 'Rising Pune Supergiants',     # was: Rising Pune Supergiant (singular)
    'GL':   'Gujarat Lions',
    'DCh':  'Deccan Chargers',
    'KTK':  'Kochi Tuskers Kerala',
}


def _build_raw_to_canonical():
    """Walk teams_mapping (raw → abbreviation) and pivot to raw → canonical
    full name via CANONICAL_FULL_BY_ABBREV. Identity entries for the
    canonical names themselves keep the alias index complete."""
    result = {}
    for raw_full, abbrev in teams_mapping.items():
        canonical = CANONICAL_FULL_BY_ABBREV.get(abbrev)
        if canonical:
            result[raw_full] = canonical
    for canonical in CANONICAL_FULL_BY_ABBREV.values():
        result.setdefault(canonical, canonical)
    return result


TEAM_RAW_TO_CANONICAL = _build_raw_to_canonical()


# All columns where raw team names live and need to be canonicalised.
TEAM_COLUMN_TARGETS = (
    ("delivery_details", "team_bat"),
    ("delivery_details", "team_bowl"),
    ("matches", "team1"),
    ("matches", "team2"),
    ("matches", "winner"),
    ("matches", "toss_winner"),
)


def standardize_teams():
    """Batched UPDATE that normalizes every team-bearing column using
    TEAM_RAW_TO_CANONICAL. Skips identity mappings; idempotent on re-run."""
    engine, SessionLocal = get_database_connection()
    session = SessionLocal()

    pairs = [(raw, canonical) for raw, canonical in TEAM_RAW_TO_CANONICAL.items() if raw != canonical]
    if not pairs:
        print("No non-identity team mappings; nothing to do.")
        session.close()
        return

    values_sql = ", ".join(f"(:r{i}, :c{i})" for i in range(len(pairs)))
    params = {}
    for i, (raw, canonical) in enumerate(pairs):
        params[f"r{i}"] = raw
        params[f"c{i}"] = canonical

    try:
        for table, column in TEAM_COLUMN_TARGETS:
            before = session.execute(
                text(f"SELECT COUNT(DISTINCT {column}) FROM {table} WHERE {column} IS NOT NULL")
            ).scalar()
            update_sql = text(f"""
                UPDATE {table} AS t
                SET {column} = mp.canonical
                FROM (VALUES {values_sql}) AS mp(raw, canonical)
                WHERE t.{column} = mp.raw AND t.{column} IS DISTINCT FROM mp.canonical
            """)
            result = session.execute(update_sql, params)
            session.commit()
            after = session.execute(
                text(f"SELECT COUNT(DISTINCT {column}) FROM {table} WHERE {column} IS NOT NULL")
            ).scalar()
            print(f"[{table}.{column}] rows updated: {result.rowcount}; distinct values {before} -> {after}")
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    standardize_teams()
