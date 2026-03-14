import React, { useEffect, useMemo, useState } from 'react';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  LinearProgress,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

import config from '../config';

const TEAM_COLORS = ['#1976d2', '#ef6c00', '#2e7d32'];
const DEFAULT_CATEGORY_WEIGHTS = {
  win_rate: 0.12,
  elo: 0.1,
  batting: 0.18,
  bowling: 0.18,
  pace_spin: 0.12,
  venue_adaptability: 0.1,
  situational: 0.1,
  squad_depth: 0.1,
};
const DEFAULT_EXPLAINER_STEPS = [
  'Resolve squad names to canonical players from the roster file.',
  'Aggregate player-level match data into team metrics by category.',
  'Convert each metric to percentile scores across all IPL teams.',
  'Average category metrics, apply weights, and rank teams by composite score.',
];
const DEFAULT_DATA_SOURCES = [
  'matches',
  'batting_stats',
  'bowling_stats',
  'deliveries',
  'delivery_details',
  'player_aliases',
  'players',
  'ipl_rosters',
];

const formatLabel = (value) =>
  value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());

const formatMetricValue = (value) => {
  if (value === null || value === undefined) {
    return 'N/A';
  }
  if (typeof value !== 'number') {
    return String(value);
  }
  if (Math.abs(value) <= 1) {
    return value.toFixed(3);
  }
  if (Math.abs(value) >= 100) {
    return value.toFixed(1);
  }
  return value.toFixed(2);
};

const RadarTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) {
    return null;
  }
  return (
    <Box sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', p: 1.25, borderRadius: 1 }}>
      <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
        {label}
      </Typography>
      {payload.map((entry) => (
        <Typography key={entry.name} variant="caption" sx={{ display: 'block', color: entry.color }}>
          {entry.name}: {Number(entry.value || 0).toFixed(1)}
        </Typography>
      ))}
    </Box>
  );
};

