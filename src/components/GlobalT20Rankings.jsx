import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Collapse,
  LinearProgress,
  TextField,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import config from '../config';
import VenueSectionTabs from './VenueSectionTabs';

const SECTIONS = [
  { id: 'controls', label: 'Controls' },
  { id: 'batting', label: 'Batting' },
  { id: 'bowling', label: 'Bowling' },
];

const DATE_PRESETS = [
  { label: '1Y', years: 1 },
  { label: '2Y', years: 2 },
  { label: '3Y', years: 3 },
  { label: 'Custom' },
];

const BOWL_KIND_OPTIONS = [
  { id: 'all', label: 'All' },
  { id: 'pace', label: 'Pace' },
  { id: 'spin', label: 'Spin' },
];

const SORT_OPTIONS = [
  { id: 'quality_score', label: 'Quality' },
  { id: 'strike_factor', label: 'Strike' },
  { id: 'control_factor', label: 'Control' },
  { id: 'rank', label: 'Rank' },
];

const toDateStr = (d) => d.toISOString().slice(0, 10);

const getPresetRange = (preset) => {
  const end = new Date();
  const start = new Date(end);
  start.setFullYear(end.getFullYear() - (preset.years || 2));
  return {
    start: toDateStr(start),
    end: toDateStr(end),
  };
};

const formatMetricLabel = (key) =>
  key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

const formatMetricValue = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
  return Number(value).toFixed(3);
};

const TrajectoryTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null;
  return (
    <Box sx={{ p: 1, border: '1px solid', borderColor: 'divider', borderRadius: 1, bgcolor: 'background.paper' }}>
      <Typography variant="caption" sx={{ display: 'block', fontWeight: 700 }}>{label}</Typography>
      <Typography variant="caption" sx={{ display: 'block' }}>
        Score: {payload[0].value ?? 'N/A'}
      </Typography>
    </Box>
  );
};

