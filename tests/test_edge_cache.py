import importlib

import pytest


@pytest.fixture(scope="module")
def policy():
    return importlib.import_module("main").cache_policy


@pytest.mark.parametrize("path,cached", [
    ("/venues", "s-maxage=86400"), ("/teams/", "s-maxage=86400"), ("/formats", "s-maxage=86400"),
    ("/matches/1539436/scorecard", "s-maxage=3600"), ("/matches/1539436/recap", "s-maxage=3600"),
])
def test_cached(policy, path, cached):
    assert cached in policy(path)


@pytest.mark.parametrize("path", ["/venues/stats", "/teams/India/matches", "/player/V Kohli/summary", "/events",
                                  "/matches/1/scorecard/extra", "/admin/usage"])
def test_not_cached(policy, path):
    assert policy(path) is None
