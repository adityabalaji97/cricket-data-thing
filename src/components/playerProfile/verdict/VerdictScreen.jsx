import React, { useEffect, useRef, useState } from 'react';
import { Box, IconButton, Skeleton, Tooltip } from '@mui/material';
import TuneRoundedIcon from '@mui/icons-material/TuneRounded';
import config from '../../../config';
import { colors, fonts } from '../../../theme/hindsightDark';
import ShareButton from '../../ui/ShareButton';
import PeerStrip, { StripAxisCue } from './PeerStrip';
import { SeasonRateChart, SeasonWinsChart } from './SeasonChart';
import FormChips from './FormChips';
import { ROLE_COLOURS, ROLE_NAMES, signed } from './verdictFormat';

// The player profile's first screen (VERDICT_SCREEN_PLAN.md V4): one screenshot that answers "is the hype fair?",
// from a single cached call (GET /player/{name}/summary). Its window (format, period or custom dates, strong sides or
// every match) is the page's (PROFILE_SIMPLIFY_PLAN.md P1): the pills here and the filters icon set it for everything
// below too. The verdict is one stat per row; no link or credit here (the page foot carries the credit).

const FORMATS = ['T20', 'ODI'];
const PHASES = ['powerplay', 'middle', 'death'];
const PHASE_LABELS = {
  T20: { powerplay: 'Powerplay', middle: 'Middle overs', death: 'Death' },
  ODI: { powerplay: 'Overs 1–10', middle: 'Overs 11–40', death: 'Overs 41–50' },
};
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const Eyebrow = ({ children, right }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 1 }}>
    <Box component="span" sx={{ fontFamily: fonts.mono, fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: colors.textLo }}>
      {children}
    </Box>
    {right}
  </Box>
);

const Legend = ({ roles }) => (
  <Box sx={{ display: 'flex', gap: 1.25, fontSize: 11.5, color: colors.textLo }}>
    {roles.map((r) => (
      <span key={r}>
        <Box component="i" sx={{ display: 'inline-block', width: 8, height: 8, borderRadius: '2px', mr: 0.5, bgcolor: ROLE_COLOURS[r] }} />
        {ROLE_NAMES[r]}
      </span>
    ))}
  </Box>
);

const identityLine = (s) => {
  const id = s.identity || {};
  const parts = [id.side];
  if (id.bowling_style && s.roles.bowl && (s.primary_role === 'bowl' || s.allrounder)) parts.push(id.bowling_style);
  if (s.roles.bat && id.batting_position) {
    const hand = id.bat_hand === 'LHB' ? 'left-hand ' : '';
    // #1 and #2 are both openers (the scorecard lists the non-striker second).
    const opener = id.batting_position <= 2;
    parts.push(s.primary_role === 'bat' && !s.allrounder
      ? (opener ? `${hand}opener` : `${hand}bat, usually #${id.batting_position}`)
      : (opener ? 'opens' : `bats #${id.batting_position}`));
  }
  return parts.filter(Boolean).join(' · ');
};

const scopeChip = (s) => {
  const month = (iso) => { const d = new Date(`${iso}T00:00:00`); return `${MONTHS[d.getMonth()]} ${d.getFullYear()}`; };
  // A window that ends before this month (custom dates) names its end too.
  const end = s.window.end_date ? new Date(`${s.window.end_date}T00:00:00`) : null;
  const now = new Date();
  const ended = end && (end.getFullYear() < now.getFullYear() || (end.getFullYear() === now.getFullYear() && end.getMonth() < now.getMonth()));
  const span = ended ? `${month(s.window.start_date)} to ${month(s.window.end_date)}` : `Since ${month(s.window.start_date)}`;
  return { short: `${span} · ${s.scope === 'strong' ? 'strong sides' : 'every match'}`, long: `${span}. ${s.scope_label}.` };
};

