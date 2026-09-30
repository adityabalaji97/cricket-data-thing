#!/usr/bin/env python3
"""
Cricsheet fallback loader: results, scorecards and basic stats for matches the ball-by-ball CSV
has not delivered yet.

Nightly step after the delivery-details legs (.github/workflows/refresh-delivery-details.yml).
Downloads Cricsheet's "recently added" men's archive and, for each men's T20/ODI in scope that the
database does not already have, writes:

  * the matches row, data_source='cricsheet' (format, gender, competition bucket, match_type);
  * `deliveries` rows, which the scorecard reads for data_source='cricsheet' matches;
  * batting_stats/bowling_stats through sync_stats_from_dd.StatsFromDeliveryDetails, with the
    Cricsheet balls converted to the delivery_details shape first -- one set of definitions for
    bowler runs, LBWs, per-format phases and fantasy points.

When the CSV later has the match, the sync upgrades it in place
(DeliveryDetailsSync.upgrade_cricsheet_matches): same matches row, stats rebuilt, these
deliveries rows dropped.

Duplicate guard: Cricsheet file names are ESPNcricinfo match ids, the key of matches.id and
delivery_details.p_match. Ids already in either are skipped. A same-date, same-teams match under
another id is also skipped, and logged for review.

Scope: every men's T20 international and ODI, plus the main T20 leagues (LEAGUE_BUCKETS). Club
and second-tier events are skipped; so is The Hundred, whose 100-ball innings the per-format
phases do not describe. Nothing before 2015 is loaded: the legacy `deliveries` table is read as
pre-2015 men's T20 wherever it is not routed by match, and these rows must stay out of that.

Player names: Cricsheet id -> ESPNcricinfo id (Cricsheet's people register) -> the name
delivery_details uses for that id, so stats join up with the ball-by-ball rows around them.
Falls back to player_aliases, then to the Cricsheet name.

Usage:
    python scripts/load_cricsheet.py                      # recently added, last 7 days
    python scripts/load_cricsheet.py --days 30 --dry-run  # what would load, no writes
    python scripts/load_cricsheet.py --zip path/or/url.zip --ids 1549969
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import os
import sys
import urllib.request
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CRICSHEET = "https://cricsheet.org"
RECENT_DAYS = (2, 7, 30)  # the "recently added" archives Cricsheet publishes
PEOPLE_URL = f"{CRICSHEET}/register/people.csv"

# The legacy deliveries table is read as pre-2015 men's T20 wherever it is not routed per match.
BBB_START = date(2015, 1, 1)

# Cricsheet event name (lowercased) -> matches.competition bucket, as the T20 feed ships it.
LEAGUE_BUCKETS = {
    'indian premier league': 'IPL',
    'big bash league': 'BBL',
    'pakistan super league': 'PSL',
    'caribbean premier league': 'CPL',
    'sa20': 'SA20',
    'international league t20': 'ILT20',
    'major league cricket': 'MLC',
    'vitality blast': 'T20 Blast',
    't20 blast': 'T20 Blast',
    'bangladesh premier league': 'BPL',
    'lanka premier league': 'LPL',
    'super smash': 'Super Smash',
}

# Cricsheet wicket kinds -> the delivery_details spelling, which the stats writer expects.
DD_DISMISSAL = {
    'lbw': 'leg before wicket',
    'caught and bowled': 'caught',
    'retired hurt': 'retired not out (hurt)',
}


# --------------------------------------------------------------------------------------------
# Pure part: parse, scope, convert. No database; tested in tests/test_load_cricsheet.py.
# --------------------------------------------------------------------------------------------

@dataclass
class CricsheetMatch:
    match_id: str
    data: Dict

    @property
    def info(self) -> Dict:
        return self.data['info']

    @property
    def date(self) -> date:
        return date.fromisoformat(self.info['dates'][0])

    @property
    def fmt(self) -> str:
        return 'ODI' if self.info.get('match_type') == 'ODI' else 'T20'

    @property
    def event(self) -> Optional[str]:
        return (self.info.get('event') or {}).get('name')

    def innings(self) -> List[Tuple[int, Dict]]:
        """(innings number, innings) for the regular innings; super overs are left out, as the
        stats writer only reads innings 1 and 2."""
        return [(n, inn) for n, inn in enumerate(self.data.get('innings', []), 1)
                if not inn.get('super_over')]

    def player_ids(self) -> Dict[str, str]:
        """Cricsheet name -> Cricsheet person id."""
        return dict((self.info.get('registry') or {}).get('people') or {})


def scope_reason(match: CricsheetMatch) -> Optional[str]:
    """Why a match is out of scope, or None when it should be loaded."""
    info = match.info
    if info.get('gender') != 'male':
        return 'not men'
    if info.get('match_type') not in ('T20', 'ODI'):
        return f"match type {info.get('match_type')}"
    if match.date < BBB_START:
        return 'before 2015'
    if info.get('balls_per_over', 6) != 6:
        return 'not six-ball overs'
    if info.get('team_type') == 'international':
        return None
    if match.fmt == 'T20' and (match.event or '').lower() in LEAGUE_BUCKETS:
        return None
    return f"not a main league ({match.event})"


def competition_for(match: CricsheetMatch, teams: List[str]) -> Tuple[str, Optional[str], str]:
    """(competition bucket, event_name, match_type) the way the delivery_details sync sets them."""
    from services.competition_normalizer import is_international, normalize_competition

    event = match.event
    if match.info.get('team_type') == 'international':
        if match.fmt == 'T20':
            # Every men's T20 international is 'T20I', World Cups included; the event keeps the name.
            return 'T20I', event, 'international'
        competition = normalize_competition(event, None, None, 'ODI')
        match_type = 'international' if is_international(competition, teams, 'ODI') else 'league'
        return competition, event, match_type
    return LEAGUE_BUCKETS[(event or '').lower()], event, 'league'


def canonical_team(name: Optional[str]) -> Optional[str]:
    from team_standardization import TEAM_RAW_TO_CANONICAL
    return TEAM_RAW_TO_CANONICAL.get(name, name) if name else name


def team_key(name: Optional[str]) -> str:
    """Comparable team identity across renames ("Kings XI Punjab" == "Punjab Kings")."""
    from models import teams_mapping
    return teams_mapping.get(name, name) if name else ''


def _other(teams: List[str], team: str) -> Optional[str]:
    return next((t for t in teams if t != team), None)


def stat_deliveries(match: CricsheetMatch, name_of) -> List[Dict]:
    """Cricsheet balls in the shape sync_stats_from_dd reads from delivery_details.

    Mirrors the feed's conventions: `ball` counts every delivery in the over, wides and no-balls
    included; `out`/`bat_out` are the strings 'true'/'false'; dismissals use the feed's spellings.
    """
    teams = [canonical_team(t) for t in match.info['teams']]
    rows: List[Dict] = []
    for inns_no, inn in match.innings():
        batting_team = canonical_team(inn['team'])
        bowling_team = _other(teams, batting_team)
        for over in inn.get('overs', []):
            for ball_no, b in enumerate(over['deliveries'], 1):
                extras = b.get('extras') or {}
                wicket = (b.get('wickets') or [None])[0]
                kind = wicket['kind'] if wicket else None
                penalty = extras.get('penalty', 0)
                rows.append({
                    'match_id': match.match_id,
                    'innings': inns_no,
                    'over': over['over'],
                    'ball': ball_no,
                    'batter': name_of(b['batter']),
                    'bowler': name_of(b['bowler']),
                    'batting_team': batting_team,
                    'bowling_team': bowling_team,
                    # Penalty runs are nobody's: not the batter's, not the bowler's.
                    'score': b['runs']['total'] - penalty,
                    'batruns': b['runs']['batter'],
                    'outcome': _outcome(b, extras, wicket),
                    'out': 'true' if wicket else 'false',
                    'bat_out': 'true' if wicket and wicket.get('player_out') == b['batter'] else 'false',
                    'dismissal': DD_DISMISSAL.get(kind, kind) if kind else None,
                    'noball': extras.get('noballs', 0),
                    'wide': extras.get('wides', 0),
                    'byes': extras.get('byes', 0),
                    'legbyes': extras.get('legbyes', 0),
                    'format': match.fmt,
                    'gender': 'male',
                })
    return rows


def _outcome(b: Dict, extras: Dict, wicket: Optional[Dict]) -> str:
    if wicket:
        return 'out'
    if extras.get('wides'):
        return 'wide'
    if extras.get('noballs'):
        return 'no ball'
    runs = b['runs']['batter']
    if runs == 4:
        return 'four'
    if runs == 6:
        return 'six'
    if extras.get('legbyes'):
        return 'leg bye'
    if extras.get('byes'):
        return 'bye'
    return 'run' if runs else 'no run'


def legacy_deliveries(match: CricsheetMatch, name_of) -> List[Dict]:
    """`deliveries` rows, as enhanced_loadMatches.py wrote them (Cricsheet wicket kinds kept)."""
    teams = [canonical_team(t) for t in match.info['teams']]
    rows: List[Dict] = []
    for inns_no, inn in match.innings():
        batting_team = canonical_team(inn['team'])
        for over in inn.get('overs', []):
            for ball_no, b in enumerate(over['deliveries'], 1):
                extras = b.get('extras') or {}
                wicket = (b.get('wickets') or [None])[0]
                fielders = (wicket or {}).get('fielders') or []
                rows.append({
                    'match_id': match.match_id,
                    'innings': inns_no,
                    'over': over['over'],
                    'ball': ball_no,
                    'batter': name_of(b['batter']),
                    'non_striker': name_of(b['non_striker']),
                    'bowler': name_of(b['bowler']),
                    'runs_off_bat': b['runs']['batter'],
                    'extras': b['runs'].get('extras', 0),
                    'wides': extras.get('wides', 0),
                    'noballs': extras.get('noballs', 0),
                    'byes': extras.get('byes', 0),
                    'legbyes': extras.get('legbyes', 0),
                    'penalty': extras.get('penalty', 0),
                    'wicket_type': wicket['kind'] if wicket else None,
                    'player_dismissed': name_of(wicket['player_out']) if wicket else None,
                    'fielder': name_of(fielders[0]['name']) if fielders and fielders[0].get('name') else None,
                    'batting_team': batting_team,
                    'bowling_team': _other(teams, batting_team),
                })
    return rows


def match_row(match: CricsheetMatch, name_of) -> Dict:
    """The matches row, with the same derived fields the delivery_details sync fills."""
    info = match.info
    innings = match.innings()
    teams = [canonical_team(t) for t in info['teams']]
    bat_first = canonical_team(innings[0][1]['team']) if innings else teams[0]
    bowl_first = _other(teams, bat_first)
    toss = info.get('toss') or {}
    toss_winner = canonical_team(toss.get('winner'))
    outcome = info.get('outcome') or {}
    winner = canonical_team(outcome.get('winner'))
    competition, event_name, match_type = competition_for(match, teams)
    max_over = max((o['over'] for _, inn in innings for o in inn.get('overs', [])), default=None)
    pom = info.get('player_of_match') or []

    return {
        'id': match.match_id,
        'date': match.date,
        'venue': info.get('venue'),
        'city': info.get('city'),
        'event_name': event_name,
        'event_match_number': (info.get('event') or {}).get('match_number'),
        'team1': bat_first,
        'team2': bowl_first,
        'toss_winner': toss_winner,
        'toss_decision': toss.get('decision'),
        'winner': winner,
        'outcome': outcome or None,
        'player_of_match': name_of(pom[0]) if pom else None,
        # Overs actually bowled, as the sync derives it (rain-reduced games come in short).
        'overs': (max_over + 1) if max_over is not None else None,
        'balls_per_over': 6,
        'win_toss_win_match': (toss_winner == winner) if toss_winner and winner else None,
        'bat_first': bat_first,
        'bowl_first': bowl_first,
        'won_batting_first': (winner == bat_first) if winner else None,
        'won_fielding_first': (winner == bowl_first) if winner else None,
        'match_type': match_type,
        'competition': competition,
        'format': match.fmt,
        'gender': 'male',
        'data_source': 'cricsheet',
    }


def read_archive(source: str) -> List[CricsheetMatch]:
    """Every match JSON in a Cricsheet zip (a path or a URL)."""
    raw = _fetch(source)
    matches = []
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        for name in zf.namelist():
            base = os.path.basename(name)
            if not base.endswith('.json'):
                continue
            matches.append(CricsheetMatch(base[:-5], json.loads(zf.read(name))))
    return matches


def read_people_register(source: str = PEOPLE_URL) -> Dict[str, List[int]]:
    """Cricsheet person id -> ESPNcricinfo ids (a player can carry up to three)."""
    reader = csv.DictReader(io.StringIO(_fetch(source).decode('utf-8')))
    register = {}
    for row in reader:
        ids = [int(row[k]) for k in ('key_cricinfo', 'key_cricinfo_2', 'key_cricinfo_3')
               if (row.get(k) or '').strip().isdigit()]
        if ids:
            register[row['identifier']] = ids
    return register


def _fetch(source: str) -> bytes:
    if source.startswith(('http://', 'https://')):
        request = urllib.request.Request(source, headers={'User-Agent': 'hindsight-cricsheet-loader'})
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.read()
    with open(source, 'rb') as fh:
        return fh.read()


# --------------------------------------------------------------------------------------------
# Database part.
# --------------------------------------------------------------------------------------------

@dataclass
class NameResolver:
    """Cricsheet name -> the name the rest of the database uses for that player."""
    names: Dict[str, str] = field(default_factory=dict)

    def __call__(self, cricsheet_name: Optional[str]) -> Optional[str]:
        if not cricsheet_name:
            return cricsheet_name
        return self.names.get(cricsheet_name, cricsheet_name)

    @classmethod
    def build(cls, session, matches: Iterable[CricsheetMatch], register: Dict[str, List[int]]) -> 'NameResolver':
        people: Dict[str, str] = {}  # Cricsheet name -> Cricsheet id
        for m in matches:
            people.update(m.player_ids())

        cricinfo_ids = sorted({cid for pid in people.values() for cid in register.get(pid, [])})
        feed_name_by_cricinfo: Dict[int, str] = {}
        if cricinfo_ids:
            # One pass for the whole run: there is no index on p_bat/p_bowl (~3 s on prod).
            rows = session.execute(text("""
                SELECT DISTINCT ON (pid) pid, name FROM (
                    SELECT p_bat AS pid, bat AS name, match_date FROM delivery_details
                    WHERE p_bat = ANY(:ids) AND bat IS NOT NULL
                    UNION ALL
                    SELECT p_bowl, bowl, match_date FROM delivery_details
                    WHERE p_bowl = ANY(:ids) AND bowl IS NOT NULL
                ) x
                ORDER BY pid, match_date DESC
            """), {'ids': cricinfo_ids}).fetchall()
            feed_name_by_cricinfo = {r[0]: r[1] for r in rows}

        alias_rows = session.execute(text("""
            SELECT player_name, alias_name, source FROM player_aliases
            WHERE player_name = ANY(:names) OR source = 'spelling_variant'
        """), {'names': list(people)}).fetchall()
        # A reviewed spelling variant points at the player's main name (migration 005).
        main_name = {r[0]: r[1] for r in alias_rows if r[2] == 'spelling_variant'}
        alias_targets: Dict[str, set] = defaultdict(set)
        for r in alias_rows:
            if r[2] != 'spelling_variant':
                alias_targets[r[0]].add(r[1])

        names = {}
        for cs_name, pid in people.items():
            resolved = next((feed_name_by_cricinfo[c] for c in register.get(pid, []) if c in feed_name_by_cricinfo), None)
            if resolved is None and len(alias_targets.get(cs_name, ())) == 1:
                resolved = next(iter(alias_targets[cs_name]))
            resolved = resolved or cs_name
            names[cs_name] = main_name.get(resolved, resolved)
        return cls(names)


def existing_ids(session, ids: List[str]) -> set:
    if not ids:
        return set()
    rows = session.execute(text("""
        SELECT id FROM matches WHERE id = ANY(:ids)
        UNION
        SELECT DISTINCT p_match FROM delivery_details WHERE p_match = ANY(:ids)
    """), {'ids': ids}).fetchall()
    return {r[0] for r in rows}


def same_fixture_ids(session, match: CricsheetMatch) -> List[str]:
    """Other ids for the same date and teams: the same match under a different key."""
    teams = {team_key(canonical_team(t)) for t in match.info['teams']}
    rows = session.execute(text("""
        SELECT id, team1, team2 FROM matches WHERE date = :d AND id <> :id
        UNION
        SELECT DISTINCT p_match, team_bat, team_bowl FROM delivery_details
        WHERE match_date = :ds AND p_match <> :id  -- match_date is text, 'YYYY-MM-DD'
    """), {'d': match.date, 'ds': match.date.isoformat(), 'id': match.match_id}).fetchall()
    return sorted({r[0] for r in rows if {team_key(r[1]), team_key(r[2])} == teams})


def write_match(session, stats_writer, match: CricsheetMatch, name_of) -> Dict:
    """One match in one transaction: matches row, deliveries, stats."""
    from models import Delivery, Match

    session.add(Match(**match_row(match, name_of)))
    session.flush()
    session.bulk_insert_mappings(Delivery, legacy_deliveries(match, name_of))
    return stats_writer.write_stats_for_deliveries(session, match.match_id, stat_deliveries(match, name_of))


def run(source: str, only_ids: Optional[List[str]] = None, dry_run: bool = False,
        people_source: str = PEOPLE_URL, post_steps: bool = True) -> Dict:
    from database import get_database_connection
    from sync_stats_from_dd import StatsFromDeliveryDetails

    summary = defaultdict(int)
    matches = read_archive(source)
    if only_ids:
        matches = [m for m in matches if m.match_id in set(only_ids)]
    summary['in_archive'] = len(matches)

    in_scope = []
    for m in matches:
        reason = scope_reason(m)
        if reason:
            summary['out_of_scope'] += 1
            logger.debug(f"{m.match_id}: skipped, {reason}")
        else:
            in_scope.append(m)

    _, SessionLocal = get_database_connection()
    session = SessionLocal()
    try:
        have = existing_ids(session, [m.match_id for m in in_scope])
        summary['already_loaded'] = sum(1 for m in in_scope if m.match_id in have)
        candidates = [m for m in in_scope if m.match_id not in have]

        to_load = []
        for m in candidates:
            clash = same_fixture_ids(session, m)
            if clash:
                summary['same_fixture_other_id'] += 1
                logger.warning(f"REVIEW {m.match_id} ({m.date} {' v '.join(m.info['teams'])}): "
                               f"same date and teams already loaded as {', '.join(clash)}; skipped")
            else:
                to_load.append(m)

        if not to_load:
            logger.info("Nothing new to load from Cricsheet")
            return dict(summary)

        name_of = NameResolver.build(session, to_load, read_people_register(people_source))
        stats_writer = StatsFromDeliveryDetails()
        for m in to_load:
            label = f"{m.match_id} {m.date} {m.fmt} {' v '.join(m.info['teams'])}"
            if dry_run:
                logger.info(f"Would load {label}")
                summary['would_load'] += 1
                continue
            try:
                result = write_match(session, stats_writer, m, name_of)
                session.commit()
                summary['loaded'] += 1
                logger.info(f"Loaded {label}: {result['batting']} batting, {result['bowling']} bowling rows")
            except Exception as e:
                session.rollback()
                summary['errors'] += 1
                logger.error(f"Failed {label}: {e}")
    finally:
        session.close()

    if summary['loaded'] and post_steps:
        _post_steps()
    return dict(summary)


def _post_steps() -> None:
    """The table-wide steps the delivery-details sync runs after creating matches, less its
    league-name step: LEAGUE_BUCKETS already writes the feed's buckets, and fix_league_names is
    interactive and would rename them."""
    def venues():
        from venue_standardization import standardize_venues
        standardize_venues()

    def teams():
        from team_standardization import standardize_teams
        standardize_teams()

    def elo():
        from elo_update_service import ELOUpdateService
        result = ELOUpdateService().calculate_missing_elo_ratings()
        logger.info(f"ELO updated: {result.get('updated', 0)}")

    for label, step in (('venue standardizing', venues), ('team standardizing', teams), ('ELO', elo)):
        try:
            step()
        except Exception as e:  # same tolerance as run_full_dd_sync: never fail the load over these
            logger.warning(f"{label} failed: {e}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--days', type=int, default=7, choices=RECENT_DAYS,
                        help="Cricsheet's recently-added window (default 7)")
    parser.add_argument('--zip', help='A Cricsheet zip (path or URL) instead of the recently-added archive')
    parser.add_argument('--people', default=PEOPLE_URL, help="Cricsheet's people register (path or URL)")
    parser.add_argument('--ids', nargs='*', help='Only these match ids')
    parser.add_argument('--dry-run', action='store_true', help='Report what would load; write nothing')
    parser.add_argument('--skip-post', action='store_true', help='Skip venue/team/league standardizing and ELO')
    args = parser.parse_args()

    source = args.zip or f"{CRICSHEET}/downloads/recently_added_{args.days}_male_json.zip"
    summary = run(source, only_ids=args.ids, dry_run=args.dry_run,
                  people_source=args.people, post_steps=not args.skip_post)
    print("Cricsheet fallback:", ", ".join(f"{k} {v}" for k, v in summary.items()))
    return 1 if summary.get('errors') else 0


if __name__ == '__main__':
    sys.exit(main())
