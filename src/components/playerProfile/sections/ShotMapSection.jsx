import React, { useEffect, useMemo, useState } from 'react';
import { Box, CircularProgress, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';
import config from '../../../config';
import { colors as hs, fieldSvg, fonts } from '../../../theme/hindsightDark';
import { DIVERGING } from '../../../theme/chartDefaults';
import { getScoringZoneLabel, SCORING_ZONE_CLOCKWISE_FROM_TOP } from '../../../utils/wagonZones';
import DetailSheet from '../../ui/DetailSheet';
import LineLengthProfile from '../LineLengthProfile';
import { appendCompetitionParams } from '../../../utils/competitionParams';

const PHASES = [['all', 'All'], ['powerplay', 'PP'], ['middle', 'Mid'], ['death', 'Death']];
const KINDS = [['all', 'All'], ['pace bowler', 'Pace'], ['spin bowler', 'Spin']];
const MIN_ZONE_BALLS = 10;

/**
 * Where a batter scores: runs by wagon-wheel zone as eight wedges.
 *
 * Wedge length = share of runs (area-honest: radius ~ sqrt(share)); colour = that zone's strike
 * rate against the batter's own overall rate (blue above, red below, grey under 10 balls). Built
 * from /visualizations/player/{name}/wagon-wheel?aggregate=true, which totals every ball in the
 * window (the per-ball list is capped at a few thousand). Tap a wedge for its numbers.
 */
const WagonZones = ({ rows, playerName }) => {
  const [phase, setPhase] = useState('all');
  const [kind, setKind] = useState('all');
  const [open, setOpen] = useState(null);

  const hand = useMemo(() => {
    const balls = { LHB: 0, RHB: 0 };
    rows.forEach((r) => { if (r.bat_hand in balls) balls[r.bat_hand] += r.balls; });
    return balls.LHB > balls.RHB ? 'LHB' : 'RHB';
  }, [rows]);

  const { zones, totalRuns, totalBalls, overallSr } = useMemo(() => {
    const picked = rows.filter((r) => (phase === 'all' || r.phase === phase) && (kind === 'all' || r.bowl_kind === kind));
    const byZone = {};
    let runs = 0;
    let balls = 0;
    picked.forEach((r) => {
      runs += r.runs;
      balls += r.balls;
      if (!r.wagon_zone) return; // zone 0 = no shot / not recorded (mostly dots)
      const z = byZone[r.wagon_zone] || { balls: 0, runs: 0, wickets: 0, fours: 0, sixes: 0 };
      ['balls', 'runs', 'wickets', 'fours', 'sixes'].forEach((k) => { z[k] += r[k]; });
      byZone[r.wagon_zone] = z;
    });
    return { zones: byZone, totalRuns: runs, totalBalls: balls, overallSr: balls ? (runs * 100) / balls : 0 };
  }, [rows, phase, kind]);

  const zoneRuns = Object.values(zones).reduce((a, z) => a + z.runs, 0);
  const maxShare = Math.max(...Object.values(zones).map((z) => z.runs / (zoneRuns || 1)), 1e-9);
  const cx = 180;
  const cy = 165;
  const R = 108;
  const pt = (deg, r) => {
    const rad = ((deg - 90) * Math.PI) / 180;
    return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
  };

  const top = Object.entries(zones).sort((a, b) => b[1].runs - a[1].runs)[0];

  return (
    <Box sx={{ display: 'grid', gap: 1.5 }}>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        <ToggleButtonGroup size="small" exclusive value={phase} onChange={(_, v) => v && setPhase(v)}>
          {PHASES.map(([v, l]) => <ToggleButton key={v} value={v} sx={{ minHeight: 36, px: 1.25 }}>{l}</ToggleButton>)}
        </ToggleButtonGroup>
        <ToggleButtonGroup size="small" exclusive value={kind} onChange={(_, v) => v && setKind(v)}>
          {KINDS.map(([v, l]) => <ToggleButton key={v} value={v} sx={{ minHeight: 36, px: 1.25 }}>{l}</ToggleButton>)}
        </ToggleButtonGroup>
      </Box>

      {zoneRuns === 0 ? (
        <Typography variant="body2" color="text.secondary">No scoring shots with location data for this filter.</Typography>
      ) : (
        <Box sx={{ maxWidth: 400, width: '100%', mx: 'auto' }}>
          <svg viewBox="0 0 360 330" width="100%" role="img" aria-label={`Runs by zone for ${playerName}`}>
            <circle cx={cx} cy={cy} r={R} fill={fieldSvg.ground} stroke={fieldSvg.boundary} />
            <circle cx={cx} cy={cy} r={R * 0.5} fill="none" stroke={fieldSvg.ring} strokeDasharray="3 4" />
            {SCORING_ZONE_CLOCKWISE_FROM_TOP.map((zoneKey, i) => {
              const z = zones[Number(zoneKey)];
              const label = getScoringZoneLabel(zoneKey, hand);
              const lp = pt(i * 45, R + 26);
              const share = z ? z.runs / zoneRuns : 0;
              const sr = z && z.balls ? (z.runs * 100) / z.balls : 0;
              const small = !z || z.balls < MIN_ZONE_BALLS;
              const r = z ? R * 0.94 * Math.sqrt(share / maxShare) : 0;
              const p0 = pt(i * 45 - 21.3, r);
              const p1 = pt(i * 45 + 21.3, r);
              const fill = small ? 'rgba(255,255,255,0.18)' : sr >= overallSr ? DIVERGING.positive : DIVERGING.negative;
              const select = () => z && setOpen({ label, ...z, share, sr });
              return (
                <g key={zoneKey}>
                  {r > 0 && (
                    <path
                      d={`M${cx},${cy} L${p0.join(',')} A${r},${r} 0 0 1 ${p1.join(',')} Z`}
                      fill={fill}
                      fillOpacity={0.88}
                      stroke={hs.surface1}
                      strokeWidth={2}
                      role="button"
                      tabIndex={0}
                      aria-label={`${label}: ${Math.round(share * 100)}% of runs, strike rate ${Math.round(sr)}`}
                      onClick={select}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(); } }}
                      style={{ cursor: 'pointer' }}
                    />
                  )}
                  <text x={lp[0]} y={lp[1] - 2} textAnchor="middle" fontSize={11} fill={fieldSvg.label} fontFamily={fonts.body} pointerEvents="none">{label}</text>
                  <text x={lp[0]} y={lp[1] + 12} textAnchor="middle" fontSize={12} fontWeight={600} fill={hs.textHi} fontFamily={fonts.mono} pointerEvents="none">
                    {z ? `${Math.round(share * 100)}%` : '–'}
                  </text>
                </g>
              );
            })}
            <rect x={cx - 3} y={cy - 9} width={6} height={18} rx={2} fill={fieldSvg.batter} />
          </svg>
        </Box>
      )}

      <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', fontSize: 12, color: hs.textLo }}>
        <span><Box component="span" sx={{ display: 'inline-block', width: 10, height: 10, borderRadius: '3px', bgcolor: DIVERGING.positive, mr: 0.75 }} />SR above his {Math.round(overallSr)}</span>
        <span><Box component="span" sx={{ display: 'inline-block', width: 10, height: 10, borderRadius: '3px', bgcolor: DIVERGING.negative, mr: 0.75 }} />SR below</span>
        <span>Wedge length = share of runs · tap a zone</span>
      </Box>
      {top && zoneRuns > 0 && (
        <Typography variant="body2" color="text.secondary">
          {getScoringZoneLabel(top[0], hand)} gives him {Math.round((top[1].runs * 100) / zoneRuns)}% of his runs.
          {' '}{totalRuns} runs off {totalBalls} balls in this view ({hand === 'LHB' ? 'left' : 'right'}-handed).
        </Typography>
      )}

      <DetailSheet
        open={Boolean(open)}
        onClose={() => setOpen(null)}
        title={open?.label || ''}
        subtitle={`${playerName} · ${PHASES.find(([v]) => v === phase)[1]} · ${KINDS.find(([v]) => v === kind)[1]}`}
        rows={open ? [
          { label: 'Runs', value: open.runs, hint: `${(open.share * 100).toFixed(1)}% of his runs` },
          { label: 'Balls', value: open.balls },
          { label: 'Strike rate', value: open.sr.toFixed(1), hint: `${overallSr.toFixed(1)} overall` },
          { label: 'Dismissals', value: open.wickets },
          { label: 'Fours', value: open.fours },
          { label: 'Sixes', value: open.sixes },
        ] : []}
      />
    </Box>
  );
};

