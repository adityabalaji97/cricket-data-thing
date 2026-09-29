from services import jev_client, search_routing

SUGGESTIONS = [{"name": "AR Sharma", "display_name": "AR Sharma", "type": "player"},
               {"name": "Abhishek Sharma", "display_name": "Abhishek Sharma", "type": "player"}]


def _answers(lookup, choice, entity_p):
    return {"intent": {"probabilities": {"lookup": lookup, "question": 1 - lookup}},
            "entity": {"choice": choice, "probabilities": {choice: entity_p}}}


def test_confident_lookup_routes_to_the_chosen_entity(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test")
    monkeypatch.setattr(search_routing, "search_entities", lambda q, db, limit=8: SUGGESTIONS)
    monkeypatch.setattr(jev_client, "ask", lambda *a, **k: _answers(0.95, "c1", 0.9))
    result = search_routing.route_search("abhishek sharma batting", None)
    assert result["route"] == "entity" and result["item"]["name"] == "Abhishek Sharma"


def test_questions_and_unsure_answers_go_to_the_query_builder(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test")
    monkeypatch.setattr(search_routing, "search_entities", lambda q, db, limit=8: SUGGESTIONS)
    monkeypatch.setattr(jev_client, "ask", lambda *a, **k: _answers(0.2, "c1", 0.9))
    assert search_routing.route_search("best death bowlers", None)["route"] == "query"
    monkeypatch.setattr(jev_client, "ask", lambda *a, **k: _answers(0.9, "c0", 0.4))
    assert search_routing.route_search("sharma", None)["route"] == "query"
    monkeypatch.setattr(jev_client, "ask", lambda *a, **k: None)
    assert search_routing.route_search("abhishek", None)["route"] == "query"


def test_without_jev_everything_goes_to_the_query_builder(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    assert search_routing.route_search("abhishek sharma batting", None) == {"route": "query"}
