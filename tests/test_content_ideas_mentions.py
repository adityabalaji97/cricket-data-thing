from services.content_ideas import _mentions


def test_metric_words_are_not_names():
    assert _mentions("Dot ball % v boundary % for IPL batters since 2024, 500+ balls") == []
    assert _mentions("Glenn Maxwell impact per 100 balls by season since 2018") == ["Glenn", "Maxwell"]
