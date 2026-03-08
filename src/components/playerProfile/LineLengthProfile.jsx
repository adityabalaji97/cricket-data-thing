import React, { useState, useEffect } from 'react';
import {
  Card, CardContent, Typography, Box, Tabs, Tab, Tooltip,
  CircularProgress, Alert, useMediaQuery, useTheme
} from '@mui/material';
import { LINE_ORDER, LENGTH_ORDER, LINE_SHORT_LABELS, LENGTH_SHORT_LABELS } from '../PitchMap/pitchMapConstants';
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

// Normalize DB line values to PitchMap LINE_ORDER values
const LINE_NORMALIZE = {
  'OUTSIDE_OFF': 'OUTSIDE_OFFSTUMP',
  'WIDE_OUTSIDE_OFF': 'WIDE_OUTSIDE_OFFSTUMP',
  'WIDE_OUTSIDE_OFFSTUMP': 'WIDE_OUTSIDE_OFFSTUMP',
  'OUTSIDE_OFFSTUMP': 'OUTSIDE_OFFSTUMP',
  'OFF_STUMP': 'OUTSIDE_OFFSTUMP',
  'ON_THE_STUMPS': 'ON_THE_STUMPS',
  'MIDDLE': 'ON_THE_STUMPS',
  'LEG_STUMP': 'DOWN_LEG',
  'DOWN_LEG': 'DOWN_LEG',
  'WIDE_DOWN_LEG': 'WIDE_DOWN_LEG',
};

const LENGTH_NORMALIZE = {
  'SHORT': 'SHORT',
  'SHORT_OF_A_GOOD_LENGTH': 'SHORT_OF_A_GOOD_LENGTH',
  'SHORT_OF_LENGTH': 'SHORT_OF_A_GOOD_LENGTH',
  'GOOD_LENGTH': 'GOOD_LENGTH',
  'FULL': 'FULL',
  'YORKER': 'YORKER',
  'FULL_TOSS': 'FULL_TOSS',
};

/**
 * Merge profile rows into normalized buckets, weight-averaging metrics.
 */
function normalizeProfile(profile, dimension) {
  const normalizeMap = dimension === 'line' ? LINE_NORMALIZE : LENGTH_NORMALIZE;
  const merged = {};

  profile.forEach(item => {
    const normalized = normalizeMap[item.bucket] || item.bucket;
    const balls = item.player.balls || 0;
    if (balls === 0) return;

    if (!merged[normalized]) {
      merged[normalized] = {
        balls: 0,
        weighted: { strike_rate: 0, control_pct: 0, boundary_pct: 0, dot_pct: 0 },
        global_avg: null,
        similar_avg: null,
        bowl_kind_avg: null,
        bowl_style_avg: null,
      };
    }

    const m = merged[normalized];
    m.balls += balls;
    ['strike_rate', 'control_pct', 'boundary_pct', 'dot_pct'].forEach(k => {
      m.weighted[k] += (item.player[k] || 0) * balls;
    });

    // Keep comparison data from the bucket with more balls
    if (!m.global_avg || balls > (m._maxBalls || 0)) {
      m.global_avg = item.global_avg;
      m.similar_avg = item.similar_avg;
      m.bowl_kind_avg = item.bowl_kind_avg;
      m.bowl_style_avg = item.bowl_style_avg;
      m._maxBalls = balls;
    }
  });

  // Finalize weighted averages
  Object.values(merged).forEach(m => {
    if (m.balls > 0) {
      ['strike_rate', 'control_pct', 'boundary_pct', 'dot_pct'].forEach(k => {
        m.weighted[k] = m.weighted[k] / m.balls;
      });
    }
  });

  return merged;
}

/**
 * Get delta color: green if player is better, red if worse.
 */
function getDeltaColor(delta, invertColor) {
  if (Math.abs(delta) < 0.5) return colors.neutral[400];
  const isPositive = invertColor ? delta < 0 : delta > 0;
  return isPositive ? colors.chart.green : colors.chart.red;
}

/**
 * Get cell background color based on delta magnitude and direction.
 */
function getCellBgColor(delta, invertColor, balls, minBalls) {
  if (balls < minBalls) return colors.neutral[100];
  if (delta == null || isNaN(delta)) return colors.neutral[100];

  const absDelta = Math.abs(delta);
  const isPositive = invertColor ? delta < 0 : delta > 0;

  // Normalize intensity: 0-30 range maps to 0-1
  const intensity = Math.min(absDelta / 30, 1);

  if (isPositive) {
    // Green spectrum
    const alpha = 0.08 + intensity * 0.25;
    return `rgba(34, 197, 94, ${alpha})`;
  } else {
    // Red spectrum
    const alpha = 0.08 + intensity * 0.25;
    return `rgba(239, 68, 68, ${alpha})`;
  }
}

/**
 * Pitch-map style SVG grid for line/length profile with delta coloring.
 */