const buildParams = ({ dateRange, selectedVenue }) => {
  const params = new URLSearchParams({ aggregate: 'true' });
  if (dateRange?.start) params.set('start_date', dateRange.start);
  if (dateRange?.end) params.set('end_date', dateRange.end);
  if (selectedVenue && selectedVenue !== 'All Venues') params.set('venue', selectedVenue);
  return params;
};

/** "Shot map" for batters: where he scores (zones) and what he's bowled (line & length). */
const ShotMapSection = ({ playerName, dateRange, selectedVenue, competitionFilters, isMobile }) => {
  const [tab, setTab] = useState('zones');
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(false);
  const params = useMemo(
    () => buildParams({ dateRange, selectedVenue }),
    [dateRange, selectedVenue],
  );

  useEffect(() => {
    if (!playerName) return undefined;
    let cancelled = false;
    setRows(null);
    setError(false);
    // Competitions go through appendCompetitionParams: this endpoint, like the query builder, reads
    // "no leagues + internationals" as internationals only.
    appendCompetitionParams(new URLSearchParams(params), competitionFilters)
      .then((full) => fetch(`${config.API_URL}/visualizations/player/${encodeURIComponent(playerName)}/wagon-wheel?${full}`))
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((d) => { if (!cancelled) setRows(d.zones || []); })
      .catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [playerName, params, competitionFilters]);

  return (
    <Box sx={{ display: 'grid', gap: 2 }}>
      <ToggleButtonGroup exclusive fullWidth size="small" value={tab} onChange={(_, v) => v && setTab(v)}>
        <ToggleButton value="zones" sx={{ minHeight: 36 }}>Where he scores</ToggleButton>
        <ToggleButton value="pitch" sx={{ minHeight: 36 }}>Line &amp; length</ToggleButton>
      </ToggleButtonGroup>
      {tab === 'zones' && (
        error ? <Typography variant="body2" color="text.secondary">Couldn&apos;t load the shot map.</Typography>
          : rows === null ? <Box sx={{ py: 3, display: 'flex', justifyContent: 'center' }}><CircularProgress size={22} /></Box>
            : rows.length === 0 ? <Typography variant="body2" color="text.secondary">No ball-by-ball location data for this window (it covers 2015 onwards).</Typography>
              : <WagonZones rows={rows} playerName={playerName} />
      )}
      {tab === 'pitch' && (
        <LineLengthProfile
          playerName={playerName}
          mode="batting"
          dateRange={dateRange}
          selectedVenue={selectedVenue}
          competitionFilters={competitionFilters}
          isMobile={isMobile}
        />
      )}
    </Box>
  );
};

export default ShotMapSection;
