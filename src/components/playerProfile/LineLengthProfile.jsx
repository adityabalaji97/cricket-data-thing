import React, { useState, useEffect } from 'react';
import {
  Card, CardContent, Typography, Box, Tabs, Tab, Tooltip,
  CircularProgress, Alert, useMediaQuery, useTheme
} from '@mui/material';
import {
  LINE_ORDER,
  LENGTH_ORDER,
  LINE_LABELS,
  LENGTH_LABELS,
  LINE_SHORT_LABELS,
  LENGTH_SHORT_LABELS,
} from '../PitchMap/pitchMapConstants';
import { colors } from '../../theme/designSystem';
import config from '../../config';

const MIN_BALLS = 20;

const METRIC_OPTIONS = [
  { value: 'strike_rate', label: 'Strike Rate', shortLabel: 'SR', invertColor: false },
  { value: 'control_pct', label: 'Control %', shortLabel: 'Ctrl%', invertColor: false },
  { value: 'boundary_pct', label: 'Boundary %', shortLabel: 'Bnd%', invertColor: false },
  { value: 'dot_pct', label: 'Dot %', shortLabel: 'Dot%', invertColor: true },
];

const COMPARISON_OPTIONS = [
  { value: 'global_avg', label: 'vs Global', shortLabel: 'Global' },
  { value: 'similar_avg', label: 'vs Similar', shortLabel: 'Similar' },
  { value: 'bowl_kind_avg', label: 'vs Bowl Kind', shortLabel: 'Kind' },
  { value: 'bowl_style_avg', label: 'vs Bowl Style', shortLabel: 'Style' },
];

function getDeltaColor(delta, invertColor) {
  if (Math.abs(delta) < 0.5) return colors.neutral[400];
  const isPositive = invertColor ? delta < 0 : delta > 0;
  return isPositive ? colors.chart.green : colors.chart.red;
}

function getCellBgColor(delta, invertColor, balls, minBalls) {
  if (balls < minBalls) return colors.neutral[100];
  if (delta == null || isNaN(delta)) return colors.neutral[100];

  const absDelta = Math.abs(delta);
  const isPositive = invertColor ? delta < 0 : delta > 0;
  const intensity = Math.min(absDelta / 30, 1);
  const alpha = 0.08 + intensity * 0.25;

  if (isPositive) {
    return `rgba(34, 197, 94, ${alpha})`;
  }
  return `rgba(239, 68, 68, ${alpha})`;
}

function normalizeBatHand(value) {
  if (!value) return null;
  const token = String(value).trim().toUpperCase().replace(/[\s-]+/g, '_');
  if (token === 'LHB' || token === 'LEFT' || token === 'LEFT_HANDED' || token === 'LEFT_HANDED_BAT') return 'LHB';
  if (token === 'RHB' || token === 'RIGHT' || token === 'RIGHT_HANDED' || token === 'RIGHT_HANDED_BAT') return 'RHB';
  return null;
}

