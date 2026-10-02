import config from '../config';

let leaguesPromise = null;

/** Every league value from /competitions, fetched once per page load. */
export const fetchAllLeagueValues = () => {
  if (!leaguesPromise) {
    leaguesPromise = fetch(`${config.API_URL}/competitions`)
      .then((response) => (response.ok ? response.json() : Promise.reject(response.status)))
      .then((payload) => (payload?.leagues || []).map((league) => league.value).filter(Boolean))
      .catch((err) => {
        leaguesPromise = null;
        throw err;
      });
  }
  return leaguesPromise;
};

/**
 * Append the page's competition filter to query-builder params with the page's meaning.
 *
 * The profile/preview filter means "these leagues (none chosen = all leagues), plus top-N
 * internationals when ticked". The query builder ORs `leagues` with `include_international`, so
 * "no leagues + internationals" there means internationals ONLY -- which is why a profile with
 * the default filter showed Kohli's Impact as 150 balls of the 2024 T20 World Cup. "All leagues"
 * is therefore always sent as the explicit league list.
 */
export const appendCompetitionParams = async (params, competitionFilters) => {
  const chosen = competitionFilters?.leagues || [];
  const international = Boolean(competitionFilters?.international);
  let leagues = chosen;
  if (!chosen.length) {
    try {
      leagues = await fetchAllLeagueValues();
    } catch {
      leagues = [];
    }
  }
  leagues.forEach((league) => params.append('leagues', league));
  if (international) {
    params.set('include_international', 'true');
    if (competitionFilters?.topTeams) params.set('top_teams', String(competitionFilters.topTeams));
  }
  return params;
};
