import { useEffect, useState } from 'react';
import axios from 'axios';
import config from '../config';
import { useFormat } from '../context/FormatContext';

/**
 * GET /match-preview/{venue}/{team1}/{team2}/cards: the story-style preview's chapters of cards
 * (services/preview_cards). Same filters as useMatchPreview, so the story and the classic page
 * describe the same matches.
 *
 * Identical requests share one response (MATCH_PREVIEW_VIZ_PLAN.md performance budget: nothing
 * fetched twice). The page remounts the preview while it reloads venue data, and React's
 * development mode runs effects twice; both used to send the same story request again.
 */
const responses = new Map(); // request key -> promise of the story

const fetchStory = (url, params) => {
  const key = `${url}?${JSON.stringify(params)}`;
  if (!responses.has(key)) {
    const request = axios.get(url, { params }).then((response) => response.data);
    request.catch(() => responses.delete(key)); // a failure is retried next time
    responses.set(key, request);
  }
  return responses.get(key);
};
const useStoryCards = ({
  venue, team1, team2, team1Short, team2Short, startDate, endDate,
  includeInternational = true, topTeams = 20, dayNightFilter = 'all', enabled = true,
}) => {
  const { pinnedFormatParams: previewFormat } = useFormat();
  const [state, setState] = useState({ data: null, loading: false, error: null });

  useEffect(() => {
    if (!enabled || !venue || !team1 || !team2) return undefined;
    let cancelled = false;
    setState({ data: null, loading: true, error: null });
    fetchStory(
      `${config.API_URL}/match-preview/${encodeURIComponent(venue)}/${encodeURIComponent(team1)}/${encodeURIComponent(team2)}/cards`,
      {
        ...(startDate ? { start_date: startDate } : {}),
        ...(endDate ? { end_date: endDate } : {}),
        include_international: includeInternational,
        top_teams: topTeams,
        format: previewFormat.format,
        ...(team1Short ? { team1_short: team1Short } : {}),
        ...(team2Short ? { team2_short: team2Short } : {}),
        ...(dayNightFilter !== 'all' ? { day_or_night: dayNightFilter } : {}),
      },
    )
      .then((data) => { if (!cancelled) setState({ data, loading: false, error: null }); })
      .catch(() => { if (!cancelled) setState({ data: null, loading: false, error: 'Failed to load the story' }); });
    return () => { cancelled = true; };
  }, [enabled, venue, team1, team2, team1Short, team2Short, startDate, endDate, includeInternational, topTeams,
      dayNightFilter, previewFormat.format]);

  return state;
};

export default useStoryCards;