const PhaseCells = ({ block, role, fmt }) => {
  const rows = Object.fromEntries((block.phases || []).map((r) => [r.phase, r]));
  // Two short lines under each number, never one wrapped line (no sentence wraps at phone width: user, 3 Nov 2026).
  const cells = PHASES.filter((p) => rows[p]).map((p) => {
    const r = rows[p];
    if (role === 'bowl') {
      return { n: PHASE_LABELS[fmt][p], v: r.economy?.toFixed(2), s: [`${Math.round(r.dot_percentage)}% dots`, `${r.wickets} wkts`] };
    }
    const second = r.balls < 60 ? 'small sample'
      : fmt === 'T20' && r.raa_per_100 !== null ? `${signed(r.raa_per_100, 0)} v par /100` : null;
    return { n: PHASE_LABELS[fmt][p], v: Math.round(r.strike_rate), s: [`${r.balls} balls`, second].filter(Boolean) };
  });
  if (!cells.length) return null;
  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: `repeat(${cells.length}, minmax(0, 1fr))`, gap: 1 }}>
      {cells.map((c) => (
        <Box key={c.n} sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '12px', px: 1.25, py: 1, display: 'flex', flexDirection: 'column' }}>
          <Box component="span" sx={{ fontFamily: fonts.mono, fontSize: 9.5, letterSpacing: '0.08em', textTransform: 'uppercase', color: colors.textLo }}>{c.n}</Box>
          <Box component="span" sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 20, fontVariantNumeric: 'tabular-nums' }}>{c.v}</Box>
          {c.s.map((line) => (
            <Box key={line} component="span" sx={{ fontSize: 11, color: colors.textLo, whiteSpace: 'nowrap', lineHeight: 1.35 }}>{line}</Box>
          ))}
        </Box>
      ))}
    </Box>
  );
};

const StripBlock = ({ role, block, keys, cue }) => {
  const p = block.peers;
  const metrics = p.metrics.filter((m) => !keys || keys.includes(m.key));
  if (!metrics.length) return null;
  const who = role === 'bowl' ? 'bowlers' : 'batters';
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {/* Who the player is ranked against on the left, the qualifying floor on the right: one line on a phone. */}
      <Eyebrow right={(
        <Tooltip title="Peers: players who cleared each season's floor (40% of that season's regulars' median balls, at least 120) in two or more seasons" enterTouchDelay={0}>
          <Box component="span" sx={{ fontFamily: fonts.mono, fontSize: 9.5, color: colors.textFaint, whiteSpace: 'nowrap' }}>
            {(p.floor_label || `${p.min_balls}+ balls`).replace(' balls in ', ' balls · ')}
          </Box>
        </Tooltip>
      )}>
        {`${ROLE_NAMES[role]} · v ${p.pool} ${who}${p.qualified ? '' : ' · below the floor'}`}
      </Eyebrow>
      {cue && <StripAxisCue />}
      {metrics.map((m) => <PeerStrip key={m.key} metric={m} />)}
    </Box>
  );
};

export const windowQuery = (w) => {
  const q = new URLSearchParams({ format: w.fmt, scope: w.scope || 'strong', period: w.period === 'career' ? 'career' : 'recent' });
  if (w.period === 'custom') {
    if (w.start) q.set('start_date', w.start);
    if (w.end) q.set('end_date', w.end);
  }
  return q.toString();
};

