import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  Box,
  Chip,
  CircularProgress,
  Stack,
  Typography,
} from '@mui/material';
import config from '../config';
import { AlertBanner, VisualizationCard } from './ui';
import { colors, spacing, typography } from '../theme/designSystem';
import { colors as hs, fonts } from '../theme/hindsightDark';
import { apiErrorText } from '../utils/apiError';

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


const fmtRaw = (v) => {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '–';
  const n = Number(v);
  return Math.abs(n) >= 100 ? n.toFixed(0) : n.toFixed(1);
};

/**
 * Player v doppelganger, one row per metric: two dots on a shared 0-100 percentile track, raw
 * values at the end, biggest gaps first.
 *
 * Replaced a 10-18 axis radar with 10px angle labels: two near-identical filled shapes that read
 * as "the same player" even where roles differ sharply (e.g. powerplay v death usage).
 */
const SimilarityDumbbells = ({ rows, targetName, compareName }) => {
  const sorted = [...rows].sort(
    (x, y) => Math.abs((y.targetPercentile ?? 0) - (y.comparePercentile ?? 0))
      - Math.abs((x.targetPercentile ?? 0) - (x.comparePercentile ?? 0)),
  );
  const dot = (left, color, z) => ({
    position: 'absolute', top: 1, left: `${left}%`, width: 12, height: 12, ml: '-6px',
    borderRadius: '50%', bgcolor: color, border: `2px solid ${hs.surface1}`, zIndex: z,
  });
  return (
    <Box>
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', fontSize: 12, color: hs.textLo, mb: 1 }}>
        <span><Box component="span" sx={{ ...dot(0, hs.accent, 1), position: 'relative', display: 'inline-block', top: 1, ml: 0, mr: 0.75 }} />{targetName}</span>
        <span><Box component="span" sx={{ ...dot(0, hs.textLo, 1), position: 'relative', display: 'inline-block', top: 1, ml: 0, mr: 0.75 }} />{compareName}</span>
        <span>Percentile among peers · biggest differences first</span>
      </Box>
      <Box sx={{ display: 'grid', gap: 0.75 }}>
        {sorted.map((r) => {
          const a = Math.max(0, Math.min(100, Number(r.targetPercentile) || 0));
          const b = Math.max(0, Math.min(100, Number(r.comparePercentile) || 0));
          return (
            <Box
              key={r.metric}
              aria-label={`${r.metric}: ${targetName} ${fmtRaw(r.targetRaw)}, ${compareName} ${fmtRaw(r.compareRaw)}`}
              sx={{ display: 'grid', gridTemplateColumns: '84px minmax(0, 1fr) 76px', gap: 1, alignItems: 'center', minHeight: 24 }}
            >
              <Typography sx={{ fontSize: 12.5, color: hs.textMed, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {r.metric}
              </Typography>
              <Box sx={{ position: 'relative', height: 14 }}>
                <Box sx={{ position: 'absolute', left: 0, right: 0, top: 6, height: 2, bgcolor: 'rgba(255,255,255,0.07)' }} />
                <Box sx={{ position: 'absolute', top: 5, height: 4, left: `${Math.min(a, b)}%`, width: `${Math.abs(a - b)}%`, bgcolor: 'rgba(255,255,255,0.28)' }} />
                <Box sx={dot(b, hs.textLo, 1)} />
                <Box sx={dot(a, hs.accent, 2)} />
              </Box>
              <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, textAlign: 'right', whiteSpace: 'nowrap' }}>
                <Box component="span" sx={{ color: hs.accent }}>{fmtRaw(r.targetRaw)}</Box>
                <Box component="span" sx={{ color: hs.textFaint }}> · </Box>
                <Box component="span" sx={{ color: hs.textLo }}>{fmtRaw(r.compareRaw)}</Box>
              </Typography>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
};

const PlayerDoppelgangers = ({
  playerName,
  playerType = null,
  startDate,
  endDate,
  leagues = [],
  includeInternational = false,
  topTeams = 10,
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
        leagues.forEach((league) => params.append('leagues', league));
        params.append('include_international', String(includeInternational));
        if (includeInternational && topTeams) {
          params.append('top_teams', String(topTeams));
        }
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
          setError(apiErrorText(err, null) || 'Failed to fetch doppelgänger results');
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
  }, [playerName, playerType, startDate, endDate, leagues, includeInternational, topTeams, fetchTrigger]);

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
                <SimilarityDumbbells
                  rows={radarData}
                  targetName={data.display_name || data.player_name}
                  compareName={selectedDoppelganger.player_name}
                />
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
