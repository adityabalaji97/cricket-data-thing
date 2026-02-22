import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  Box,
  Chip,
  CircularProgress,
  Stack,
  Typography,
} from '@mui/material';
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
import { AlertBanner, VisualizationCard } from './ui';
import { colors, spacing, typography } from '../theme/designSystem';

const ROLE_LABELS = {
  batter: 'Batter',
  bowler: 'Bowler',
  all_rounder: 'All-Rounder',
};

const roleFromPlayerType = (playerType) => {
  if (playerType === 'bowler') return 'bowler';
  if (playerType === 'batter') return 'batter';
  return null;
};

const RadarTooltip = ({ active, payload, label }) => {
  if (!active || !payload || payload.length === 0) return null;

  const datum = payload[0]?.payload;
  if (!datum) return null;

  return (
    <Box
      sx={{
        backgroundColor: colors.neutral[0],
        border: `1px solid ${colors.neutral[200]}`,
        borderRadius: 2,
        p: `${spacing.sm}px ${spacing.md}px`,
        boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
        maxWidth: 280,
      }}
    >
      <Typography variant="body2" sx={{ fontWeight: typography.fontWeight.semibold, mb: `${spacing.xs}px` }}>
        {label}
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block">
        Target: {datum.targetPercentile}% ({datum.targetRaw})
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block">
        Match: {datum.comparePercentile}% ({datum.compareRaw})
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block">
        League avg: {datum.leagueAvg}
      </Typography>
    </Box>
  );
};

const PlayerDoppelgangers = ({
  playerName,
  playerType = null,
  startDate,
  endDate,
  fetchTrigger,
  isMobile = false,
}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedSimilarIndex, setSelectedSimilarIndex] = useState(0);

  useEffect(() => {
    if (!playerName || !fetchTrigger) return;

    let cancelled = false;

    const fetchDoppelgangers = async () => {
      setLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        params.append('top_n', '5');
        params.append('min_matches', '10');

        const role = roleFromPlayerType(playerType);
        if (role) params.append('role', role);

        const response = await axios.get(
          `${config.API_URL}/search/player/${encodeURIComponent(playerName)}/doppelgangers?${params.toString()}`
        );

        if (!cancelled) {
          setData(response.data);
          setSelectedSimilarIndex(0);
        }
      } catch (err) {
        if (!cancelled) {
          setData(null);
          setError(err.response?.data?.detail || 'Failed to fetch doppelgänger results');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchDoppelgangers();

    return () => {
      cancelled = true;
    };
  }, [playerName, playerType, startDate, endDate, fetchTrigger]);

  const selectedDoppelganger = data?.most_similar?.[selectedSimilarIndex] || null;

  const radarData = useMemo(() => {
    if (!data?.target_radar_metrics || !selectedDoppelganger?.radar_metrics) return [];

    const compareByKey = new Map(
      selectedDoppelganger.radar_metrics.map((metric) => [metric.key, metric])
    );

    return data.target_radar_metrics
      .map((targetMetric) => {
        const compareMetric = compareByKey.get(targetMetric.key);
        if (!compareMetric) return null;
        return {
          metric: targetMetric.metric,
          targetPercentile: targetMetric.percentile,
          comparePercentile: compareMetric.percentile,
          targetRaw: targetMetric.raw_value,
          compareRaw: compareMetric.raw_value,
          leagueAvg: targetMetric.league_avg,
        };
      })
      .filter(Boolean);
  }, [data, selectedDoppelganger]);

  if (!playerName || !fetchTrigger) return null;

  return (
    <Box sx={{ mt: `${spacing.lg}px` }}>
      <VisualizationCard
        title="Doppelganger Search"
        subtitle="Role-aware similarity using phase and overall performance metrics"
        isMobile={isMobile}
      >
        {loading && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: `${spacing.md}px`, py: `${spacing.base}px` }}>
            <CircularProgress size={18} />
            <Typography variant="body2" color="text.secondary">
              Finding comparable profiles...
            </Typography>
          </Box>
        )}

        {error && !loading && (
          <AlertBanner severity="error">
            <Typography variant="body2">{error}</Typography>
          </AlertBanner>
        )}

        {data?.found && !loading && (
          <Stack spacing={2}>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                Detected role:
              </Typography>
              <Chip
                size="small"
                label={ROLE_LABELS[data.comparison_role] || data.comparison_role}
                sx={{
                  backgroundColor: colors.primary[50],
                  color: colors.primary[700],
                  border: `1px solid ${colors.primary[200]}`,
                }}
              />
              {data.role_overridden && (
                <Typography variant="caption" color="text.secondary">
                  (manual override)
                </Typography>
              )}
            </Box>

            <Box>
              <Typography variant="body2" sx={{ mb: 1, fontWeight: typography.fontWeight.medium }}>
                Most Similar ({data.most_similar?.length || 0})
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {(data.most_similar || []).map((player, index) => (
                  <Chip
                    key={`${player.player_name}-${index}`}
                    clickable
                    color={selectedSimilarIndex === index ? 'primary' : 'default'}
                    variant={selectedSimilarIndex === index ? 'filled' : 'outlined'}
                    onClick={() => setSelectedSimilarIndex(index)}
                    label={`${player.player_name} · ${player.distance}`}
                  />
                ))}
              </Box>
            </Box>

            {selectedDoppelganger && radarData.length > 0 && (
              <Box>
                <Typography variant="body2" sx={{ mb: 1, fontWeight: typography.fontWeight.medium }}>
                  {data.display_name || data.player_name} vs {selectedDoppelganger.player_name}
                </Typography>
                <Box sx={{ width: '100%', height: isMobile ? 360 : 440 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart
                      data={radarData}
                      outerRadius={isMobile ? '68%' : 165}
                      margin={{ top: 8, right: 12, bottom: 8, left: 12 }}
                    >
                      <PolarGrid />
                      <PolarAngleAxis
                        dataKey="metric"
                        tick={{ fontSize: isMobile ? 10 : 12, fill: colors.neutral[800] }}
                      />
                      <PolarRadiusAxis
                        domain={[0, 100]}
                        tickCount={6}
                        tick={{ fontSize: isMobile ? 9 : 11, fill: colors.neutral[600] }}
                      />
                      <Radar
                        name={data.display_name || data.player_name}
                        dataKey="targetPercentile"
                        stroke={colors.chart.blue}
                        fill={colors.chart.blue}
                        fillOpacity={0.2}
                      />
                      <Radar
                        name={selectedDoppelganger.player_name}
                        dataKey="comparePercentile"
                        stroke={colors.chart.orange}
                        fill={colors.chart.orange}
                        fillOpacity={0.2}
                      />
                      <Tooltip content={<RadarTooltip />} />
                      <Legend
                        wrapperStyle={{
                          fontSize: isMobile ? '0.75rem' : '0.875rem',
                          color: colors.neutral[800],
                        }}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </Box>
              </Box>
            )}

            <Box>
              <Typography variant="body2" sx={{ mb: 1, fontWeight: typography.fontWeight.medium }}>
                Most Different
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {(data.most_dissimilar || []).slice(0, 3).map((player, index) => (
                  <Chip
                    key={`dissimilar-${player.player_name}-${index}`}
                    variant="outlined"
                    label={`${player.player_name} · ${player.distance}`}
                    sx={{
                      borderColor: colors.error[200] || colors.error[500],
                      color: colors.error[700],
                    }}
                  />
                ))}
              </Box>
            </Box>
          </Stack>
        )}
      </VisualizationCard>
    </Box>
  );
};

export default PlayerDoppelgangers;
