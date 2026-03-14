import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Collapse,
  LinearProgress,
  Slider,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import TuneIcon from '@mui/icons-material/Tune';
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
import VenueSectionTabs from './VenueSectionTabs';

const TEAM_COLORS = ['#1976d2', '#ef6c00', '#2e7d32'];

const CATEGORY_KEYS = [
  'win_rate', 'elo', 'batting', 'bowling',
  'pace_spin', 'venue_adaptability', 'situational', 'squad_depth',
];

const WEIGHT_PRESETS = {
  Balanced: { win_rate: 0.12, elo: 0.10, batting: 0.18, bowling: 0.18, pace_spin: 0.12, venue_adaptability: 0.10, situational: 0.10, squad_depth: 0.10 },
  'Batting-heavy': { win_rate: 0.10, elo: 0.08, batting: 0.28, bowling: 0.10, pace_spin: 0.10, venue_adaptability: 0.10, situational: 0.12, squad_depth: 0.12 },
  'Bowling-heavy': { win_rate: 0.10, elo: 0.08, batting: 0.10, bowling: 0.28, pace_spin: 0.12, venue_adaptability: 0.10, situational: 0.10, squad_depth: 0.12 },
  'Recent Form': { win_rate: 0.22, elo: 0.20, batting: 0.14, bowling: 0.14, pace_spin: 0.08, venue_adaptability: 0.08, situational: 0.08, squad_depth: 0.06 },
};

const DATE_PRESETS = [
  { label: '1Y', years: 1 },
  { label: '2Y', years: 2 },
  { label: '3Y', years: 3 },
  { label: 'IPL 2025', start: '2025-03-01', end: '2025-06-01' },
  { label: 'IPL 2024', start: '2024-03-01', end: '2024-06-01' },
  { label: 'Custom' },
];

const SECTIONS = [
  { id: 'controls', label: 'Controls' },
  { id: 'leaderboard', label: 'Leaderboard' },
  { id: 'radar', label: 'Top 3 Radar' },
];

const formatLabel = (value) =>
  value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

const formatMetricValue = (value) => {
  if (value === null || value === undefined) return 'N/A';
  if (typeof value !== 'number') return String(value);
  if (Math.abs(value) <= 1) return value.toFixed(3);
  if (Math.abs(value) >= 100) return value.toFixed(1);
  return value.toFixed(2);
};

const rerank = (predictions, weights) =>
  predictions
    .map((team) => {
      const composite = Object.entries(weights).reduce(
        (sum, [cat, w]) => sum + (team.category_scores[cat]?.score || 50) * w,
        0,
      );
      return { ...team, composite_score: composite };
    })
    .sort((a, b) => b.composite_score - a.composite_score)
    .map((team, i) => ({ ...team, rank: i + 1 }));

const normalizeWeights = (weights) => {
  const total = Object.values(weights).reduce((s, v) => s + v, 0);
  if (total === 0) return weights;
  const result = {};
  for (const k of Object.keys(weights)) result[k] = weights[k] / total;
  return result;
};

const toDateStr = (d) => d.toISOString().slice(0, 10);

const RadarTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <Box sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', p: 1.25, borderRadius: 1 }}>
      <Typography variant="subtitle2" sx={{ mb: 0.5 }}>{label}</Typography>
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
  const [refetching, setRefetching] = useState(false);
  const [error, setError] = useState(null);
  const [payload, setPayload] = useState(null);
  const [expandedTeam, setExpandedTeam] = useState(null);

  // Controls state
  const [activeDatePreset, setActiveDatePreset] = useState('1Y');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');
  const [activeWeightPreset, setActiveWeightPreset] = useState('Balanced');
  const [weights, setWeights] = useState(WEIGHT_PRESETS.Balanced);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Section navigation
  const [activeSection, setActiveSection] = useState('controls');
  const sectionRefs = useRef({});
  const observerRef = useRef(null);

  // Intersection observer for active section tracking
  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.dataset.section);
          }
        }
      },
      { rootMargin: '-15% 0px -60% 0px' },
    );

    const refs = sectionRefs.current;
    for (const id of Object.keys(refs)) {
      if (refs[id]) observerRef.current.observe(refs[id]);
    }

    return () => observerRef.current?.disconnect();
  }, [payload]);

  const setSectionRef = useCallback((id) => (el) => {
    sectionRefs.current[id] = el;
    if (el && observerRef.current) observerRef.current.observe(el);
  }, []);

  const handleSectionSelect = useCallback((id) => {
    setActiveSection(id);
    sectionRefs.current[id]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  // Fetch predictions
  const fetchPredictions = useCallback(async (startDate, endDate, isRefetch = false) => {
    try {
      if (isRefetch) setRefetching(true);
      else setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (startDate) params.set('start_date', startDate);
      if (endDate) params.set('end_date', endDate);
      const qs = params.toString();
      const url = `${config.API_URL}/teams/ipl-predictions${qs ? `?${qs}` : ''}`;

      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setPayload(await response.json());
    } catch (err) {
      console.error('Failed to fetch IPL predictions:', err);
      setError('Failed to load IPL predictions.');
    } finally {
      setLoading(false);
      setRefetching(false);
    }
  }, []);

  // Initial load
  useEffect(() => { fetchPredictions(); }, [fetchPredictions]);

  // Date preset handler
  const handleDatePreset = useCallback((preset) => {
    setActiveDatePreset(preset.label);
    if (preset.label === 'Custom') return;

    let start, end;
    if (preset.start && preset.end) {
      start = preset.start;
      end = preset.end;
    } else if (preset.years) {
      const now = new Date();
      end = toDateStr(now);
      const s = new Date(now);
      s.setFullYear(s.getFullYear() - preset.years);
      start = toDateStr(s);
    }
    fetchPredictions(start, end, !!payload);
  }, [fetchPredictions, payload]);

  const handleCustomDateFetch = useCallback(() => {
    if (customStart && customEnd) {
      fetchPredictions(customStart, customEnd, !!payload);
    }
  }, [customStart, customEnd, fetchPredictions, payload]);

  // Weight handlers
  const handleWeightPreset = useCallback((name) => {
    setActiveWeightPreset(name);
    setWeights(WEIGHT_PRESETS[name]);
  }, []);

  const handleSliderChange = useCallback((cat, newVal) => {
    setWeights((prev) => {
      const updated = { ...prev, [cat]: newVal / 100 };
      const normalized = normalizeWeights(updated);
      return normalized;
    });
    setActiveWeightPreset(null);
  }, []);

  // Derived data
  const rawPredictions = useMemo(() => payload?.predictions ?? [], [payload]);
  const modelExplainer = useMemo(() => payload?.model_explainer ?? {}, [payload]);
  const categoryMetricKeys = useMemo(() => modelExplainer.category_metric_keys || {}, [modelExplainer]);

  const predictions = useMemo(
    () => rawPredictions.length ? rerank(rawPredictions, weights) : [],
    [rawPredictions, weights],
  );

  const topThree = useMemo(() => predictions.slice(0, 3), [predictions]);

  const radarData = useMemo(
    () => CATEGORY_KEYS.map((cat) => {
      const point = { category: formatLabel(cat) };
      topThree.forEach((team) => {
        point[team.team] = Number(team.category_scores?.[cat]?.score || 0);
      });
      return point;
    }),
    [topThree],
  );

  // Initial load spinner
  if (loading && !payload) {
    return (
      <Box sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ pb: 3 }}>
      <VenueSectionTabs
        sections={SECTIONS}
        activeSectionId={activeSection}
        onSectionSelect={handleSectionSelect}
      />

      {/* Section 1: Controls */}
      <Box
        ref={setSectionRef('controls')}
        data-section="controls"
        sx={{ scrollMarginTop: '56px', px: { xs: 2, sm: 2.5 }, pt: 2.5 }}
      >
        <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
          IPL Championship Predictions
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Composite percentile ranking across 8 categories.
        </Typography>

        {/* Date range */}
        <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', letterSpacing: '0.06em', textTransform: 'uppercase', display: 'block', mb: 0.75 }}>
          Date Range
        </Typography>
        <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mb: 1.5 }}>
          {DATE_PRESETS.map((preset) => (
            <Chip
              key={preset.label}
              label={preset.label}
              size="small"
              variant={activeDatePreset === preset.label ? 'filled' : 'outlined'}
              color={activeDatePreset === preset.label ? 'primary' : 'default'}
              onClick={() => handleDatePreset(preset)}
              sx={{ fontWeight: 600, fontSize: '0.8rem' }}
            />
          ))}
          {refetching && <CircularProgress size={20} sx={{ ml: 0.5 }} />}
        </Box>

        <Collapse in={activeDatePreset === 'Custom'}>
          <Box sx={{ display: 'flex', gap: 1.5, mb: 1.5, alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <Box>
              <Typography variant="caption" color="text.secondary">Start</Typography>
              <input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                style={{ display: 'block', padding: '6px 8px', border: '1px solid #ccc', borderRadius: 6, fontSize: 14 }}
              />
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">End</Typography>
              <input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                style={{ display: 'block', padding: '6px 8px', border: '1px solid #ccc', borderRadius: 6, fontSize: 14 }}
              />
            </Box>
            <Chip
              label="Apply"
              size="small"
              color="primary"
              onClick={handleCustomDateFetch}
              disabled={!customStart || !customEnd}
              sx={{ fontWeight: 600, mb: 0.5 }}
            />
          </Box>
        </Collapse>

        {/* Weight presets */}
        <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', letterSpacing: '0.06em', textTransform: 'uppercase', display: 'block', mb: 0.75 }}>
          Weight Preset
        </Typography>
        <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mb: 1 }}>
          {Object.keys(WEIGHT_PRESETS).map((name) => (
            <Chip
              key={name}
              label={name}
              size="small"
              variant={activeWeightPreset === name ? 'filled' : 'outlined'}
              color={activeWeightPreset === name ? 'primary' : 'default'}
              onClick={() => handleWeightPreset(name)}
              sx={{ fontWeight: 600, fontSize: '0.8rem' }}
            />
          ))}
        </Box>

        <Box
          onClick={() => setShowAdvanced((v) => !v)}
          sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, cursor: 'pointer', mb: 1, color: 'primary.main' }}
        >
          <TuneIcon sx={{ fontSize: 16 }} />
          <Typography variant="caption" sx={{ fontWeight: 600 }}>
            {showAdvanced ? 'Hide weights' : 'Customize weights'}
          </Typography>
        </Box>

        <Collapse in={showAdvanced}>
          <Box sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
            gap: { xs: 1, sm: 1.5 },
            mb: 1.5,
            p: 2,
            borderRadius: 3,
            border: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
          }}>
            {CATEGORY_KEYS.map((cat) => (
              <Box key={cat}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: -0.5 }}>
                  <Typography variant="caption">{formatLabel(cat)}</Typography>
                  <Typography variant="caption" sx={{ fontWeight: 700 }}>
                    {Math.round((weights[cat] || 0) * 100)}%
                  </Typography>
                </Box>
                <Slider
                  size="small"
                  min={0}
                  max={40}
                  value={Math.round((weights[cat] || 0) * 100)}
                  onChange={(_, v) => handleSliderChange(cat, v)}
                  sx={{ py: 1 }}
                />
              </Box>
            ))}
            <Box sx={{ gridColumn: '1 / -1' }}>
              <Chip
                label="Reset"
                size="small"
                variant="outlined"
                onClick={() => handleWeightPreset(activeWeightPreset || 'Balanced')}
                sx={{ fontWeight: 600 }}
              />
            </Box>
          </Box>
        </Collapse>

        {/* Footer meta */}
        {payload?.date_range && (
          <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mt: 1, mb: 1 }}>
            <Chip size="small" variant="outlined" label={`${payload.date_range.start} → ${payload.date_range.end}`} />
            {payload.total_teams ? <Chip size="small" variant="outlined" label={`${payload.total_teams} teams`} /> : null}
            {modelExplainer.version ? <Chip size="small" variant="outlined" label={`v${modelExplainer.version}`} /> : null}
          </Box>
        )}

        {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}
      </Box>

      {/* Section 2: Leaderboard */}
      <Box
        ref={setSectionRef('leaderboard')}
        data-section="leaderboard"
        sx={{ scrollMarginTop: '56px', px: { xs: 2, sm: 2.5 }, pt: 3 }}
      >
        <Typography variant="h6" sx={{ fontWeight: 700, mb: 1.5 }}>
          Leaderboard
        </Typography>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {predictions.map((team) => {
            const isExpanded = expandedTeam === team.team;
            return (
              <Box
                key={team.team}
                sx={{
                  borderRadius: 3,
                  border: '1px solid',
                  borderColor: 'divider',
                  boxShadow: 1,
                  bgcolor: 'background.paper',
                  overflow: 'hidden',
                  cursor: 'pointer',
                }}
                onClick={() => setExpandedTeam(isExpanded ? null : team.team)}
              >
                {/* Header */}
                <Box sx={{ px: 2, py: 1.5 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Box sx={{
                      width: 28, height: 28, borderRadius: '50%',
                      bgcolor: 'primary.main', color: 'white',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '0.75rem', fontWeight: 700, flexShrink: 0,
                    }}>
                      {team.rank}
                    </Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
                      {team.team}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {team.team_full_name}
                    </Typography>
                    <Chip
                      size="small"
                      color="primary"
                      label={Number(team.composite_score || 0).toFixed(1)}
                      sx={{ fontWeight: 700, minWidth: 48 }}
                    />
                    <ExpandMoreIcon sx={{
                      fontSize: 20, color: 'text.secondary',
                      transform: isExpanded ? 'rotate(180deg)' : 'none',
                      transition: 'transform 0.2s',
                    }} />
                  </Box>

                  {/* Category mini-bars */}
                  <Box sx={{ display: 'grid', gap: 0.75, gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, 1fr)' } }}>
                    {CATEGORY_KEYS.map((cat) => {
                      const score = Number(team.category_scores?.[cat]?.score || 0);
                      return (
                        <Box key={cat} sx={{ minWidth: 0 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="caption" color="text.secondary" noWrap>
                              {formatLabel(cat)}
                            </Typography>
                            <Typography variant="caption" sx={{ fontWeight: 600, ml: 0.5 }}>
                              {score.toFixed(0)}
                            </Typography>
                          </Box>
                          <LinearProgress
                            variant="determinate"
                            value={Math.max(0, Math.min(100, score))}
                            sx={{ height: 6, borderRadius: 8, mt: 0.25 }}
                          />
                        </Box>
                      );
                    })}
                  </Box>
                </Box>

                {/* Expandable detail */}
                <Collapse in={isExpanded}>
                  <Box sx={{
                    px: 2, pb: 2, pt: 0.5,
                    borderTop: '1px solid',
                    borderColor: 'divider',
                    display: 'grid',
                    gap: 1.25,
                    gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
                  }}>
                    {CATEGORY_KEYS.map((cat) => {
                      const category = team.category_scores?.[cat] || {};
                      const raw = category.raw || {};
                      const scoringKeySet = new Set(categoryMetricKeys[cat] || []);
                      const scoringEntries = Object.entries(raw).filter(([k]) => scoringKeySet.has(k));
                      const supportEntries = Object.entries(raw).filter(([k]) => !scoringKeySet.has(k));
                      return (
                        <Box key={cat} sx={{ p: 1.25, borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
                            {formatLabel(cat)}: {Number(category.score || 0).toFixed(1)}
                          </Typography>
                          {scoringEntries.length > 0 && (
                            <Box sx={{ mb: supportEntries.length ? 0.75 : 0 }}>
                              <Typography variant="caption" sx={{ fontWeight: 700, display: 'block', mb: 0.25 }}>
                                Scoring Metrics
                              </Typography>
                              {scoringEntries.map(([k, v]) => (
                                <Typography key={k} variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                                  {formatLabel(k)}: {formatMetricValue(v)}
                                </Typography>
                              ))}
                            </Box>
                          )}
                          {supportEntries.length > 0 && (
                            <Box>
                              <Typography variant="caption" sx={{ fontWeight: 700, display: 'block', mb: 0.25 }}>
                                Data (Coverage / Volumes)
                              </Typography>
                              {supportEntries.map(([k, v]) => (
                                <Typography key={k} variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                                  {formatLabel(k)}: {formatMetricValue(v)}
                                </Typography>
                              ))}
                            </Box>
                          )}
                        </Box>
                      );
                    })}
                  </Box>
                </Collapse>
              </Box>
            );
          })}
        </Box>
      </Box>

      {/* Section 3: Top 3 Radar */}
      <Box
        ref={setSectionRef('radar')}
        data-section="radar"
        sx={{ scrollMarginTop: '56px', px: { xs: 2, sm: 2.5 }, pt: 3, pb: 2 }}
      >
        <Typography variant="h6" sx={{ fontWeight: 700, mb: 1.5 }}>
          Top 3 Radar
        </Typography>

        {topThree.length > 0 && (
          <Box sx={{
            borderRadius: 3, border: '1px solid', borderColor: 'divider',
            boxShadow: 1, bgcolor: 'background.paper', p: { xs: 1, sm: 2 },
          }}>
            <Box sx={{ width: '100%', height: { xs: 280, md: 380 } }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} outerRadius="72%">
                  <PolarGrid />
                  <PolarAngleAxis dataKey="category" tick={{ fontSize: 11 }} />
                  <PolarRadiusAxis domain={[0, 100]} tickCount={6} />
                  {topThree.map((team, i) => (
                    <Radar
                      key={team.team}
                      name={`${team.rank}. ${team.team}`}
                      dataKey={team.team}
                      stroke={TEAM_COLORS[i % TEAM_COLORS.length]}
                      fill={TEAM_COLORS[i % TEAM_COLORS.length]}
                      fillOpacity={0.18}
                      strokeWidth={2}
                    />
                  ))}
                  <Legend />
                  <Tooltip content={<RadarTooltip />} />
                </RadarChart>
              </ResponsiveContainer>
            </Box>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default IPLPredictions;
