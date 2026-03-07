def test_boundary_shape_endpoint_response_schema(client, monkeypatch):
    sample_payload = {
        "venue": "Test Venue",
        "filters": {
            "start_date": "2024-01-01",
            "end_date": "2026-03-07",
            "leagues": ["IPL"],
            "include_international": False,
            "top_teams": None,
            "min_matches": 20,
            "angle_bin_size": 15,
        },
        "quality": {
            "fours_total": 1000,
            "fours_with_xy": 980,
            "fours_nonzero_xy": 720,
            "nonzero_rate": 0.7347,
        },
        "sample": {
            "matches_total": 120,
            "matches_with_nonzero4": 85,
            "matches_used": 42,
        },
        "profile_bins": [
            {
                "angle_bin": 0,
                "angle_start_deg": 0,
                "angle_mid_deg": 7.5,
                "r_median": 183.2,
                "r_iqr": 7.8,
                "bin_coverage_pct": 90.0,
            }
        ],
        "summary": {
            "mean_boundary_r": 183.2,
            "mean_bin_sd": 5.9,
            "relative_sd": 0.0322,
            "avg_bins_with_data": 14.2,
        },
        "confidence": {
            "confidence_score": 81.7,
            "coverage_score": 78.4,
            "sample_score": 74.8,
            "stability_score": 87.9,
            "warning_flags": ["LOW_SAMPLE"],
        },
        "diagnostics": {
            "surface_regime_signal": "single_likely",
            "reason": "Inter-match contour volatility is moderate for this venue sample.",
        },
    }

    monkeypatch.setattr(
        "routers.visualizations.get_venue_boundary_shape_data",
        lambda **_: sample_payload,
    )

    response = client.get("/visualizations/venue/TestVenue/boundary-shape")
    assert response.status_code == 200
    payload = response.json()

    assert payload["venue"] == "Test Venue"
    assert "quality" in payload
    assert "sample" in payload
    assert "profile_bins" in payload
    assert "summary" in payload
    assert "confidence" in payload
    assert "diagnostics" in payload


def test_boundary_shape_endpoint_angle_bin_validation(client):
    response = client.get("/visualizations/venue/TestVenue/boundary-shape?angle_bin_size=13")
    assert response.status_code == 422
