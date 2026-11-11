"""IPL squads with the moves since the last auction (services/ipl_squads.py)."""
from services import ipl_squads as S


def test_a_two_way_trade_is_one_deal(monkeypatch):
    rows = [
        {"id": 1, "deal": "pbks-mi-1", "player_name": "Hardik Pandya", "pid": 1, "from_team": "MI", "to_team": "PBKS",
         "price_lakh": 1635, "kind": "trade", "state": "reported", "source": "reports", "announced": None},
        {"id": 2, "deal": "pbks-mi-1", "player_name": "Arshdeep Singh", "pid": 2, "from_team": "PBKS", "to_team": "MI",
         "price_lakh": 1800, "kind": "trade", "state": "reported", "source": "reports", "announced": None},
    ]
    monkeypatch.setattr(S, "moves", lambda db, code, season=2027, as_of=None, reported=True: rows if reported else [])
    d = S.deals(None, "PBKS")
    assert d == [{"other": "MI", "ins": ["Hardik Pandya"], "outs": ["Arshdeep Singh"], "state": "reported",
                  "source": "reports", "when": None}]
    assert S.deals(None, "PBKS", reported=False) == []