const IPLPredictions = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [payload, setPayload] = useState(null);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`${config.API_URL}/teams/ipl-predictions`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        setPayload(data);
      } catch (fetchError) {
        console.error('Failed to fetch IPL predictions:', fetchError);
        setError('Failed to load IPL predictions.');
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const predictions = useMemo(() => payload?.predictions ?? [], [payload]);
  const modelExplainer = useMemo(() => payload?.model_explainer ?? {}, [payload]);
  const categoryWeights = useMemo(
    () => modelExplainer.category_weights || DEFAULT_CATEGORY_WEIGHTS,
    [modelExplainer],
  );
  const categoryMetricKeys = useMemo(
    () => modelExplainer.category_metric_keys || {},
    [modelExplainer],
  );
  const explainerSteps = useMemo(
    () => modelExplainer.steps || DEFAULT_EXPLAINER_STEPS,
    [modelExplainer],
  );
  const dataSources = useMemo(
    () => modelExplainer.data_sources || DEFAULT_DATA_SOURCES,
    [modelExplainer],
  );
  const categoryKeys = useMemo(
    () => (predictions[0]?.category_scores ? Object.keys(predictions[0].category_scores) : []),
    [predictions],
  );
  const weightedCategories = useMemo(
    () =>
      Object.entries(categoryWeights).sort((left, right) => {
        return right[1] - left[1];
      }),
    [categoryWeights],
  );
  const topThree = predictions.slice(0, 3);

  const radarData = useMemo(
    () =>
      categoryKeys.map((categoryKey) => {
        const point = { category: formatLabel(categoryKey) };
        topThree.forEach((team) => {
          point[team.team] = Number(team.category_scores?.[categoryKey]?.score || 0);
        });
        return point;
      }),
    [categoryKeys, topThree],
  );

  return (
    <Box sx={{ py: 3 }}>
      <Typography variant="h4" gutterBottom>
        IPL Championship Predictions
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Composite score is percentile-based across 8 categories and weighted into a 0-100 ranking.
      </Typography>

      {payload?.date_range ? (
        <Box sx={{ mb: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Chip
            size="small"
            variant="outlined"
            label={`Date range: ${payload.date_range.start} to ${payload.date_range.end}`}
          />
          <Chip size="small" variant="outlined" label={`Teams: ${payload.total_teams || 0}`} />
          {modelExplainer.version ? <Chip size="small" variant="outlined" label={`Model: ${modelExplainer.version}`} /> : null}
          {payload.generated_at ? <Chip size="small" variant="outlined" label={`Generated: ${payload.generated_at.slice(0, 19)}Z`} /> : null}
        </Box>
      ) : null}

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 1 }}>
            How This Prediction Is Calculated
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            {modelExplainer.description ||
              'Composite model using recency-weighted player/team inputs, percentile normalization, and weighted category blending.'}
          </Typography>

          <Box sx={{ display: 'grid', gap: 0.5, mb: 1.5 }}>
            {explainerSteps.map((step, index) => (
              <Typography key={`step-${index}`} variant="body2" color="text.secondary">
                {index + 1}. {step}
              </Typography>
            ))}
          </Box>

          <Typography variant="subtitle2" sx={{ mb: 0.75 }}>
            Category Weights
          </Typography>
          <Box sx={{ display: 'grid', gap: 1, gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, mb: 1.5 }}>
            {weightedCategories.map(([categoryKey, weight]) => (
              <Box key={`weight-${categoryKey}`}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption">{formatLabel(categoryKey)}</Typography>
                  <Typography variant="caption" sx={{ fontWeight: 700 }}>
                    {(Number(weight) * 100).toFixed(0)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={Math.max(0, Math.min(100, Number(weight) * 100))}
                  sx={{ height: 7, borderRadius: 8, mt: 0.4 }}
                />
              </Box>
            ))}
          </Box>

          <Typography variant="subtitle2" sx={{ mb: 0.75 }}>
            Data Sources Used
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
            {dataSources.map((source) => (
              <Chip key={source} size="small" variant="outlined" label={source} />
            ))}
          </Box>
        </CardContent>
      </Card>

      {loading ? (
        <Box sx={{ py: 6, display: 'flex', justifyContent: 'center' }}>
          <CircularProgress />
        </Box>
      ) : null}

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}

      {!loading && !error && topThree.length ? (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 1.5 }}>
              Top 3 Radar (Category Scores)
            </Typography>
            <Box sx={{ width: '100%', height: 380 }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} outerRadius="72%">
                  <PolarGrid />
                  <PolarAngleAxis dataKey="category" tick={{ fontSize: 11 }} />
                  <PolarRadiusAxis domain={[0, 100]} tickCount={6} />
                  {topThree.map((team, index) => (
                    <Radar
                      key={team.team}
                      name={`${team.rank}. ${team.team}`}
                      dataKey={team.team}
                      stroke={TEAM_COLORS[index % TEAM_COLORS.length]}
                      fill={TEAM_COLORS[index % TEAM_COLORS.length]}
                      fillOpacity={0.18}
                      strokeWidth={2}
                    />
                  ))}
                  <Legend />
                  <Tooltip content={<RadarTooltip />} />
                </RadarChart>
              </ResponsiveContainer>
            </Box>
          </CardContent>
        </Card>
      ) : null}

      {!loading && !error ? (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 1.5 }}>
              Leaderboard
            </Typography>
            {predictions.map((team) => (
              <Accordion
                key={team.team}
                expanded={expanded === team.team}
                onChange={(_, isExpanded) => setExpanded(isExpanded ? team.team : null)}
                disableGutters
              >
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box sx={{ width: '100%' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                        #{team.rank} {team.team} ({team.team_full_name})
                      </Typography>
                      <Chip
                        size="small"
                        color="primary"
                        label={`Composite ${Number(team.composite_score || 0).toFixed(1)}`}
                      />
                    </Box>
                    <Box sx={{ mt: 1, display: 'grid', gap: 1, gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, 1fr)' } }}>
                      {categoryKeys.map((categoryKey) => {
                        const score = Number(team.category_scores?.[categoryKey]?.score || 0);
                        return (
                          <Box key={`${team.team}-${categoryKey}`} sx={{ minWidth: 0 }}>
                            <Typography variant="caption" color="text.secondary">
                              {formatLabel(categoryKey)}
                            </Typography>
                            <LinearProgress
                              variant="determinate"
                              value={Math.max(0, Math.min(100, score))}
                              sx={{ height: 7, borderRadius: 8, mt: 0.3 }}
                            />
                          </Box>
                        );
                      })}
                    </Box>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{ display: 'grid', gap: 1.25, gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' } }}>
                    {categoryKeys.map((categoryKey) => {
                      const category = team.category_scores?.[categoryKey] || {};
                      const raw = category.raw || {};
                      const scoringKeySet = new Set(categoryMetricKeys[categoryKey] || []);
                      const scoringEntries = Object.entries(raw).filter(([metricKey]) => scoringKeySet.has(metricKey));
                      const supportEntries = Object.entries(raw).filter(([metricKey]) => !scoringKeySet.has(metricKey));
                      return (
                        <Card key={`${team.team}-${categoryKey}-detail`} variant="outlined">
                          <CardContent sx={{ py: 1.25 }}>
                            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>
                              {formatLabel(categoryKey)}: {Number(category.score || 0).toFixed(1)}
                            </Typography>
                            {scoringEntries.length ? (
                              <Box sx={{ mb: supportEntries.length ? 1 : 0 }}>
                                <Typography variant="caption" sx={{ fontWeight: 700, display: 'block', mb: 0.35 }}>
                                  Scoring Metrics
                                </Typography>
                                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr', gap: 0.35 }}>
                                  {scoringEntries.map(([metricKey, metricValue]) => (
                                    <Typography key={`${team.team}-${categoryKey}-${metricKey}`} variant="caption" color="text.secondary">
                                      {formatLabel(metricKey)}: {formatMetricValue(metricValue)}
                                    </Typography>
                                  ))}
                                </Box>
                              </Box>
                            ) : null}
                            {supportEntries.length ? (
                              <Box>
                                <Typography variant="caption" sx={{ fontWeight: 700, display: 'block', mb: 0.35 }}>
                                  Data Used (Coverage / Volumes)
                                </Typography>
                                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr', gap: 0.35 }}>
                                  {supportEntries.map(([metricKey, metricValue]) => (
                                    <Typography key={`${team.team}-${categoryKey}-${metricKey}`} variant="caption" color="text.secondary">
                                      {formatLabel(metricKey)}: {formatMetricValue(metricValue)}
                                    </Typography>
                                  ))}
                                </Box>
                              </Box>
                            ) : null}
                          </CardContent>
                        </Card>
                      );
                    })}
                  </Box>
                </AccordionDetails>
              </Accordion>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </Box>
  );
};

export default IPLPredictions;