const useSummary = (player, win) => {
  const query = windowQuery(win);
  const [state, setState] = useState({ status: 'loading', data: null });
  useEffect(() => {
    if (!player) return undefined;
    let cancelled = false;
    setState({ status: 'loading', data: null });
    fetch(`${config.API_URL}/player/${encodeURIComponent(player)}/summary?${query}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => { if (!cancelled) setState({ status: 'ready', data }); })
      .catch((e) => {
        if (!cancelled) setState({ status: e === 404 ? 'empty' : e === 503 ? 'busy' : 'error', data: null });
      });
    return () => { cancelled = true; };
  }, [player, query]);
  return state;
};

const PERIOD_TABS = [['recent', 'Recent'], ['career', 'Career']];

const VerdictScreen = ({ player, win, onWindow, onFilters, onSummary }) => {
  const { fmt, period } = win;
  const setFmt = (f) => onWindow({ fmt: f });
  const setPeriod = (p) => onWindow({ period: p });
  // Recent (the last few seasons) by default; a player with nothing recent (retired, or out since 2024) opens on
  // Career, since 2015 (VERDICT_SCREEN_PLAN.md V10).
  const autoCareer = useRef(false);
  const { status, data: s } = useSummary(player, win);

  useEffect(() => {
    if (status === 'empty' && fmt === 'T20' && period === 'recent' && !autoCareer.current) {
      autoCareer.current = true;
      setPeriod('career');
      return;
    }
    if (onSummary) onSummary(status === 'ready' ? s : null, status);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, s, fmt, period]);

  const header = (name, meta) => (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 1.5 }}>
      <Box sx={{ minWidth: 0 }}>
        <Box component="h1" sx={{ m: 0, fontFamily: fonts.display, fontWeight: 700, fontSize: 27, lineHeight: 1.05 }}>{name}</Box>
        {meta && <Box sx={{ color: colors.textLo, fontSize: 13.5, mt: 0.5 }}>{meta}</Box>}
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'center', flexShrink: 0, mt: '-2px' }}>
        <Tooltip title="Filters">
          <IconButton aria-label="Filters: format, period, competitions" onClick={onFilters} sx={{ color: colors.textHi }}>
            <TuneRoundedIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <ShareButton variant="icon" kind="player" title={`${name} on Hindsight`} sx={{ color: colors.textHi }} />
      </Box>
    </Box>
  );

  const formatSwitch = (chip) => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, flexWrap: 'wrap' }}>
      <Box role="tablist" aria-label="Format" sx={{ display: 'inline-flex', border: `1px solid ${colors.borderStrong}`, borderRadius: '999px', p: '2px' }}>
        {FORMATS.map((f) => (
          <Box key={f} component="button" role="tab" aria-selected={f === fmt} onClick={() => setFmt(f)}
            sx={{
              all: 'unset', cursor: 'pointer', fontFamily: fonts.display, fontWeight: 600, fontSize: 13, letterSpacing: '0.04em',
              px: 1.5, py: '3px', borderRadius: '999px',
              bgcolor: f === fmt ? colors.accent : 'transparent', color: f === fmt ? colors.bg : colors.textLo,
              '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 },
            }}>
            {f}
          </Box>
        ))}
        <Tooltip title="Tests are coming: the data isn't loaded yet" enterTouchDelay={0}>
          <Box component="span" sx={{ fontFamily: fonts.display, fontWeight: 600, fontSize: 13, px: 1.5, py: '3px', color: colors.textGhost }}>Test</Box>
        </Tooltip>
      </Box>
      <Box role="tablist" aria-label="Period" sx={{ display: 'inline-flex', border: `1px solid ${colors.borderStrong}`, borderRadius: '999px', p: '2px' }}>
        {PERIOD_TABS.map(([key, name]) => (
          <Box key={key} component="button" role="tab" aria-selected={key === period} onClick={() => setPeriod(key)}
            sx={{
              all: 'unset', cursor: 'pointer', fontFamily: fonts.display, fontWeight: 600, fontSize: 13, letterSpacing: '0.04em',
              px: 1.5, py: '3px', borderRadius: '999px',
              bgcolor: key === period ? colors.textHi : 'transparent', color: key === period ? colors.bg : colors.textLo,
              '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 },
            }}>
            {name}
          </Box>
        ))}
      </Box>
      {chip && (
        <Tooltip title={chip.long} enterTouchDelay={0}>
          <Box component="span" sx={{ fontSize: 12, color: colors.textLo, whiteSpace: 'nowrap' }}>{chip.short}</Box>
        </Tooltip>
      )}
    </Box>
  );

  const wrap = (children) => (
    <Box sx={{ px: 2, pt: 1.5, pb: 2, display: 'flex', flexDirection: 'column', gap: 1.5, color: colors.textHi, maxWidth: 520 }}>
      {children}
    </Box>
  );

  if (status === 'loading') {
    return wrap(
      <>
        {header(player)}
        {formatSwitch(null)}
        <Skeleton variant="text" sx={{ fontSize: 21, bgcolor: colors.surface2 }} />
        <Skeleton variant="rounded" height={120} sx={{ bgcolor: colors.surface2 }} />
        <Skeleton variant="rounded" height={170} sx={{ bgcolor: colors.surface2 }} />
      </>,
    );
  }
  if (status !== 'ready') {
    const when = period === 'career' ? 'since 2015' : `in the last ${fmt === 'ODI' ? 'three' : 'two'} years`;
    const message = status === 'empty' ? `No ${fmt}s for ${player} ${when} against strong sides.`
      : status === 'busy' ? (period === 'career' ? 'Career numbers are still being built. Try again in a minute.'
        : 'Busy building another player. Try again in a few seconds.')
        : "This couldn't load just now. Try again shortly.";
    return wrap(
      <>
        {header(player)}
        {formatSwitch(null)}
        <Box sx={{ color: colors.textLo, fontSize: 14 }}>{message}</Box>
      </>,
    );
  }

  const roles = s.roles;
  const order = [s.primary_role, s.primary_role === 'bowl' ? 'bat' : 'bowl'].filter((r) => roles[r]);
  const shown = s.allrounder ? order : order.slice(0, 1);
  const main = shown[0];
  const mainStrip = (key) => roles[main].peers.metrics.find((m) => m.key === key);
  const rateKey = main === 'bowl' ? 'economy' : 'strike_rate';
  const chip = scopeChip(s);

  return wrap(
    <>
      {header(s.player, identityLine(s))}
      {formatSwitch(chip)}
      {s.verdict_rows?.length > 0 ? (
        <Box component="ul" aria-label="Verdict" sx={{ listStyle: 'none', m: 0, p: 0 }}>
          {s.verdict_rows.map((r) => (
            <Box component="li" key={`${r.rank}-${r.what}`}
              sx={{ display: 'grid', gridTemplateColumns: '92px minmax(0, 1fr)', alignItems: 'baseline', columnGap: 1.25, py: 0.6,
                borderBottom: `1px solid ${colors.border}`, whiteSpace: 'nowrap' }}>
              <Box component="span" sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: r.lead ? 22 : 17, color: r.lead ? colors.textHi : colors.accent }}>{r.rank}</Box>
              <Box component="span" sx={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis',
                ...(r.lead ? { fontFamily: fonts.display, fontWeight: 700, fontSize: 20, color: colors.textHi } : { fontWeight: 500, fontSize: 15, color: colors.textMed }) }}>
                {r.what}
              </Box>
            </Box>
          ))}
        </Box>
      ) : s.verdict && (
        <Box component="p" sx={{ m: 0, fontFamily: fonts.display, fontWeight: 600, fontSize: 21, lineHeight: 1.2, textWrap: 'balance' }}>
          {s.verdict}
        </Box>
      )}

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {s.has_wins_added ? (
          <>
            <Eyebrow right={shown.length > 1 ? <Legend roles={shown} /> : null}>Wins added by season</Eyebrow>
            <SeasonWinsChart roles={roles} order={shown} />
          </>
        ) : mainStrip(rateKey) && (
          <>
            <Eyebrow>{main === 'bowl' ? 'Economy' : 'Strike rate'} by year</Eyebrow>
            <SeasonRateChart rows={roles[main].seasons} metricKey={rateKey} label={main === 'bowl' ? 'Economy' : 'Strike rate'}
              median={mainStrip(rateKey).median} />
          </>
        )}
      </Box>

      {shown.map((role, i) => (
        <StripBlock key={role} role={role} block={roles[role]} cue={i === 0}
          keys={s.allrounder && i > 0 ? roles[role].peers.metrics.filter((m) => m.key !== 'wpa').map((m) => m.key) : null} />
      ))}

      {/* Every role shown gets its phases: an all-rounder's batting by phase is nowhere else on the page (Livingstone,
          3 Nov 2026), the role cards carry phases for bowling only. */}
      {shown.map((role) => (
        <Box key={`ph-${role}`} sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Eyebrow>{role === 'bowl' ? 'Economy' : 'Strike rate'} by phase</Eyebrow>
          <PhaseCells block={roles[role]} role={role} fmt={fmt} />
        </Box>
      ))}

      {s.form?.length > 0 && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Eyebrow>{`Last ${s.form.length} · ${s.has_wins_added ? 'coloured by runs above par' : 'no par in ODIs yet'}`}</Eyebrow>
          <FormChips games={s.form} />
        </Box>
      )}

    </>,
  );
};

export default VerdictScreen;
