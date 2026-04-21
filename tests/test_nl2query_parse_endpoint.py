from routers import nl2query as nl2query_router


def test_parse_endpoint_includes_structured_interpretation(client, monkeypatch):
    monkeypatch.setattr(
        nl2query_router,
        'parse_nl_query',
        lambda query, db=None: {
            'success': True,
            'filters': {'batters': ['Virat Kohli'], 'query_mode': 'delivery'},
            'group_by': ['batter'],
            'explanation': 'Showing Kohli batting analysis',
            'confidence': 'high',
            'suggestions': ['grouped by venue'],
            'interpretation': {
                'summary': 'Showing Kohli batting analysis',
                'parsed_entities': [
                    {'type': 'player', 'value': 'Virat Kohli', 'matched_from': 'kohli'}
                ],
                'suggestions': ['grouped by venue'],
            },
        },
    )
    monkeypatch.setattr(nl2query_router, 'log_nl_query_event_background', lambda **kwargs: None)

    response = client.post('/nl2query/parse', json={'query': 'kohli by year'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['success'] is True
    assert payload['interpretation']['summary'] == 'Showing Kohli batting analysis'
    assert payload['interpretation']['parsed_entities'][0]['type'] == 'player'