const RankingCard = ({
  row,
  mode,
  expanded,
  onToggle,
  trajectory,
  trajectoryLoading,
}) => {
  const baseParams = row.base_params || {};
  const perCompetition = row.per_competition || {};
  const hasTrajectoryValues = Array.isArray(trajectory)
    && trajectory.some((point) => point?.quality_score !== null && point?.quality_score !== undefined);

  return (
    <Box
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 3,
        bgcolor: 'background.paper',
        boxShadow: 1,
        overflow: 'hidden',
      }}
    >
      <Box
        onClick={onToggle}
        sx={{
          px: 1.5,
          py: 1.25,
          cursor: 'pointer',
          borderBottom: expanded ? '1px solid' : 'none',
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <Box
            sx={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              bgcolor: 'primary.main',
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '0.78rem',
              flexShrink: 0,
            }}
          >
            {row.rank}
          </Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, flex: 1, minWidth: 0 }} noWrap>
            {row.player}
          </Typography>
          <Chip size="small" color="primary" label={Number(row.quality_score || 0).toFixed(1)} sx={{ fontWeight: 700 }} />
          <ExpandMoreIcon
            sx={{
              transform: expanded ? 'rotate(180deg)' : 'none',
              transition: 'transform 0.2s',
              color: 'text.secondary',
            }}
          />
        </Box>

        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr', gap: 0.7 }}>
          {[
            { label: 'Quality', value: row.quality_score },
            { label: 'Strike Factor', value: row.strike_factor },
            { label: 'Control Factor', value: row.control_factor },
          ].map((metric) => (
            <Box key={metric.label}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="caption" color="text.secondary">{metric.label}</Typography>
                <Typography variant="caption" sx={{ fontWeight: 700 }}>{Number(metric.value || 0).toFixed(1)}</Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={Math.max(0, Math.min(100, Number(metric.value || 0)))}
                sx={{ height: 6, borderRadius: 999, mt: 0.25 }}
              />
            </Box>
          ))}
        </Box>
      </Box>

      <Collapse in={expanded}>
        <Box sx={{ px: 1.5, py: 1.25, display: 'grid', gap: 1.25 }}>
          <Box>
            <Typography variant="caption" sx={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Base Parameters ({mode === 'batting' ? 'SR / Control / Intent / Reliability' : 'EconInv / Dot / Restriction / Consistency'})
            </Typography>
            <Box sx={{ mt: 0.5, display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0,1fr))', gap: 0.5 }}>
              {Object.entries(baseParams).map(([key, value]) => (
                <Typography key={key} variant="caption" color="text.secondary">
                  {formatMetricLabel(key)}: {formatMetricValue(value)}
                </Typography>
              ))}
            </Box>
          </Box>

          <Box>
            <Typography variant="caption" sx={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Per Competition
            </Typography>
            <Box sx={{ mt: 0.5, border: '1px solid', borderColor: 'divider', borderRadius: 1, overflow: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ background: 'rgba(0,0,0,0.03)' }}>
                    <th style={{ textAlign: 'left', padding: '6px 8px' }}>Competition</th>
                    <th style={{ textAlign: 'right', padding: '6px 8px' }}>Wt</th>
                    <th style={{ textAlign: 'right', padding: '6px 8px' }}>Balls</th>
                    <th style={{ textAlign: 'right', padding: '6px 8px' }}>Primary</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(perCompetition).map(([competition, vals]) => {
                    const primary = mode === 'batting' ? vals.sr : vals.econ_inv;
                    return (
                      <tr key={competition}>
                        <td style={{ padding: '6px 8px', borderTop: '1px solid #eee' }}>{competition}</td>
                        <td style={{ textAlign: 'right', padding: '6px 8px', borderTop: '1px solid #eee' }}>{Number(vals.weight || 1).toFixed(2)}</td>
                        <td style={{ textAlign: 'right', padding: '6px 8px', borderTop: '1px solid #eee' }}>{vals.balls || 0}</td>
                        <td style={{ textAlign: 'right', padding: '6px 8px', borderTop: '1px solid #eee' }}>{primary !== undefined && primary !== null ? Number(primary).toFixed(2) : 'N/A'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Box>
          </Box>

          <Box>
            <Typography variant="caption" sx={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Career Trajectory (Last 6 Months)
            </Typography>
            <Box sx={{ mt: 0.5, height: 120, border: '1px solid', borderColor: 'divider', borderRadius: 1, p: 0.75 }}>
              {trajectoryLoading ? (
                <Box sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CircularProgress size={18} />
                </Box>
              ) : hasTrajectoryValues ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trajectory} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                    <YAxis hide domain={[0, 100]} />
                    <Tooltip content={<TrajectoryTooltip />} />
                    <Line
                      type="monotone"
                      dataKey="quality_score"
                      stroke="#1976d2"
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Box sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Typography variant="caption" color="text.secondary">No trajectory data</Typography>
                </Box>
              )}
            </Box>
          </Box>
        </Box>
      </Collapse>
    </Box>
  );
};

const GlobalT20Rankings = () => {
  const defaultRange = getPresetRange({ years: 2 });

  const [loading, setLoading] = useState(true);
  const [refetching, setRefetching] = useState(false);
  const [error, setError] = useState(null);

  const [activeDatePreset, setActiveDatePreset] = useState('2Y');
  const [startDate, setStartDate] = useState(defaultRange.start);
  const [endDate, setEndDate] = useState(defaultRange.end);
  const [customStart, setCustomStart] = useState(defaultRange.start);
  const [customEnd, setCustomEnd] = useState(defaultRange.end);

  const [bowlKind, setBowlKind] = useState('all');
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('quality_score');

  const [battingPayload, setBattingPayload] = useState(null);
  const [bowlingPayload, setBowlingPayload] = useState(null);

  const [expandedCard, setExpandedCard] = useState(null);
  const [trajectoryCache, setTrajectoryCache] = useState({});

  const [activeSection, setActiveSection] = useState('controls');
  const sectionRefs = useRef({});
  const observerRef = useRef(null);
  const hasLoadedRef = useRef(false);

  const fetchRankings = useCallback(async (newStart, newEnd, newBowlKind, isRefetch = false) => {
    try {
      if (isRefetch) setRefetching(true);
      else setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      params.set('start_date', newStart);
      params.set('end_date', newEnd);
      params.set('limit', '300');
      params.set('offset', '0');
      if (newBowlKind && newBowlKind !== 'all') params.set('bowl_kind', newBowlKind);

      const query = params.toString();
      const [batRes, bowlRes] = await Promise.all([
        fetch(`${config.API_URL}/rankings/batting?${query}`),
        fetch(`${config.API_URL}/rankings/bowling?${query}`),
      ]);

      if (!batRes.ok || !bowlRes.ok) {
        throw new Error(`HTTP ${batRes.status}/${bowlRes.status}`);
      }

      const [batData, bowlData] = await Promise.all([batRes.json(), bowlRes.json()]);
      setBattingPayload(batData);
      setBowlingPayload(bowlData);
      setTrajectoryCache({});
      setExpandedCard(null);
    } catch (err) {
      console.error('Failed to fetch rankings', err);
      setError('Failed to load global rankings.');
    } finally {
      setLoading(false);
      setRefetching(false);
    }
  }, []);

  useEffect(() => {
    fetchRankings(startDate, endDate, bowlKind, hasLoadedRef.current);
    hasLoadedRef.current = true;
  }, [fetchRankings, startDate, endDate, bowlKind]);

  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.dataset.sectionId);
          }
        }
      },
      { rootMargin: '-15% 0px -60% 0px' },
    );

    for (const section of SECTIONS) {
      const el = sectionRefs.current[section.id];
      if (el) observerRef.current.observe(el);
    }

    return () => observerRef.current?.disconnect();
  }, [battingPayload, bowlingPayload]);

  const handleSectionSelect = useCallback((sectionId) => {
    setActiveSection(sectionId);
    const el = sectionRefs.current[sectionId];
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const handleDatePreset = useCallback((preset) => {
    setActiveDatePreset(preset.label);
    if (preset.label === 'Custom') return;
    const range = getPresetRange(preset);
    setStartDate(range.start);
    setEndDate(range.end);
    setCustomStart(range.start);
    setCustomEnd(range.end);
  }, []);

  const applyCustomRange = useCallback(() => {
    if (!customStart || !customEnd) return;
    setStartDate(customStart);
    setEndDate(customEnd);
  }, [customStart, customEnd]);

  const handleBowlKind = useCallback((next) => {
    setBowlKind(next);
  }, []);

  const fetchTrajectory = useCallback(async (mode, playerName) => {
    const key = `${mode}:${playerName}`;
    if (trajectoryCache[key]?.data || trajectoryCache[key]?.loading) {
      return;
    }

    setTrajectoryCache((prev) => ({
      ...prev,
      [key]: { loading: true, data: null },
    }));

    try {
      const params = new URLSearchParams();
      params.set('start_date', startDate);
      params.set('end_date', endDate);
      params.set('snapshots', '6');
      params.set('mode', mode);
      if (bowlKind !== 'all') params.set('bowl_kind', bowlKind);

      const response = await fetch(`${config.API_URL}/rankings/player/${encodeURIComponent(playerName)}?${params.toString()}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();

      const trajectory = (data?.[mode]?.trajectory || []).map((point) => ({
        ...point,
        label: point.date ? point.date.slice(2, 7) : '--',
      }));

      setTrajectoryCache((prev) => ({
        ...prev,
        [key]: { loading: false, data: trajectory },
      }));
    } catch (err) {
      console.error('Failed to fetch trajectory', err);
      setTrajectoryCache((prev) => ({
        ...prev,
        [key]: { loading: false, data: [] },
      }));
    }
  }, [trajectoryCache, startDate, endDate, bowlKind]);

  const buildRows = useCallback((rows) => {
    const q = search.trim().toLowerCase();
    const filtered = (rows || []).filter((row) => row.player?.toLowerCase().includes(q));

    const sorted = [...filtered].sort((a, b) => {
      if (sortBy === 'rank') {
        return Number(a.rank || 999999) - Number(b.rank || 999999);
      }
      return Number(b[sortBy] || 0) - Number(a[sortBy] || 0);
    });

    return sorted;
  }, [search, sortBy]);

  const battingRows = useMemo(() => buildRows(battingPayload?.rankings || []), [battingPayload, buildRows]);
  const bowlingRows = useMemo(() => buildRows(bowlingPayload?.rankings || []), [bowlingPayload, buildRows]);

  const renderSectionMeta = (payload) => {
    if (!payload) return null;
    return (
      <Box sx={{ mt: 0.5, display: 'flex', gap: 0.75, flexWrap: 'wrap' }}>
        {payload.date_range ? (
          <Chip size="small" variant="outlined" label={`${payload.date_range.start} → ${payload.date_range.end}`} />
        ) : null}
        {payload.total !== undefined ? <Chip size="small" variant="outlined" label={`${payload.total} players`} /> : null}
        {payload.competition_weight_source ? (
          <Chip size="small" variant="outlined" label={`weights: ${payload.competition_weight_source}`} />
        ) : null}
      </Box>
    );
  };

  if (loading && !battingPayload && !bowlingPayload) {
    return (
      <Box sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ pb: 3 }}>
      <VenueSectionTabs sections={SECTIONS} activeSectionId={activeSection} onSectionSelect={handleSectionSelect} />

      <Box
        ref={(el) => { sectionRefs.current.controls = el; }}
        data-section-id="controls"
        sx={{ scrollMarginTop: '56px', px: { xs: 2, sm: 2.5 }, pt: 2.5 }}
      >
        <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>Global T20 Rankings</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Cross-league batting and bowling rankings with competition difficulty adjustments.
        </Typography>

        <Typography variant="caption" sx={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'text.secondary' }}>
          Date Range
        </Typography>
        <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mt: 0.75, mb: 1.25 }}>
          {DATE_PRESETS.map((preset) => (
            <Chip
              key={preset.label}
              label={preset.label}
              size="small"
              variant={activeDatePreset === preset.label ? 'filled' : 'outlined'}
              color={activeDatePreset === preset.label ? 'primary' : 'default'}
              onClick={() => handleDatePreset(preset)}
              sx={{ fontWeight: 600 }}
            />
          ))}
          {refetching ? <CircularProgress size={18} sx={{ ml: 0.5 }} /> : null}
        </Box>

        <Collapse in={activeDatePreset === 'Custom'}>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'flex-end', mb: 1.25 }}>
            <TextField
              label="Start"
              type="date"
              size="small"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="End"
              type="date"
              size="small"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
            <Chip
              label="Apply"
              color="primary"
              size="small"
              onClick={applyCustomRange}
              disabled={!customStart || !customEnd}
            />
          </Box>
        </Collapse>

        <Typography variant="caption" sx={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'text.secondary' }}>
          Bowl Kind
        </Typography>
        <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mt: 0.75, mb: 1.5 }}>
          {BOWL_KIND_OPTIONS.map((option) => (
            <Chip
              key={option.id}
              label={option.label}
              size="small"
              variant={bowlKind === option.id ? 'filled' : 'outlined'}
              color={bowlKind === option.id ? 'primary' : 'default'}
              onClick={() => handleBowlKind(option.id)}
              sx={{ fontWeight: 600 }}
            />
          ))}
        </Box>

        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1.5 }}>
          <TextField
            label="Search Player"
            size="small"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="e.g. V Kohli"
          />
          <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', alignItems: 'center' }}>
            <Typography variant="caption" color="text.secondary" sx={{ mr: 0.5 }}>Sort By</Typography>
            {SORT_OPTIONS.map((option) => (
              <Chip
                key={option.id}
                label={option.label}
                size="small"
                variant={sortBy === option.id ? 'filled' : 'outlined'}
                color={sortBy === option.id ? 'primary' : 'default'}
                onClick={() => setSortBy(option.id)}
                sx={{ fontWeight: 600 }}
              />
            ))}
          </Box>
        </Box>

        {error ? <Alert severity="error" sx={{ mt: 1.5 }}>{error}</Alert> : null}
      </Box>

      <Box
        ref={(el) => { sectionRefs.current.batting = el; }}
        data-section-id="batting"
        sx={{ scrollMarginTop: '56px', px: { xs: 2, sm: 2.5 }, pt: 3 }}
      >
        <Typography variant="h6" sx={{ fontWeight: 700 }}>Batting Rankings</Typography>
        {renderSectionMeta(battingPayload)}

        <Box sx={{ mt: 1.25, display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1.25 }}>
          {battingRows.map((row) => {
            const key = `batting:${row.player}`;
            const trajectory = trajectoryCache[key]?.data;
            const trajectoryLoading = trajectoryCache[key]?.loading;
            const expanded = expandedCard === key;
            return (
              <RankingCard
                key={key}
                row={row}
                mode="batting"
                expanded={expanded}
                trajectory={trajectory}
                trajectoryLoading={trajectoryLoading}
                onToggle={() => {
                  const next = expanded ? null : key;
                  setExpandedCard(next);
                  if (next) fetchTrajectory('batting', row.player);
                }}
              />
            );
          })}
          {!battingRows.length ? (
            <Typography variant="body2" color="text.secondary">No batting players match current filters.</Typography>
          ) : null}
        </Box>
      </Box>

      <Box
        ref={(el) => { sectionRefs.current.bowling = el; }}
        data-section-id="bowling"
        sx={{ scrollMarginTop: '56px', px: { xs: 2, sm: 2.5 }, pt: 3 }}
      >
        <Typography variant="h6" sx={{ fontWeight: 700 }}>Bowling Rankings</Typography>
        {renderSectionMeta(bowlingPayload)}

        <Box sx={{ mt: 1.25, display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1.25 }}>
          {bowlingRows.map((row) => {
            const key = `bowling:${row.player}`;
            const trajectory = trajectoryCache[key]?.data;
            const trajectoryLoading = trajectoryCache[key]?.loading;
            const expanded = expandedCard === key;
            return (
              <RankingCard
                key={key}
                row={row}
                mode="bowling"
                expanded={expanded}
                trajectory={trajectory}
                trajectoryLoading={trajectoryLoading}
                onToggle={() => {
                  const next = expanded ? null : key;
                  setExpandedCard(next);
                  if (next) fetchTrajectory('bowling', row.player);
                }}
              />
            );
          })}
          {!bowlingRows.length ? (
            <Typography variant="body2" color="text.secondary">No bowling players match current filters.</Typography>
          ) : null}
        </Box>
      </Box>
    </Box>
  );
};

export default GlobalT20Rankings;
