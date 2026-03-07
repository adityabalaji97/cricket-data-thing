import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Stack,
  Typography,
} from '@mui/material';
import config from '../config';

const fmt = (value, digits = 1) => {
  const n = Number(value);
  if (!Number.isFinite(n)) return 'N/A';
  return n.toFixed(digits);
};

const safePercent = (value, digits = 1) => {
  const n = Number(value);
  if (!Number.isFinite(n)) return 'N/A';
  return `${(n * 100).toFixed(digits)}%`;
};

const toPolarPoint = (angleDeg, scaledRadius, centerX, centerY) => {
  const radians = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: centerX + (scaledRadius * Math.cos(radians)),
    y: centerY + (scaledRadius * Math.sin(radians)),
  };
};

const renderWarnings = (warnings = []) => {
  if (!warnings.length) return null;
  return (
    <Stack direction="row" spacing={0.8} useFlexGap flexWrap="wrap">
      {warnings.map((warning) => (
        <Chip key={warning} size="small" color="warning" variant="outlined" label={warning} />
      ))}
    </Stack>
  );
};

const VenueBoundaryShape = ({
  venue,
  startDate,
  endDate,
  leagues = [],
  includeInternational = false,
  topTeams = null,
  isMobile = false,
}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const leaguesKey = Array.isArray(leagues) ? leagues.join('|') : '';
  const leaguesList = useMemo(
    () => (leaguesKey ? leaguesKey.split('|').filter(Boolean) : []),
    [leaguesKey],
  );

  useEffect(() => {
    if (!venue) return;
    let cancelled = false;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        leaguesList.forEach((league) => params.append('leagues', league));
        params.append('include_international', String(Boolean(includeInternational)));
        if (includeInternational && topTeams) params.append('top_teams', String(topTeams));
        params.append('min_matches', '20');
        params.append('angle_bin_size', '15');

        const url = `${config.API_URL}/visualizations/venue/${encodeURIComponent(venue)}/boundary-shape?${params.toString()}`;
        const response = await fetch(url);
        if (!response.ok) {
          const payload = await response.json().catch(() => null);
          throw new Error(payload?.detail || 'Failed to fetch boundary shape');
        }
        const payload = await response.json();
        if (!cancelled) setData(payload);
      } catch (fetchError) {
        if (!cancelled) {
          setData(null);
          setError(fetchError.message || 'Failed to fetch boundary shape');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchData();
    return () => {
      cancelled = true;
    };
  }, [venue, startDate, endDate, leaguesList, includeInternational, topTeams]);

  const chartModel = useMemo(() => {
    const bins = data?.profile_bins || [];
    const validBins = bins
      .filter((bin) => Number.isFinite(Number(bin?.r_median)) && Number(bin?.r_median) > 0)
      .sort((a, b) => Number(a.angle_bin) - Number(b.angle_bin));

    if (!validBins.length) return null;

    const rValues = validBins.map((bin) => Number(bin.r_median));
    const minR = Math.min(...rValues);
    const maxR = Math.max(...rValues);
    return {
      bins: validBins,
      minR,
      maxR,
    };
  }, [data]);

  const renderPolarProfile = () => {
    if (!chartModel) return null;

    const width = isMobile ? 320 : 420;
    const height = width;
    const centerX = width / 2;
    const centerY = height / 2;
    const maxRadius = width * 0.42;
    const minRadius = maxRadius * 0.34;

    const scaleR = (value) => {
      if (!Number.isFinite(value)) return minRadius;
      const range = chartModel.maxR - chartModel.minR;
      if (range < 1e-6) return (minRadius + maxRadius) / 2;
      const normalized = (value - chartModel.minR) / range;
      return minRadius + (normalized * (maxRadius - minRadius));
    };

    const medianPoints = chartModel.bins.map((bin) => {
      const scaledR = scaleR(Number(bin.r_median));
      return toPolarPoint(Number(bin.angle_mid_deg), scaledR, centerX, centerY);
    });
    const medianPolyline = medianPoints.map((p) => `${p.x},${p.y}`).join(' ');

    const bandOuterPoints = [];
    const bandInnerPoints = [];
    chartModel.bins.forEach((bin) => {
      const median = Number(bin.r_median);
      const iqr = Number(bin.r_iqr || 0);
      const lower = Math.max(0, median - (iqr / 2));
      const upper = median + (iqr / 2);
      bandOuterPoints.push(toPolarPoint(Number(bin.angle_mid_deg), scaleR(upper), centerX, centerY));
      bandInnerPoints.push(toPolarPoint(Number(bin.angle_mid_deg), scaleR(lower), centerX, centerY));
    });
    const bandPolygon = [
      ...bandOuterPoints.map((p) => `${p.x},${p.y}`),
      ...bandInnerPoints.reverse().map((p) => `${p.x},${p.y}`),
    ].join(' ');

    const rings = [0.34, 0.56, 0.78, 1.0].map((ratio, idx) => (
      <circle
        key={`ring-${idx}`}
        cx={centerX}
        cy={centerY}
        r={maxRadius * ratio}
        fill="none"
        stroke="#e2e8f0"
        strokeDasharray={idx === 3 ? 'none' : '4,4'}
      />
    ));

    const spokes = Array.from({ length: 24 }).map((_, idx) => {
      const angle = (idx * 15) - 90;
      const radians = (angle * Math.PI) / 180;
      const x2 = centerX + (maxRadius * Math.cos(radians));
      const y2 = centerY + (maxRadius * Math.sin(radians));
      return (
        <line
          key={`spoke-${idx}`}
          x1={centerX}
          y1={centerY}
          x2={x2}
          y2={y2}
          stroke="#f1f5f9"
        />
      );
    });

    return (
      <Box sx={{ display: 'flex', justifyContent: 'center' }}>
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ maxWidth: '100%', height: 'auto' }}>
          <circle cx={centerX} cy={centerY} r={maxRadius} fill="#fafafa" stroke="#dbe3ea" strokeWidth="2" />
          {spokes}
          {rings}
          {bandPolygon ? (
            <polygon points={bandPolygon} fill="rgba(59, 130, 246, 0.15)" stroke="none" />
          ) : null}
          <polygon points={medianPolyline} fill="none" stroke="#1d4ed8" strokeWidth="2.3" />
          {medianPoints.map((point, idx) => (
            <circle key={`median-point-${idx}`} cx={point.x} cy={point.y} r={2.2} fill="#1d4ed8" />
          ))}
          <circle cx={centerX} cy={centerY} r={5} fill="#111827" />
        </svg>
      </Box>
    );
  };

  if (loading && !data) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 2 }}>
        <CircularProgress size={22} />
        <Typography variant="body2" color="text.secondary">Loading boundary shape profile...</Typography>
      </Box>
    );
  }

  if (error && !loading) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!data) return null;

  if ((data?.quality?.fours_total || 0) === 0) {
    return (
      <Alert severity="info">
        No boundary-shape data is available for this venue/filter combination.
      </Alert>
    );
  }

  const confidence = data?.confidence || {};
  const quality = data?.quality || {};
  const sample = data?.sample || {};
  const summary = data?.summary || {};
  const diagnostics = data?.diagnostics || {};

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      <Stack direction="row" spacing={0.8} useFlexGap flexWrap="wrap">
        <Chip size="small" color="primary" label={`Confidence ${fmt(confidence.confidence_score, 1)}/100`} />
        <Chip size="small" label={`Matches used ${sample.matches_used || 0}`} />
        <Chip size="small" label={`Non-sentinel 4s ${safePercent(quality.nonzero_rate, 1)}`} />
      </Stack>
      <Typography variant="caption" color="text.secondary">
        {`All matches with non-sentinel 4s are included (${sample.matches_used || 0} of ${sample.matches_with_nonzero4 || 0}); per-match/bin q90 still requires >=2 fours in that bin.`}
      </Typography>

      {renderPolarProfile()}

      {renderWarnings(confidence.warning_flags || [])}

      <Box>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          {diagnostics.surface_regime_signal === 'mixed_signal' ? 'Mixed surface signal likely.' : 'Single surface regime likely.'}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {diagnostics.reason}
        </Typography>
      </Box>

      <Typography variant="caption" color="text.secondary">
        Mean boundary radius: {fmt(summary.mean_boundary_r, 2)} | Volatility (rel SD): {fmt(summary.relative_sd, 4)}
      </Typography>

      <Typography variant="caption" color="text.secondary">
        Method: `4s` only, sentinel `(0,0)` filtered, competition-aware outlier clipping, confidence-gated interpretation.
      </Typography>
    </Box>
  );
};

export default VenueBoundaryShape;