const CombinedLineLengthGrid = ({ data, metric, comparison, isMobile, mirrorLineForLhb = false }) => {
  const grid = data?.line_length_grid || {};
  const cells = grid?.cells || {};
  const baseLineOrder = Array.isArray(grid?.line_order) && grid.line_order.length ? grid.line_order : LINE_ORDER;
  const baseLengthOrder = Array.isArray(grid?.length_order) && grid.length_order.length ? grid.length_order : LENGTH_ORDER;
  const lineOrder = mirrorLineForLhb ? [...baseLineOrder].reverse() : baseLineOrder;
  const lengthOrder = [...baseLengthOrder].reverse();

  const rowHeaderWidth = isMobile ? 74 : 112;
  const minCellWidth = isMobile ? 68 : 88;
  const minTableWidth = rowHeaderWidth + (lineOrder.length * minCellWidth);

  return (
    <Box sx={{ width: '100%', overflowX: 'auto' }}>
      <Box
        sx={{
          minWidth: minTableWidth,
          border: `1px solid ${colors.neutral[200]}`,
          borderRadius: 1,
          overflow: 'hidden',
        }}
      >
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: `${rowHeaderWidth}px repeat(${lineOrder.length}, minmax(${minCellWidth}px, 1fr))`,
          }}
        >
          <Box
            sx={{
              borderRight: `1px solid ${colors.neutral[200]}`,
              borderBottom: `1px solid ${colors.neutral[200]}`,
              bgcolor: colors.neutral[50],
            }}
          />

          {lineOrder.map((lineBucket) => (
            <Box
              key={`head-${lineBucket}`}
              sx={{
                p: 0.8,
                textAlign: 'center',
                borderRight: `1px solid ${colors.neutral[200]}`,
                borderBottom: `1px solid ${colors.neutral[200]}`,
                bgcolor: colors.neutral[50],
              }}
            >
              <Typography variant="caption" sx={{ fontWeight: 700 }}>
                {isMobile
                  ? (LINE_SHORT_LABELS[lineBucket] || lineBucket)
                  : (LINE_LABELS[lineBucket] || LINE_SHORT_LABELS[lineBucket] || lineBucket)}
              </Typography>
            </Box>
          ))}

          {lengthOrder.map((lengthBucket) => (
            <React.Fragment key={`row-${lengthBucket}`}>
              <Box
                sx={{
                  minHeight: isMobile ? 58 : 72,
                  px: 0.9,
                  display: 'flex',
                  alignItems: 'center',
                  borderRight: `1px solid ${colors.neutral[200]}`,
                  borderBottom: `1px solid ${colors.neutral[200]}`,
                  bgcolor: colors.neutral[50],
                }}
              >
                <Typography variant="caption" sx={{ fontWeight: 700 }}>
                  {isMobile
                    ? (LENGTH_SHORT_LABELS[lengthBucket] || lengthBucket)
                    : (LENGTH_LABELS[lengthBucket] || LENGTH_SHORT_LABELS[lengthBucket] || lengthBucket)}
                </Typography>
              </Box>

              {lineOrder.map((lineBucket) => {
                const cellKey = `${lengthBucket}_${lineBucket}`;
                const cell = cells[cellKey] || null;
                const playerVal = cell?.player?.[metric.value];
                const baselineVal = cell?.[comparison]?.[metric.value];
                const delta = cell?.deltas?.[comparison]?.[metric.value];
                const balls = Number(cell?.player?.balls || 0);
                const belowThreshold = balls < MIN_BALLS;
                const sign = delta > 0 ? '+' : '';
                const bgColor = getCellBgColor(delta, metric.invertColor, balls, MIN_BALLS);
                const deltaColor = delta != null ? getDeltaColor(delta, metric.invertColor) : colors.neutral[400];

                const tooltipLines = [
                  `${LENGTH_LABELS[lengthBucket] || lengthBucket} • ${LINE_LABELS[lineBucket] || lineBucket}`,
                  `Balls: ${balls}`,
                ];
                if (playerVal != null) tooltipLines.push(`${metric.label}: ${playerVal.toFixed(1)}`);
                if (baselineVal != null) tooltipLines.push(`Comparison: ${baselineVal.toFixed(1)}`);
                if (delta != null) tooltipLines.push(`Delta: ${sign}${delta.toFixed(1)}`);

                return (
                  <Tooltip
                    key={`cell-${cellKey}`}
                    title={
                      <Box sx={{ p: 0.5 }}>
                        {tooltipLines.map((line, i) => (
                          <Typography key={i} variant="caption" display="block">{line}</Typography>
                        ))}
                      </Box>
                    }
                    arrow
                  >
                    <Box
                      sx={{
                        minHeight: isMobile ? 58 : 72,
                        p: 0.7,
                        borderRight: `1px solid ${colors.neutral[200]}`,
                        borderBottom: `1px solid ${colors.neutral[200]}`,
                        bgcolor: bgColor,
                        opacity: belowThreshold ? 0.45 : 1,
                        cursor: 'default',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 0.15,
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{
                          fontWeight: 700,
                          color: colors.neutral[800],
                          lineHeight: 1.1,
                          fontSize: isMobile ? '0.72rem' : '0.78rem',
                        }}
                      >
                        {playerVal != null ? playerVal.toFixed(1) : '--'}
                      </Typography>

                      <Typography
                        variant="caption"
                        sx={{
                          fontWeight: 700,
                          color: deltaColor,
                          lineHeight: 1.1,
                          fontSize: isMobile ? '0.68rem' : '0.74rem',
                        }}
                      >
                        {delta != null ? `${sign}${delta.toFixed(1)}` : '--'}
                      </Typography>

                      <Typography
                        variant="caption"
                        sx={{
                          color: colors.neutral[500],
                          lineHeight: 1.1,
                          fontSize: isMobile ? '0.62rem' : '0.68rem',
                        }}
                      >
                        {balls}b
                      </Typography>
                    </Box>
                  </Tooltip>
                );
              })}
            </React.Fragment>
          ))}
        </Box>
      </Box>
    </Box>
  );
};

