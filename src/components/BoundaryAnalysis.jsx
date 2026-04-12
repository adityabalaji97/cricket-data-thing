import React, { useState, useEffect } from 'react';
import {
  Box, Typography, ToggleButtonGroup, ToggleButton, CircularProgress, Alert,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  useMediaQuery, useTheme,
} from '@mui/material';
import Card from './ui/Card';
import { fetchAnalyticsJson } from '../utils/analyticsApi';
import { colors as designColors } from '../theme/designSystem';

const MIN_BALLS = 30;

const PHASES = ['powerplay', 'middle', 'death'];
const PHASE_LABELS = { powerplay: 'PP', middle: 'Mid', death: 'Death' };

const formatShotName = (name) => {
  if (!name) return '';
  return name
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
};

const getBoundaryStyle = (pct) => {
  if (pct >= 30) return { bgcolor: designColors.success[700], color: '#fff' };
  if (pct >= 20) return { bgcolor: designColors.success[500], color: '#fff' };
  if (pct >= 10) return { bgcolor: designColors.success[50], color: designColors.neutral[900] };
  return { bgcolor: designColors.neutral[200], color: designColors.neutral[900] };
};

const getTopShot = (shots) => {
  if (!shots) return null;
  let best = null;
  Object.entries(shots).forEach(([name, data]) => {
    if (!best || data.boundaries > best.boundaries) {
      best = { name, ...data };
    }
  });
  return best;
};

const getTotalBalls = (data) => {
  if (!data?.overall?.groups) return 0;
  return Object.values(data.overall.groups).reduce((sum, g) => sum + (g.total_balls || 0), 0);
};

const buildDetailRows = (groups) => {
  if (!groups) return [];
  return Object.entries(groups)
    .filter(([, data]) => data.total_balls > 0)
    .map(([key, data]) => ({ key, ...data }));
};

