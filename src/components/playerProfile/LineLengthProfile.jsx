import React, { useState, useEffect } from 'react';
import {
  Card, CardContent, Typography, Box, Tabs, Tab, Tooltip,
  CircularProgress, Alert, useMediaQuery, useTheme
} from '@mui/material';
import config from '../../config';

const MIN_BALLS = 20;

const METRIC_OPTIONS = [
  { value: 'strike_rate', label: 'Strike Rate', shortLabel: 'SR' },
  { value: 'control_pct', label: 'Control %', shortLabel: 'Ctrl%' },
  { value: 'boundary_pct', label: 'Boundary %', shortLabel: 'Bnd%' },
  { value: 'dot_pct', label: 'Dot %', shortLabel: 'Dot%', invertColor: true },
];

const DeltaCell = ({ playerVal, comparisonVal, metric, isMobile }) => {
  if (comparisonVal == null) return <td style={{ color: '#999', textAlign: 'center' }}>-</td>;
  const delta = playerVal - comparisonVal;
  const invertColor = metric.invertColor;
  const isPositive = invertColor ? delta < 0 : delta > 0;
  const color = Math.abs(delta) < 0.5 ? '#888' : isPositive ? '#2e7d32' : '#c62828';
  const sign = delta > 0 ? '+' : '';
  return (
    <Tooltip
      title={
        <Box sx={{ p: 0.5 }}>
          <Typography variant="caption" display="block">Player: {playerVal.toFixed(1)}</Typography>
          <Typography variant="caption" display="block">Comparison: {comparisonVal.toFixed(1)}</Typography>
          <Typography variant="caption" display="block">Delta: {sign}{delta.toFixed(1)}</Typography>
        </Box>
      }
      arrow
    >
      <td style={{
        color,
        fontWeight: 600,
        textAlign: 'center',
        fontSize: isMobile ? '0.75rem' : '0.85rem',
        padding: isMobile ? '4px 6px' : '6px 12px',
      }}>
        {sign}{delta.toFixed(1)}
      </td>
    </Tooltip>
  );
};