const LineLengthPitchGrid = ({ data, dimension, metric, comparison, isMobile }) => {
  const order = dimension === 'line' ? LINE_ORDER : [...LENGTH_ORDER].reverse();
  const labelMap = dimension === 'line' ? LINE_SHORT_LABELS : LENGTH_SHORT_LABELS;

  const profile = dimension === 'line' ? data.line_profile : data.length_profile;
  const merged = normalizeProfile(profile || [], dimension);

  const isVertical = dimension === 'line'; // vertical strips for line, horizontal for length

  // SVG dimensions
  const svgWidth = isMobile ? 340 : 400;
  const labelWidth = isMobile ? 50 : 70;
  const padding = { top: 10, right: 10, bottom: 10, left: labelWidth + 5 };
  const pitchWidth = svgWidth - padding.left - padding.right;

  let pitchHeight, cellWidth, cellHeight;
  if (isVertical) {
    pitchHeight = isMobile ? 200 : 240;
    cellWidth = pitchWidth / order.length;
    cellHeight = pitchHeight;
  } else {
    pitchHeight = (isMobile ? 56 : 64) * order.length;
    cellWidth = pitchWidth;
    cellHeight = pitchHeight / order.length;
  }

  const svgHeight = pitchHeight + padding.top + padding.bottom + (isVertical ? 30 : 0);

  return (
    <svg
      width={svgWidth}
      height={svgHeight}
      style={{ overflow: 'visible', maxWidth: '100%', display: 'block' }}
    >
      {/* Pitch background */}
      <rect
        x={padding.left}
        y={padding.top}
        width={pitchWidth}
        height={pitchHeight}
        fill={colors.neutral[50]}
        stroke={colors.chart.green}
        strokeWidth={1.5}
        rx={4}
      />

      {order.map((bucket, index) => {
        const cellData = merged[bucket];
        const balls = cellData?.balls || 0;
        const playerVal = cellData?.weighted?.[metric.value];
        const compVal = cellData?.[comparison]?.[metric.value];
        const delta = (playerVal != null && compVal != null) ? playerVal - compVal : null;
        const belowThreshold = balls < MIN_BALLS;

        let x, y, w, h;
        if (isVertical) {
          x = padding.left + index * cellWidth;
          y = padding.top;
          w = cellWidth;
          h = cellHeight;
        } else {
          x = padding.left;
          y = padding.top + index * cellHeight;
          w = cellWidth;
          h = cellHeight;
        }

        const bgColor = getCellBgColor(delta, metric.invertColor, balls, MIN_BALLS);
        const deltaColor = delta != null ? getDeltaColor(delta, metric.invertColor) : colors.neutral[400];
        const sign = delta > 0 ? '+' : '';
        const opacity = belowThreshold ? 0.35 : 1;

        const tooltipLines = [];
        tooltipLines.push(`${labelMap[bucket] || bucket}`);
        tooltipLines.push(`Balls: ${balls}`);
        if (playerVal != null) tooltipLines.push(`${metric.label}: ${playerVal.toFixed(1)}`);
        if (compVal != null) tooltipLines.push(`Comparison: ${compVal.toFixed(1)}`);
        if (delta != null) tooltipLines.push(`Delta: ${sign}${delta.toFixed(1)}`);

        // Font sizes
        const valueFontSize = isMobile ? 11 : 13;
        const deltaFontSize = isMobile ? 10 : 12;
        const ballsFontSize = isMobile ? 8 : 9;
        const labelFontSize = isMobile ? 9 : 10;

        return (
          <Tooltip
            key={bucket}
            title={
              <Box sx={{ p: 0.5 }}>
                {tooltipLines.map((line, i) => (
                  <Typography key={i} variant="caption" display="block">{line}</Typography>
                ))}
              </Box>
            }
            arrow
          >
            <g style={{ cursor: 'pointer', opacity }}>
              {/* Cell background */}
              <rect
                x={x + 1}
                y={y + 1}
                width={w - 2}
                height={h - 2}
                fill={bgColor}
                stroke={colors.neutral[200]}
                strokeWidth={1}
                rx={3}
              />

              {isVertical ? (
                /* Vertical layout for line-only: stacked text */
                <>
                  {/* Metric value */}
                  {playerVal != null && !belowThreshold && (
                    <text
                      x={x + w / 2}
                      y={y + h * 0.35}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={valueFontSize}
                      fontWeight="600"
                      fill={colors.neutral[800]}
                    >
                      {playerVal.toFixed(1)}
                    </text>
                  )}
                  {/* Delta */}
                  {delta != null && !belowThreshold && (
                    <text
                      x={x + w / 2}
                      y={y + h * 0.52}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={deltaFontSize}
                      fontWeight="700"
                      fill={deltaColor}
                    >
                      {sign}{delta.toFixed(1)}
                    </text>
                  )}
                  {/* Balls count */}
                  <text
                    x={x + w / 2}
                    y={y + h * 0.68}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize={ballsFontSize}
                    fill={colors.neutral[400]}
                  >
                    {balls}b
                  </text>
                  {/* Label below */}
                  <text
                    x={x + w / 2}
                    y={y + h + 16}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize={labelFontSize}
                    fill={colors.neutral[600]}
                  >
                    {labelMap[bucket] || bucket}
                  </text>
                </>
              ) : (
                /* Horizontal layout for length-only: left label, center value, right delta */
                <>
                  {/* Label on left side (outside the pitch) */}
                  <text
                    x={padding.left - 8}
                    y={y + h / 2}
                    textAnchor="end"
                    dominantBaseline="middle"
                    fontSize={labelFontSize}
                    fill={colors.neutral[600]}
                  >
                    {labelMap[bucket] || bucket}
                  </text>
                  {/* Metric value */}
                  {playerVal != null && !belowThreshold && (
                    <text
                      x={x + w * 0.25}
                      y={y + h / 2}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={valueFontSize}
                      fontWeight="600"
                      fill={colors.neutral[800]}
                    >
                      {playerVal.toFixed(1)}
                    </text>
                  )}
                  {/* Delta */}
                  {delta != null && !belowThreshold && (
                    <text
                      x={x + w * 0.55}
                      y={y + h / 2}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={deltaFontSize}
                      fontWeight="700"
                      fill={deltaColor}
                    >
                      {sign}{delta.toFixed(1)}
                    </text>
                  )}
                  {/* Balls count */}
                  <text
                    x={x + w * 0.82}
                    y={y + h / 2}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize={ballsFontSize}
                    fill={colors.neutral[400]}
                  >
                    {balls}b
                  </text>
                </>
              )}
            </g>
          </Tooltip>
        );
      })}
    </svg>
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
  const [selectedComparison, setSelectedComparison] = useState(0);
  const [similarPlayers, setSimilarPlayers] = useState([]);

  // Fetch doppelgangers for similar-player comparison
  useEffect(() => {
    if (!playerName) {
      setSimilarPlayers([]);
      return;
    }

    // Clear stale similar players while new profile context is loading.
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
          const names = (json.most_similar || []).map(d => d.player_name).filter(Boolean);
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
  const hasSimilar = [...(data.length_profile || []), ...(data.line_profile || [])].some(r => r.similar_avg);

  // Build available comparison options
  const availableComparisons = COMPARISON_OPTIONS.filter(c => {
    if (c.value === 'similar_avg') return hasSimilar;
    if (c.value === 'bowl_kind_avg') return isBowling && data.bowler_info;
    if (c.value === 'bowl_style_avg') return isBowling && data.bowler_info?.bowl_style;
    return true; // global_avg always available
  });

  // Clamp selectedComparison to valid range
  const comparisonIndex = Math.min(selectedComparison, availableComparisons.length - 1);
  const comparison = availableComparisons[comparisonIndex]?.value || 'global_avg';

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

  return (
    <Card>
      <CardContent>
        {/* Header with metric selector */}
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

        {/* Length/Line toggle + Comparison toggle */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5, flexWrap: 'wrap', gap: 1 }}>
          <Tabs
            value={activeView}
            onChange={(_, v) => setActiveView(v)}
            sx={{ minHeight: 32, '& .MuiTab-root': { minHeight: 32, py: 0.5 } }}
          >
            <Tab label="By Length" />
            <Tab label="By Line" />
          </Tabs>

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

        {/* Pitch Map Grid */}
        <Box sx={{ display: 'flex', justifyContent: 'center', overflow: 'auto' }}>
          <LineLengthPitchGrid
            data={data}
            dimension={activeView === 0 ? 'length' : 'line'}
            metric={metric}
            comparison={comparison}
            isMobile={isMobile}
          />
        </Box>

        {/* Legend */}
        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 1.5, flexWrap: 'wrap' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box sx={{ width: 12, height: 12, borderRadius: 1, bgcolor: 'rgba(34, 197, 94, 0.25)' }} />
            <Typography variant="caption" color="text.secondary">Better than {availableComparisons[comparisonIndex]?.shortLabel || 'avg'}</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box sx={{ width: 12, height: 12, borderRadius: 1, bgcolor: 'rgba(239, 68, 68, 0.25)' }} />
            <Typography variant="caption" color="text.secondary">Worse than {availableComparisons[comparisonIndex]?.shortLabel || 'avg'}</Typography>
          </Box>
          <Typography variant="caption" color="text.secondary">
            (Faded = &lt;{MIN_BALLS} balls)
          </Typography>
        </Box>

        {data.data_coverage && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1, textAlign: 'center' }}>
            Coverage: {data.data_coverage.player_balls_with_length} of {data.data_coverage.player_balls} balls
            have length data, {data.data_coverage.player_balls_with_line} have line data
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default LineLengthProfile;