/* ---------- Stat Card ---------- */
const StatCard = ({ group, isMobile }) => {
  if (!group || group.total_balls === 0) {
    return (
      <Box sx={{
        p: 1.5, borderRadius: 1, border: `1px solid ${designColors.neutral[200]}`,
        bgcolor: designColors.neutral[50], minHeight: 80,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Typography variant="caption" color="text.disabled">No data</Typography>
      </Box>
    );
  }

  const pct = group.boundary_pct ?? (group.total_balls > 0 ? +(group.boundaries / group.total_balls * 100).toFixed(1) : 0);
  const style = getBoundaryStyle(pct);
  const topShot = getTopShot(group.shots);

  return (
    <Box sx={{
      p: 1.5, borderRadius: 1, border: `1px solid ${designColors.neutral[200]}`,
      bgcolor: designColors.neutral[0], display: 'flex', flexDirection: 'column', gap: 0.5,
    }}>
      {/* Boundary % badge */}
      <Box sx={{
        display: 'inline-flex', alignSelf: 'flex-start',
        px: 1, py: 0.25, borderRadius: 1,
        bgcolor: style.bgcolor, color: style.color,
      }}>
        <Typography variant="body1" sx={{ fontWeight: 700, fontSize: isMobile ? '1rem' : '1.125rem' }}>
          {pct.toFixed(1)}%
        </Typography>
      </Box>

      {/* 4s × 6s */}
      <Typography variant="body2" sx={{ fontWeight: 500 }}>
        {group.fours}×4&nbsp;&nbsp;{group.sixes}×6
      </Typography>

      {/* Balls */}
      <Typography variant="caption" color="text.secondary">
        {group.total_balls} balls
      </Typography>

      {/* Top shot */}
      {topShot && topShot.boundaries > 0 && (
        <Typography variant="caption" sx={{ color: designColors.neutral[500], fontStyle: 'italic' }}>
          {formatShotName(topShot.name)}
        </Typography>
      )}

      {/* Thin bar */}
      <Box sx={{ mt: 0.5, height: 4, borderRadius: 2, bgcolor: designColors.neutral[100], overflow: 'hidden' }}>
        <Box sx={{
          height: '100%', borderRadius: 2,
          width: `${Math.min(pct, 100)}%`,
          bgcolor: pct >= 20 ? designColors.success[500] : pct >= 10 ? designColors.success[600] : designColors.neutral[400],
        }} />
      </Box>
    </Box>
  );
};

/* ---------- Row of cards for one group ---------- */
const CardRow = ({ label, phaseData, isMobile }) => (
  <Box sx={{ display: 'contents' }}>
    {/* Row label */}
    <Box sx={{
      display: 'flex', alignItems: 'center',
      fontWeight: 600, fontSize: '0.875rem',
      pr: 1, minWidth: isMobile ? 'auto' : 70,
    }}>
      {label}
    </Box>
    {PHASES.map((phase) => (
      <StatCard key={phase} group={phaseData[phase]} isMobile={isMobile} />
    ))}
  </Box>
);

/* ---------- Build grid data ---------- */
const buildGridRows = (data, drillDown, context) => {
  if (!data) return [];

  const isBowler = context === 'bowler';

  if (drillDown && !isBowler) {
    // Bowl style drill-down: collect all styles across phases
    const allStyles = new Set();
    PHASES.forEach((phase) => {
      const groups = data.phases?.[phase]?.groups;
      if (!groups) return;
      Object.values(groups).forEach((g) => {
        if (g.styles) Object.keys(g.styles).forEach((s) => allStyles.add(s));
      });
    });

    return Array.from(allStyles).sort().map((style) => {
      const phaseData = {};
      PHASES.forEach((phase) => {
        const groups = data.phases?.[phase]?.groups;
        let merged = { total_balls: 0, boundaries: 0, fours: 0, sixes: 0, total_runs: 0, shots: {} };
        if (groups) {
          Object.values(groups).forEach((g) => {
            const s = g.styles?.[style];
            if (s) {
              merged.total_balls += s.total_balls || 0;
              merged.boundaries += s.boundaries || 0;
              merged.fours += s.fours || 0;
              merged.sixes += s.sixes || 0;
              merged.total_runs += s.total_runs || 0;
              if (s.shots) {
                Object.entries(s.shots).forEach(([shotName, shotData]) => {
                  if (!merged.shots[shotName]) merged.shots[shotName] = { boundaries: 0 };
                  merged.shots[shotName].boundaries += shotData.boundaries || 0;
                });
              }
            }
          });
        }
        merged.boundary_pct = merged.total_balls > 0 ? +(merged.boundaries / merged.total_balls * 100).toFixed(1) : 0;
        phaseData[phase] = merged;
      });
      return { label: style, phaseData };
    }).filter((row) => PHASES.some((p) => row.phaseData[p].total_balls > 0));
  }

  // Standard: pace/spin rows (or LHB/RHB for bowler)
  const groupKeys = data.overall?.groups ? Object.keys(data.overall.groups) : [];
  return groupKeys.map((gk) => {
    const phaseData = {};
    PHASES.forEach((phase) => {
      phaseData[phase] = data.phases?.[phase]?.groups?.[gk] || null;
    });
    return { label: gk.toUpperCase(), phaseData };
  });
};

/* ---------- Main component ---------- */
const BoundaryAnalysis = ({ context, name, startDate, endDate, leagues, includeInternational, isMobile: isMobileProp }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [drillDown, setDrillDown] = useState(false);

  const theme = useTheme();
  const isMobileDetected = useMediaQuery(theme.breakpoints.down('sm'));
  const isMobile = isMobileProp !== undefined ? isMobileProp : isMobileDetected;

  useEffect(() => {
    if (!name || !context) return;

    setLoading(true);
    setError(null);

    const params = { context, name };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (leagues?.length) params.leagues = leagues;
    if (includeInternational) params.include_international = true;

    fetchAnalyticsJson('/boundary-analysis', params)
      .then((result) => {
        setData(result);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [context, name, startDate, endDate, leagues, includeInternational]);

  if (loading) {
    return (
      <Card isMobile={isMobile}>
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress size={28} />
        </Box>
      </Card>
    );
  }

  if (error) {
    return (
      <Card isMobile={isMobile}>
        <Alert severity="error" sx={{ mb: 1 }}>Failed to load boundary analysis</Alert>
      </Card>
    );
  }

  if (!data || getTotalBalls(data) < MIN_BALLS) return null;

  const gridRows = buildGridRows(data, drillDown, context);
  const isBowlerCtx = context === 'bowler';
  const dimLabel = isBowlerCtx ? 'Bat Hand' : 'Bowl Type';

  // Detail rows from overall for the summary table
  const detailRows = buildDetailRows(data.overall?.groups);

  return (
    <Card isMobile={isMobile}>
      <Typography variant="h6" gutterBottom>
        Boundary Analysis
      </Typography>

      {/* Controls */}
      {context !== 'bowler' && (
        <Box sx={{ mb: 2 }}>
          <ToggleButtonGroup
            value={drillDown ? 'style' : 'type'}
            exclusive
            onChange={(_, v) => v && setDrillDown(v === 'style')}
            size="small"
          >
            <ToggleButton value="type">Pace / Spin</ToggleButton>
            <ToggleButton value="style">Bowl Style</ToggleButton>
          </ToggleButtonGroup>
        </Box>
      )}

      {/* Card Grid */}
      {gridRows.length > 0 && (
        <Box sx={{
          display: 'grid',
          gridTemplateColumns: isMobile ? 'auto 1fr 1fr' : 'auto 1fr 1fr 1fr',
          gap: 1,
          mb: 3,
        }}>
          {/* Column headers */}
          <Box />
          {(isMobile ? PHASES.slice(0, 2) : PHASES).map((phase) => (
            <Typography key={phase} variant="caption" sx={{
              fontWeight: 600, textAlign: 'center', color: designColors.neutral[500],
              textTransform: 'uppercase', letterSpacing: '0.05em', pb: 0.5,
            }}>
              {PHASE_LABELS[phase]}
            </Typography>
          ))}

          {/* Data rows */}
          {gridRows.map((row) => (
            <React.Fragment key={row.label}>
              <Box sx={{
                display: 'flex', alignItems: 'center',
                fontWeight: 600, fontSize: '0.8rem',
                pr: 1, minWidth: isMobile ? 'auto' : 70,
              }}>
                {row.label}
              </Box>
              {(isMobile ? PHASES.slice(0, 2) : PHASES).map((phase) => (
                <StatCard key={phase} group={row.phaseData[phase]} isMobile={isMobile} />
              ))}
            </React.Fragment>
          ))}

          {/* On mobile, show death phase as a separate row below */}
          {isMobile && gridRows.length > 0 && (
            <>
              <Box />
              <Typography variant="caption" sx={{
                fontWeight: 600, textAlign: 'center', color: designColors.neutral[500],
                textTransform: 'uppercase', letterSpacing: '0.05em', pt: 1, pb: 0.5,
                gridColumn: 'span 2',
              }}>
                Death
              </Typography>
              {gridRows.map((row) => (
                <React.Fragment key={`death-${row.label}`}>
                  <Box sx={{
                    display: 'flex', alignItems: 'center',
                    fontWeight: 600, fontSize: '0.8rem', pr: 1,
                  }}>
                    {row.label}
                  </Box>
                  <Box sx={{ gridColumn: 'span 2' }}>
                    <StatCard group={row.phaseData.death} isMobile={isMobile} />
                  </Box>
                </React.Fragment>
              ))}
            </>
          )}
        </Box>
      )}

      {/* Detail Table */}
      {detailRows.length > 0 && (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{dimLabel}</TableCell>
                <TableCell align="right">Balls</TableCell>
                <TableCell align="right">Runs</TableCell>
                <TableCell align="right">4s</TableCell>
                <TableCell align="right">6s</TableCell>
                <TableCell align="right">Boundaries</TableCell>
                <TableCell align="right">Boundary %</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {detailRows.map((row) => (
                <TableRow key={row.key}>
                  <TableCell sx={{ fontWeight: 500 }}>{row.key.toUpperCase()}</TableCell>
                  <TableCell align="right">{row.total_balls}</TableCell>
                  <TableCell align="right">{row.total_runs}</TableCell>
                  <TableCell align="right">{row.fours}</TableCell>
                  <TableCell align="right">{row.sixes}</TableCell>
                  <TableCell align="right">{row.boundaries}</TableCell>
                  <TableCell align="right">{row.boundary_pct}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Card>
  );
};

export default BoundaryAnalysis;