const LineLengthProfile = ({ playerName, mode, dateRange, selectedVenue, competitionFilters, isMobile: isMobileProp }) => {
  const theme = useTheme();
  const isMobileQuery = useMediaQuery(theme.breakpoints.down('sm'));
  const isMobile = isMobileProp !== undefined ? isMobileProp : isMobileQuery;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeView, setActiveView] = useState(0); // 0 = length, 1 = line
  const [selectedMetric, setSelectedMetric] = useState(0);
  const [similarPlayers, setSimilarPlayers] = useState([]);

  // Fetch doppelgangers for similar-player comparison
  useEffect(() => {
    if (!playerName) return;
    const fetchDoppelgangers = async () => {
      try {
        const params = new URLSearchParams();
        params.append('top_n', '5');
        if (dateRange?.start) params.append('start_date', dateRange.start);
        if (dateRange?.end) params.append('end_date', dateRange.end);
        const res = await fetch(
          `${config.API_URL}/search/player/${encodeURIComponent(playerName)}/doppelgangers?${params}`
        );
        if (res.ok) {
          const json = await res.json();
          const names = (json.most_similar || []).map(d => d.player_name).filter(Boolean);
          setSimilarPlayers(names);
        }
      } catch (e) {
        // Non-critical — just skip similar player comparison
        console.warn('Failed to fetch doppelgangers:', e);
      }
    };
    fetchDoppelgangers();
  }, [playerName, dateRange]);

  // Fetch line/length profile
  useEffect(() => {
    if (!playerName) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        params.append('mode', mode);
        if (dateRange?.start) params.append('start_date', dateRange.start);
        if (dateRange?.end) params.append('end_date', dateRange.end);
        if (selectedVenue && selectedVenue !== 'All Venues') params.append('venue', selectedVenue);
        if (competitionFilters?.leagues) {
          competitionFilters.leagues.forEach(l => params.append('leagues', l));
        }
        if (competitionFilters?.international) {
          params.append('include_international', 'true');
        }
        if (competitionFilters?.topTeams) {
          params.append('top_teams', competitionFilters.topTeams);
        }
        similarPlayers.forEach(name => params.append('similar_players', name));

        const url = `${config.API_URL}/player/${encodeURIComponent(playerName)}/line-length-profile?${params}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setData(json);
      } catch (e) {
        console.error('LineLengthProfile fetch error:', e);
        setError('Failed to load line & length data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [playerName, mode, dateRange, selectedVenue, competitionFilters, similarPlayers]);

  if (loading) {
    return (
      <Card>
        <CardContent sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress size={28} />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <Alert severity="error">{error}</Alert>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  const profile = activeView === 0 ? data.length_profile : data.line_profile;
  const metric = METRIC_OPTIONS[selectedMetric];
  const isBowling = mode === 'bowling';
  const hasSimilar = (data.length_profile || []).some(r => r.similar_avg);

  if (!profile || profile.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>Line & Length Analysis</Typography>
          <Typography variant="body2" color="text.secondary">
            No line/length data available for this player with current filters.
          </Typography>
          {data.data_coverage && (
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
              Total balls: {data.data_coverage.player_balls} |
              With length data: {data.data_coverage.player_balls_with_length} |
              With line data: {data.data_coverage.player_balls_with_line}
            </Typography>
          )}
        </CardContent>
      </Card>
    );
  }

  const headerStyle = {
    padding: isMobile ? '4px 6px' : '6px 12px',
    textAlign: 'center',
    fontWeight: 600,
    fontSize: isMobile ? '0.7rem' : '0.8rem',
    color: '#555',
    borderBottom: '2px solid #e0e0e0',
    whiteSpace: 'nowrap',
  };

  const cellStyle = {
    padding: isMobile ? '4px 6px' : '6px 12px',
    textAlign: 'center',
    fontSize: isMobile ? '0.75rem' : '0.85rem',
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1, flexWrap: 'wrap', gap: 1 }}>
          <Typography variant="h6">Line & Length Analysis</Typography>
          <Tabs
            value={selectedMetric}
            onChange={(_, v) => setSelectedMetric(v)}
            sx={{ minHeight: 32, '& .MuiTab-root': { minHeight: 32, py: 0.5, px: 1.5, fontSize: '0.75rem' } }}
          >
            {METRIC_OPTIONS.map((m) => (
              <Tab key={m.value} label={isMobile ? m.shortLabel : m.label} />
            ))}
          </Tabs>
        </Box>

        <Tabs
          value={activeView}
          onChange={(_, v) => setActiveView(v)}
          sx={{ mb: 1.5, minHeight: 32, '& .MuiTab-root': { minHeight: 32, py: 0.5 } }}
        >
          <Tab label="By Length" />
          <Tab label="By Line" />
        </Tabs>

        {data.bowler_info && isBowling && (
          <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
            Bowler type: {data.bowler_info.bowl_style} ({data.bowler_info.bowl_kind})
          </Typography>
        )}

        <Box sx={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', borderSpacing: 0 }}>
            <thead>
              <tr>
                <th style={{ ...headerStyle, textAlign: 'left' }}>
                  {activeView === 0 ? 'Length' : 'Line'}
                </th>
                <th style={headerStyle}>Balls</th>
                <th style={headerStyle}>{isMobile ? metric.shortLabel : metric.label}</th>
                <th style={headerStyle}>vs Global</th>
                {!isMobile && hasSimilar && (
                  <th style={headerStyle}>vs Similar</th>
                )}
                {!isMobile && isBowling && data.bowler_info && (
                  <>
                    <th style={headerStyle}>vs {data.bowler_info.bowl_kind}</th>
                    {data.bowler_info.bowl_style && (
                      <th style={headerStyle}>vs {data.bowler_info.bowl_style}</th>
                    )}
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {profile.map((row) => {
                const belowThreshold = row.player.balls < MIN_BALLS;
                const rowStyle = belowThreshold
                  ? { opacity: 0.4, backgroundColor: '#fafafa' }
                  : {};
                const playerVal = row.player[metric.value];
                return (
                  <tr key={row.bucket} style={{ ...rowStyle, borderBottom: '1px solid #eee' }}>
                    <td style={{ ...cellStyle, textAlign: 'left', fontWeight: 500 }}>
                      {row.label}
                    </td>
                    <td style={{ ...cellStyle, color: '#666' }}>{row.player.balls}</td>
                    <td style={{ ...cellStyle, fontWeight: 600 }}>{playerVal.toFixed(1)}</td>
                    <DeltaCell
                      playerVal={playerVal}
                      comparisonVal={row.global_avg?.[metric.value]}
                      metric={metric}
                      isMobile={isMobile}
                    />
                    {!isMobile && hasSimilar && (
                      <DeltaCell
                        playerVal={playerVal}
                        comparisonVal={row.similar_avg?.[metric.value]}
                        metric={metric}
                        isMobile={isMobile}
                      />
                    )}
                    {!isMobile && isBowling && data.bowler_info && (
                      <>
                        <DeltaCell
                          playerVal={playerVal}
                          comparisonVal={row.bowl_kind_avg?.[metric.value]}
                          metric={metric}
                          isMobile={isMobile}
                        />
                        {data.bowler_info.bowl_style && (
                          <DeltaCell
                            playerVal={playerVal}
                            comparisonVal={row.bowl_style_avg?.[metric.value]}
                            metric={metric}
                            isMobile={isMobile}
                          />
                        )}
                      </>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Box>

        {data.data_coverage && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1.5 }}>
            Coverage: {data.data_coverage.player_balls_with_length} of {data.data_coverage.player_balls} balls
            have length data, {data.data_coverage.player_balls_with_line} have line data
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default LineLengthProfile;