const LegacyLineLengthTable = ({
  data,
  metric,
  comparison,
  isMobile,
  activeView,
  onActiveViewChange,
}) => {
  const profile = activeView === 0 ? (data.length_profile || []) : (data.line_profile || []);
  const bucketLabel = activeView === 0 ? 'Length' : 'Line';

  return (
    <Box sx={{ width: '100%' }}>
      <Tabs
        value={activeView}
        onChange={(_, v) => onActiveViewChange(v)}
        sx={{ mb: 1, minHeight: 32, '& .MuiTab-root': { minHeight: 32, py: 0.5 } }}
      >
        <Tab label="By Length" />
        <Tab label="By Line" />
      </Tabs>

      <Box sx={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', borderSpacing: 0 }}>
          <thead>
            <tr>
              <th style={{ padding: 8, textAlign: 'left', borderBottom: `1px solid ${colors.neutral[200]}` }}>{bucketLabel}</th>
              <th style={{ padding: 8, textAlign: 'center', borderBottom: `1px solid ${colors.neutral[200]}` }}>Balls</th>
              <th style={{ padding: 8, textAlign: 'center', borderBottom: `1px solid ${colors.neutral[200]}` }}>{isMobile ? metric.shortLabel : metric.label}</th>
              <th style={{ padding: 8, textAlign: 'center', borderBottom: `1px solid ${colors.neutral[200]}` }}>Delta</th>
            </tr>
          </thead>
          <tbody>
            {profile.map((row) => {
              const balls = Number(row?.player?.balls || 0);
              const belowThreshold = balls < MIN_BALLS;
              const playerVal = row?.player?.[metric.value];
              const baselineVal = row?.[comparison]?.[metric.value];
              const delta = (playerVal != null && baselineVal != null) ? playerVal - baselineVal : null;
              const sign = delta > 0 ? '+' : '';
              const deltaColor = delta != null ? getDeltaColor(delta, metric.invertColor) : colors.neutral[400];

              return (
                <tr key={row.bucket} style={{ opacity: belowThreshold ? 0.45 : 1 }}>
                  <td style={{ padding: 8, borderBottom: `1px solid ${colors.neutral[100]}`, fontWeight: 600 }}>{row.label || row.bucket}</td>
                  <td style={{ padding: 8, textAlign: 'center', borderBottom: `1px solid ${colors.neutral[100]}` }}>{balls}</td>
                  <td style={{ padding: 8, textAlign: 'center', borderBottom: `1px solid ${colors.neutral[100]}` }}>
                    {playerVal != null ? playerVal.toFixed(1) : '--'}
                  </td>
                  <td style={{ padding: 8, textAlign: 'center', borderBottom: `1px solid ${colors.neutral[100]}`, color: deltaColor, fontWeight: 700 }}>
                    {delta != null ? `${sign}${delta.toFixed(1)}` : '--'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Box>
    </Box>
  );
};

const LineLengthProfile = ({ playerName, mode, dateRange, selectedVenue, competitionFilters, isMobile: isMobileProp }) => {
  const theme = useTheme();
  const isMobileQuery = useMediaQuery(theme.breakpoints.down('sm'));
  const isMobile = isMobileProp !== undefined ? isMobileProp : isMobileQuery;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedMetric, setSelectedMetric] = useState(0);
  const [selectedComparison, setSelectedComparison] = useState(0);
  const [legacyActiveView, setLegacyActiveView] = useState(0);
  const [similarPlayers, setSimilarPlayers] = useState([]);

  useEffect(() => {
    if (!playerName) {
      setSimilarPlayers([]);
      return;
    }

    setSimilarPlayers([]);

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
          const names = (json.most_similar || []).map((d) => d.player_name).filter(Boolean);
          setSimilarPlayers(names);
        } else {
          setSimilarPlayers([]);
        }
      } catch (e) {
        setSimilarPlayers([]);
        console.warn('Failed to fetch doppelgangers:', e);
      }
    };

    fetchDoppelgangers();
  }, [playerName, dateRange]);

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
          competitionFilters.leagues.forEach((l) => params.append('leagues', l));
        }
        if (competitionFilters?.international) {
          params.append('include_international', 'true');
        }
        if (competitionFilters?.topTeams) {
          params.append('top_teams', competitionFilters.topTeams);
        }
        similarPlayers.forEach((name) => params.append('similar_players', name));

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

  const metric = METRIC_OPTIONS[selectedMetric];
  const isBowling = mode === 'bowling';
  const hasGridPayload = !!data?.line_length_grid?.cells;
  const gridCells = Object.values(data?.line_length_grid?.cells || {});
  const hasGridData = gridCells.some((cell) => Number(cell?.player?.balls || 0) > 0);
  const hasLegacyData = (data.length_profile || []).length > 0 || (data.line_profile || []).length > 0;

  const hasSimilar = gridCells.some((cell) => !!cell?.similar_avg)
    || [...(data.length_profile || []), ...(data.line_profile || [])].some((r) => r.similar_avg);
  const hasBowlKind = isBowling && !!data.bowler_info && gridCells.some((cell) => !!cell?.bowl_kind_avg);
  const hasBowlStyle = isBowling && !!data.bowler_info?.bowl_style && gridCells.some((cell) => !!cell?.bowl_style_avg);

  const availableComparisons = COMPARISON_OPTIONS.filter((c) => {
    if (c.value === 'similar_avg') return hasSimilar;
    if (c.value === 'bowl_kind_avg') return hasBowlKind;
    if (c.value === 'bowl_style_avg') return hasBowlStyle;
    return true;
  });

  const comparisonIndex = Math.min(selectedComparison, availableComparisons.length - 1);
  const comparison = availableComparisons[comparisonIndex]?.value || 'global_avg';
  const playerBatHand = normalizeBatHand(data?.player_bat_hand);
  const mirrorLineForLhb = mode === 'batting' && playerBatHand === 'LHB';

  if (!hasGridData && !hasLegacyData) {
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

        <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', mb: 1.5, flexWrap: 'wrap', gap: 1 }}>
          {availableComparisons.length > 1 && (
            <Tabs
              value={comparisonIndex}
              onChange={(_, v) => setSelectedComparison(v)}
              sx={{ minHeight: 28, '& .MuiTab-root': { minHeight: 28, py: 0.25, px: 1, fontSize: '0.7rem' } }}
            >
              {availableComparisons.map((c) => (
                <Tab key={c.value} label={isMobile ? c.shortLabel : c.label} />
              ))}
            </Tabs>
          )}
        </Box>

        {data.bowler_info && isBowling && (
          <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
            Bowler type: {data.bowler_info.bowl_style} ({data.bowler_info.bowl_kind})
          </Typography>
        )}

        <Box sx={{ display: 'flex', justifyContent: 'center' }}>
          {hasGridData ? (
            <CombinedLineLengthGrid
              data={data}
              metric={metric}
              comparison={comparison}
              isMobile={isMobile}
              mirrorLineForLhb={mirrorLineForLhb}
            />
          ) : (
            <Box sx={{ width: '100%' }}>
              {!hasGridPayload && (
                <Alert severity="info" sx={{ mb: 1 }}>
                  Combined line×length grid not available in API response yet. Showing legacy view.
                </Alert>
              )}
              <LegacyLineLengthTable
                data={data}
                metric={metric}
                comparison={comparison}
                isMobile={isMobile}
                activeView={legacyActiveView}
                onActiveViewChange={setLegacyActiveView}
              />
            </Box>
          )}
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 1.5, flexWrap: 'wrap' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box sx={{ width: 12, height: 12, borderRadius: 1, bgcolor: 'rgba(34, 197, 94, 0.25)' }} />
            <Typography variant="caption" color="text.secondary">
              Better than {availableComparisons[comparisonIndex]?.shortLabel || 'avg'}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box sx={{ width: 12, height: 12, borderRadius: 1, bgcolor: 'rgba(239, 68, 68, 0.25)' }} />
            <Typography variant="caption" color="text.secondary">
              Worse than {availableComparisons[comparisonIndex]?.shortLabel || 'avg'}
            </Typography>
          </Box>
          <Typography variant="caption" color="text.secondary">
            (Faded = &lt;{MIN_BALLS} balls)
          </Typography>
        </Box>

        {data.data_coverage && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1, textAlign: 'center' }}>
            Coverage: {data.data_coverage.player_balls_with_length} of {data.data_coverage.player_balls} balls
            {' '}have length data, {data.data_coverage.player_balls_with_line} have line data
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default LineLengthProfile;
