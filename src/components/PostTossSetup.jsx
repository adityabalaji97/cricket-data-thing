import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  Radio,
  RadioGroup,
  FormControlLabel,
  Stack,
  TextField,
  Typography,
  Chip,
} from '@mui/material';
import config from '../config';
import CondensedName from './common/CondensedName';

const uniqueNames = (names = []) => {
  const seen = new Set();
  const output = [];
  names.forEach((name) => {
    const clean = String(name || '').trim();
    if (!clean) return;
    const key = clean.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    output.push(clean);
  });
  return output;
};

const isSameTeam = (a = '', b = '') => (
  String(a || '').trim().toLowerCase() === String(b || '').trim().toLowerCase()
);

const PostTossSetup = ({
  venue,
  team1Identifier,
  team2Identifier,
  dayNightFilter = 'all',
  isMobile = false,
  onApplyResult,
}) => {
  const [loadingRosters, setLoadingRosters] = useState(false);
  const [rosterError, setRosterError] = useState(null);
  const [team1Roster, setTeam1Roster] = useState([]);
  const [team2Roster, setTeam2Roster] = useState([]);

  const [cricinfoUrl, setCricinfoUrl] = useState('');
  const [scrapeLoading, setScrapeLoading] = useState(false);
  const [scrapeMessage, setScrapeMessage] = useState(null);
  const [inputSource, setInputSource] = useState('manual');

  const [battingFirstTeam, setBattingFirstTeam] = useState(team1Identifier || '');
  const [team1Xi, setTeam1Xi] = useState([]);
  const [team2Xi, setTeam2Xi] = useState([]);
  const [impactSubs, setImpactSubs] = useState([]);

  const [applyLoading, setApplyLoading] = useState(false);
  const [applyError, setApplyError] = useState(null);
  const normalizedDayNight = dayNightFilter === 'day' || dayNightFilter === 'night'
    ? dayNightFilter
    : null;

  const allPlayers = useMemo(
    () => uniqueNames([...(team1Roster || []), ...(team2Roster || [])]),
    [team1Roster, team2Roster]
  );

  useEffect(() => {
    if (!team1Identifier || !team2Identifier) return;
    let cancelled = false;

    const loadRosters = async () => {
      setLoadingRosters(true);
      setRosterError(null);
      try {
        const [team1Res, team2Res] = await Promise.all([
          axios.get(`${config.API_URL}/teams/${encodeURIComponent(team1Identifier)}/roster`, {
            params: normalizedDayNight ? { day_or_night: normalizedDayNight } : {},
          }),
          axios.get(`${config.API_URL}/teams/${encodeURIComponent(team2Identifier)}/roster`, {
            params: normalizedDayNight ? { day_or_night: normalizedDayNight } : {},
          }),
        ]);

        if (cancelled) return;

        const team1Players = (team1Res.data?.players || []).map((row) => row?.name).filter(Boolean);
        const team2Players = (team2Res.data?.players || []).map((row) => row?.name).filter(Boolean);

        const nextTeam1 = uniqueNames(team1Players);
        const nextTeam2 = uniqueNames(team2Players);
        setTeam1Roster(nextTeam1);
        setTeam2Roster(nextTeam2);
        setTeam1Xi(nextTeam1);
        setTeam2Xi(nextTeam2);
        setBattingFirstTeam(team1Identifier);
        setInputSource('manual');
      } catch (err) {
        if (cancelled) return;
        console.error('Failed to load team rosters', err);
        setRosterError('Failed to load team rosters. You can still type player names manually.');
      } finally {
        if (!cancelled) {
          setLoadingRosters(false);
        }
      }
    };

    loadRosters();
    return () => {
      cancelled = true;
    };
  }, [team1Identifier, team2Identifier, normalizedDayNight]);

  const handleScrape = async () => {
    const url = String(cricinfoUrl || '').trim();
    if (!url) return;
    setScrapeLoading(true);
    setScrapeMessage(null);
    try {
      const response = await axios.post(`${config.API_URL}/match-preview/scrape-cricinfo`, { url });
      const data = response.data || {};

      const scrapedTeam1 = data.team1 || '';
      const scrapedTeam2 = data.team2 || '';
      const scrapedBatFirst = data.batting_first_team || '';

      const canMapTeamsDirectly =
        (isSameTeam(scrapedTeam1, team1Identifier) && isSameTeam(scrapedTeam2, team2Identifier))
        || (isSameTeam(scrapedTeam1, team2Identifier) && isSameTeam(scrapedTeam2, team1Identifier));

      const scrapedTeam1Xi = uniqueNames(data.team1_xi || []);
      const scrapedTeam2Xi = uniqueNames(data.team2_xi || []);
      const scrapedImpact = uniqueNames(data.impact_subs || []);

      if (canMapTeamsDirectly) {
        if (isSameTeam(scrapedTeam1, team1Identifier)) {
          if (scrapedTeam1Xi.length) setTeam1Xi(scrapedTeam1Xi);
          if (scrapedTeam2Xi.length) setTeam2Xi(scrapedTeam2Xi);
        } else {
          if (scrapedTeam1Xi.length) setTeam2Xi(scrapedTeam1Xi);
          if (scrapedTeam2Xi.length) setTeam1Xi(scrapedTeam2Xi);
        }
      } else {
        // If mapping is uncertain, still populate likely values without overwriting both sides aggressively.
        if (scrapedTeam1Xi.length && !team1Xi.length) setTeam1Xi(scrapedTeam1Xi);
        if (scrapedTeam2Xi.length && !team2Xi.length) setTeam2Xi(scrapedTeam2Xi);
      }

      if (scrapedImpact.length) {
        setImpactSubs(scrapedImpact);
      }

      if (scrapedBatFirst) {
        if (isSameTeam(scrapedBatFirst, team1Identifier)) setBattingFirstTeam(team1Identifier);
        if (isSameTeam(scrapedBatFirst, team2Identifier)) setBattingFirstTeam(team2Identifier);
      }

      if (data.success) {
        setInputSource('scraped');
        setScrapeMessage(`Auto-fetch succeeded (${data.source || 'espn_api'}). Review and edit if needed.`);
      } else {
        setInputSource('manual');
        setScrapeMessage('No toss/XI data available yet for this URL. Fill details manually below.');
      }
    } catch (err) {
      console.error('Cricinfo scrape failed', err);
      setInputSource('manual');
      setScrapeMessage('Auto-fetch failed. Fill details manually below.');
    } finally {
      setScrapeLoading(false);
    }
  };

  const handleApply = async () => {
    setApplyLoading(true);
    setApplyError(null);
    try {
      const response = await axios.post(`${config.API_URL}/match-preview/post-toss`, {
        venue,
        team1_id: team1Identifier,
        team2_id: team2Identifier,
        batting_first_team: battingFirstTeam,
        team1_xi: uniqueNames(team1Xi),
        team2_xi: uniqueNames(team2Xi),
        impact_subs: uniqueNames(impactSubs),
        source: inputSource,
        ...(normalizedDayNight ? { day_or_night: normalizedDayNight } : {}),
        ...(normalizedDayNight === 'day'
          ? { general_window_years: 4, venue_window_years: 5 }
          : {}),
      });
      onApplyResult?.(response.data);
    } catch (err) {
      console.error('Post-toss apply failed', err);
      const message = err?.response?.data?.detail || 'Failed to apply post-toss analysis.';
      setApplyError(message);
    } finally {
      setApplyLoading(false);
    }
  };

  return (
    <Box sx={{ mt: 2, p: { xs: 1.5, sm: 2 }, borderRadius: 2, border: '1px solid rgba(0,0,0,0.08)', bgcolor: 'rgba(0,0,0,0.015)' }}>
      <Typography variant={isMobile ? 'subtitle1' : 'h6'} sx={{ mb: 1 }}>
        Post-Toss Setup
      </Typography>

      <Stack direction={isMobile ? 'column' : 'row'} spacing={1} sx={{ mb: 1.5 }}>
        <TextField
          size="small"
          fullWidth
          label="Cricinfo URL (optional)"
          value={cricinfoUrl}
          onChange={(e) => setCricinfoUrl(e.target.value)}
        />
        <Button
          variant="outlined"
          onClick={handleScrape}
          disabled={scrapeLoading || !cricinfoUrl.trim()}
        >
          {scrapeLoading ? 'Fetching...' : 'Auto-fetch'}
        </Button>
      </Stack>

      {scrapeMessage && (
        <Alert severity="info" sx={{ mb: 1.5 }}>
          {scrapeMessage}
        </Alert>
      )}

      {rosterError && (
        <Alert severity="warning" sx={{ mb: 1.5 }}>
          {rosterError}
        </Alert>
      )}

      <Typography variant="body2" color="text.secondary" sx={{ mb: 0.75 }}>
        Who bats first?
      </Typography>
      <RadioGroup
        row={!isMobile}
        value={battingFirstTeam}
        onChange={(e) => setBattingFirstTeam(e.target.value)}
        sx={{ mb: 1 }}
      >
        <FormControlLabel
          value={team1Identifier}
          control={<Radio size="small" />}
          label={<CondensedName name={team1Identifier} type="team" />}
        />
        <FormControlLabel
          value={team2Identifier}
          control={<Radio size="small" />}
          label={<CondensedName name={team2Identifier} type="team" />}
        />
      </RadioGroup>

      <Stack direction="column" spacing={1.5}>
        <Autocomplete
          multiple
          options={team1Roster}
          freeSolo
          loading={loadingRosters}
          value={team1Xi}
          onChange={(event, value) => setTeam1Xi(uniqueNames(value))}
          renderInput={(params) => (
            <TextField
              {...params}
              size="small"
              label={`${team1Identifier} Playing XI / impact pool`}
              placeholder="Select players"
            />
          )}
        />

        <Autocomplete
          multiple
          options={team2Roster}
          freeSolo
          loading={loadingRosters}
          value={team2Xi}
          onChange={(event, value) => setTeam2Xi(uniqueNames(value))}
          renderInput={(params) => (
            <TextField
              {...params}
              size="small"
              label={`${team2Identifier} Playing XI / impact pool`}
              placeholder="Select players"
            />
          )}
        />

        <Autocomplete
          multiple
          options={allPlayers}
          freeSolo
          value={impactSubs}
          onChange={(event, value) => setImpactSubs(uniqueNames(value))}
          renderInput={(params) => (
            <TextField
              {...params}
              size="small"
              label="Impact subs (optional)"
              placeholder="Add impact substitutes"
            />
          )}
        />
      </Stack>

      <Stack direction={isMobile ? 'column' : 'row'} spacing={1} sx={{ mt: 1.5, mb: 1 }}>
        <Chip size="small" label={`${team1Identifier} selected: ${team1Xi.length}`} />
        <Chip size="small" label={`${team2Identifier} selected: ${team2Xi.length}`} />
      </Stack>

      {applyError && (
        <Alert severity="error" sx={{ mb: 1 }}>
          {applyError}
        </Alert>
      )}

      <Button
        variant="contained"
        onClick={handleApply}
        disabled={applyLoading || !battingFirstTeam || !team1Xi.length || !team2Xi.length}
      >
        {applyLoading ? (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CircularProgress size={14} color="inherit" />
            Applying...
          </Box>
        ) : (
          'Apply Post-Toss'
        )}
      </Button>
    </Box>
  );
};

export default PostTossSetup;
