"""
Who is overseas where (shared by the 19-0 data build and Pick your XI, 13 Nov 2026): a player's years of evidence that
he's foreign to a home country, and whether that makes a given season's card overseas. See overseas_years for the
evidence and the cases that shaped it (Vaas, Warne, Mascarenhas, Karthik's World XI, Harmeet Singh, Tim David).
"""
from __future__ import annotations

INDIAN_COMPS = ("Indian Premier League", "IPL", "Syed Mushtaq Ali Trophy", "SMAT", "SMA TROPHY", "SMA TROPHY FINAL")



FULL_MEMBERS = ("Australia", "England", "South Africa", "New Zealand", "Pakistan", "Sri Lanka", "West Indies", "Bangladesh",
                "Zimbabwe", "Afghanistan", "Ireland")


def overseas_years(db, home: str = "India", abroad_signal: bool = True):
    """Outside the IPL (abroad_signal off) only full-member internationals count: a local can play for an associate
    first (Tim David, Singapore, then Australia; a BBL local throughout). {display name: years with evidence he was an overseas player} (12 Nov 2026). Evidence, any of:
      - an international for a side other than India, by player id on the ball-by-ball feed (2015 on): ids, because
        names collide (a Mandeep Singh plays for Norway);
      - on the older scorecards (names only), an international for a full-member side (Chaminda Vaas);
      - an IPL auction entry, by id, with a country other than India;
      - a domestic or franchise league outside India before 2019 (Shane Warne, BBL; Dimitri Mascarenhas, county T20).
    Composite sides (World XI) don't count (Dinesh Karthik). A card is overseas only if the evidence is near its season
    (CARD_WINDOW): players who emigrated later (Harmeet Singh, USA from 2024; Unmukt Chand) were Indian then."""
    from collections import defaultdict

    from sqlalchemy import text

    years = defaultdict(set)
    rows = db.execute(text("""
        SELECT p.display_name, x.y FROM player_identity p JOIN (
            SELECT p_bat AS pid, SUBSTRING(match_date, 1, 4)::int y FROM delivery_details WHERE competition IN ('T20I', 'ODI')
                AND team_bat <> :home AND team_bat NOT ILIKE '%XI%' AND p_bat IS NOT NULL AND (:any_side OR team_bat = ANY(:full))
            UNION SELECT p_bowl, SUBSTRING(match_date, 1, 4)::int FROM delivery_details WHERE competition IN ('T20I', 'ODI')
                AND team_bowl <> :home AND team_bowl NOT ILIKE '%XI%' AND p_bowl IS NOT NULL AND (:any_side OR team_bowl = ANY(:full))
            UNION SELECT pid, year FROM auction_lots WHERE pid IS NOT NULL AND country IS NOT NULL AND country <> :home AND (:any_side OR country = ANY(:full))) x
        ON x.pid = p.pid"""), {"home": home, "any_side": abroad_signal, "full": list(FULL_MEMBERS)}).fetchall()
    rows += db.execute(text("""
        SELECT d.batter, EXTRACT(YEAR FROM m.date)::int FROM deliveries d JOIN matches m ON m.id = d.match_id
            WHERE m.match_type = 'international' AND d.batting_team = ANY(:full)
        UNION SELECT d.bowler, EXTRACT(YEAR FROM m.date)::int FROM deliveries d JOIN matches m ON m.id = d.match_id
            WHERE m.match_type = 'international' AND d.bowling_team = ANY(:full)
        UNION SELECT d.batter, EXTRACT(YEAR FROM m.date)::int FROM deliveries d JOIN matches m ON m.id = d.match_id
            WHERE :abroad AND m.match_type = 'league' AND m.date < '2019-01-01' AND NOT (m.competition = ANY(:ind))
        UNION SELECT d.bowler, EXTRACT(YEAR FROM m.date)::int FROM deliveries d JOIN matches m ON m.id = d.match_id
            WHERE :abroad AND m.match_type = 'league' AND m.date < '2019-01-01' AND NOT (m.competition = ANY(:ind))"""),
        {"full": [t for t in FULL_MEMBERS if t != home], "ind": list(INDIAN_COMPS), "abroad": abroad_signal}).fetchall()
    alias = aliases(db)
    for name, y in rows:
        years[name].add(int(y))
        if name in alias:  # the scorecards' short names ("ST Jayasuriya") under the cards' names too
            years[alias[name]].add(int(y))
    return years


def aliases(db):
    """{scorecard name: our display name} (player_aliases: "RV Uthappa" -> "Robin Uthappa")."""
    from sqlalchemy import text

    return dict(db.execute(text("SELECT player_name, alias_name FROM player_aliases WHERE alias_name IS NOT NULL")).fetchall())


CARD_WINDOW = (10, 3)  # overseas evidence from 10 years before a season to 3 after makes that season's card overseas


def is_overseas(years, name, season):
    s = int(str(season)[:4])  # "2024-25" (a BBL season): its first year
    return any(s - CARD_WINDOW[0] <= y <= s + CARD_WINDOW[1] for y in years.get(name, ()))
