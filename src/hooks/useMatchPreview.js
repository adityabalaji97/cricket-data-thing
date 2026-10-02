import { useEffect, useState } from 'react';
import axios from 'axios';
import config from '../config';
import { useFormat } from '../context/FormatContext';

/**
 * GET /match-preview/{venue}/{team1}/{team2}. Shared by the preview card and the "What to expect"
 * strip, so the page makes one request however many places show it.
 */
const useMatchPreview = ({
  venue,
  team1,
  team2,
  startDate,
  endDate,
  includeInternational = true,
  topTeams = 20,
  dayNightFilter = 'all',
  enabled = true,
}) => {
  // Pinned: a preview is a single fixture, so 'ALL' has no meaning and the endpoint rejects it.
  const { pinnedFormatParams: previewFormat } = useFormat();
  const [state, setState] = useState({ data: null, loading: false, error: null });

  useEffect(() => {
    if (!enabled || !venue || !team1 || !team2) return undefined;
    let cancelled = false;
    setState({ data: null, loading: true, error: null });
    axios.get(
      `${config.API_URL}/match-preview/${encodeURIComponent(venue)}/${encodeURIComponent(team1)}/${encodeURIComponent(team2)}`,
      {
        params: {
          ...(startDate ? { start_date: startDate } : {}),
          ...(endDate ? { end_date: endDate } : {}),
          include_international: includeInternational,
          top_teams: topTeams,
          format: previewFormat.format,
          gender: previewFormat.gender,
          ...(dayNightFilter !== 'all' ? { day_or_night: dayNightFilter } : {}),
        },
      },
    )
      .then((response) => { if (!cancelled) setState({ data: response.data, loading: false, error: null }); })
      .catch((err) => {
        console.error('Error fetching match preview:', err);
        if (!cancelled) setState({ data: null, loading: false, error: 'Failed to load match preview' });
      });
    return () => { cancelled = true; };
  }, [enabled, venue, team1, team2, startDate, endDate, includeInternational, topTeams, dayNightFilter,
      previewFormat.format, previewFormat.gender]);

  return state;
};

export default useMatchPreview;
