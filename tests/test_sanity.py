"""Endpoint smoke tests — verify routes respond without 500 errors.

These use a mocked DB, so they won't return real data but will catch
import errors, missing dependencies, broken routes, and startup crashes.
A 4xx response is acceptable; a 500 is not.
"""

import pytest


def _assert_not_500(response, label=""):
    assert response.status_code != 500, (
        f"{label} returned 500: {response.text[:300]}"
    )


class TestHealthAndLists:
    def test_root(self, client):
        r = client.get("/")
        _assert_not_500(r, "GET /")

    def test_venues_list(self, client):
        r = client.get("/venues/")
        _assert_not_500(r, "GET /venues/")

    def test_teams_list(self, client):
        r = client.get("/teams/")
        _assert_not_500(r, "GET /teams/")

    def test_competitions(self, client):
        r = client.get("/competitions")
        _assert_not_500(r, "GET /competitions")


class TestVenueEndpoints:
    def test_venue_stats(self, client):
        r = client.get("/venues/TestVenue/stats")
        _assert_not_500(r, "GET /venues/{venue}/stats")

    def test_venue_history(self, client):
        r = client.get("/venues/TestVenue/teams/TeamA/TeamB/history")
        _assert_not_500(r, "GET /venues/{venue}/teams/{t1}/{t2}/history")

    def test_venue_fantasy_stats(self, client):
        r = client.get("/venues/TestVenue/teams/TeamA/TeamB/fantasy_stats")
        _assert_not_500(r, "GET /venues/{venue}/teams/{t1}/{t2}/fantasy_stats")


class TestMatchPreview:
    def test_match_preview(self, client):
        r = client.get("/match-preview/TestVenue/TeamA/TeamB")
        _assert_not_500(r, "GET /match-preview/{venue}/{t1}/{t2}")


class TestPlayerEndpoints:
    def test_players_search(self, client):
        r = client.get("/players/search?q=test")
        _assert_not_500(r, "GET /players/search")

    def test_player_profile(self, client):
        r = client.get("/players/TestPlayer/profile")
        _assert_not_500(r, "GET /players/{player}/profile")


class TestMatchupsEndpoint:
    def test_matchups(self, client):
        r = client.get("/matchups?team1=TeamA&team2=TeamB")
        _assert_not_500(r, "GET /matchups")


class TestSearchEndpoint:
    def test_search(self, client):
        r = client.get("/search?q=test")
        _assert_not_500(r, "GET /search")
