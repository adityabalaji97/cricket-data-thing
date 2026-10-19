from services import ig_links
from services.ig_posts import series_preview as P, spotlight

SPEC = spotlight.SPECS["nz-india-t20i"]


def ground(label):
    return next(g for g in SPEC["grounds"] if g["label"] == label)


def test_wellington_is_one_ground_under_every_name():
    names = set(ground("Wellington")["names"])
    assert {"Sky Stadium, Wellington", "Westpac Stadium, Wellington", "Westpac Stadium",
            "WestpacTrust Stadium, Wellington", "Henry Stadium, Wellington"} <= names
    assert "Basin Reserve, Wellington" not in names  # a different ground


def test_eden_park_outer_oval_is_another_ground():
    assert ground("Eden Park")["names"] == ["Eden Park, Auckland"]


def test_thin_grounds_are_flagged():
    games = {"Hagley Oval": 59, "Wellington": 11}
    assert P._label(ground("Hagley Oval"), games) == "Hagley Oval"
    assert P._label(ground("Wellington"), games) == "Wellington*"


def test_a_series_post_never_links_to_a_player_page():
    fact = {"kind": "spotlight", "subject": "India in New Zealand T20Is", "subject_role": "series"}
    assert "/player?" not in ig_links.post_link(fact)
    assert "/venue?venue=Hagley" in ig_links.post_link({**fact, "link": SPEC["link"]})
