import React, { useEffect, useState } from 'react';
import { Box, IconButton, Menu, MenuItem } from '@mui/material';
import IosShareRoundedIcon from '@mui/icons-material/IosShareRounded';
import { colors, fonts } from '../../theme/hindsightDark';
import { POST_VISUALS } from '../story/postVisuals';
import GraphicMaker from '../GraphicMaker';
import QueryResults from '../QueryResults';
import { ScoringWheel } from '../playerProfile/cards/RoleCards';
import { fmtValue, MEASURES, metricOf } from './answerShape';

// The answer (QUERY_BUILDER_PLAN.md Q2): one sentence that reads the result, the picture that fits its shape, then
// the rows. "All columns" opens the full table; the share button copies the link or makes a graphic (the old Make a
// Graphic page's maker, folded in here).

const Sentence = ({ parts }) => (
  <Box component="p" sx={{ m: 0, fontFamily: fonts.display, fontWeight: 600, fontSize: 18.5, lineHeight: 1.3, textWrap: 'pretty', flex: 1 }}>
    {parts.map(([t, strong], i) => (strong
      ? <Box key={i} component="span" sx={{ color: colors.accent, fontWeight: 700 }}>{t}</Box>
      : <React.Fragment key={i}>{t}</React.Fragment>))}
  </Box>
);

const Rows = ({ rows }) => (
  <Box component="ul" sx={{ listStyle: 'none', m: 0, p: 0 }}>
    {rows.map((r) => (
      <Box component="li" key={r.label}
        sx={{ display: 'grid', gridTemplateColumns: 'auto minmax(0, 1fr) 58px', columnGap: 1, alignItems: 'baseline', py: 0.9,
          borderBottom: `1px solid ${colors.border}`, whiteSpace: 'nowrap' }}>
        <Box component="span" sx={{ fontWeight: 600, fontSize: 14 }}>{r.label}</Box>
        <Box component="span" sx={{ color: colors.textLo, fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.detail}</Box>
        <Box component="span" sx={{ fontFamily: fonts.mono, fontSize: 14, textAlign: 'right' }}>{r.value}</Box>
      </Box>
    ))}
  </Box>
);

const Ranked = ({ rows, lowerBetter }) => {
  const nums = rows.map((r) => r.num).filter((n) => n != null);
  const max = Math.max(...nums, 1);
  return (
    <Box component="ol" sx={{ listStyle: 'none', m: 0, p: 0 }}>
      {rows.map((r) => (
        <Box component="li" key={r.label}
          sx={{ display: 'grid', gridTemplateColumns: '18px minmax(0, 1fr) 64px 50px', columnGap: 1, alignItems: 'center', py: 0.8,
            borderBottom: `1px solid ${colors.border}` }}>
          <Box component="span" sx={{ fontFamily: fonts.mono, fontSize: 12, color: colors.textLo }}>{r.rank}</Box>
          <Box sx={{ minWidth: 0 }}>
            <Box sx={{ fontWeight: 600, fontSize: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.label}</Box>
            <Box sx={{ color: colors.textLo, fontSize: 11.5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.detail}</Box>
          </Box>
          <Box sx={{ height: 10, bgcolor: 'rgba(255,255,255,.05)', borderRadius: '4px', overflow: 'hidden' }}>
            <Box sx={{ height: '100%', width: `${Math.max(4, (100 * (r.num || 0)) / max)}%`, borderRadius: '4px', bgcolor: r.rank === 1 ? colors.accent : '#5b6b85' }} />
          </Box>
          <Box sx={{ fontFamily: fonts.mono, fontSize: 14, textAlign: 'right' }}>{r.value}</Box>
        </Box>
      ))}
      {lowerBetter && <Box component="li" sx={{ display: 'none' }} />}
    </Box>
  );
};

const Tiles = ({ r, measure }) => {
  const cells = [
    ['Runs (balls)', `${r.runs} (${r.balls})`], [measure === 'economy' ? 'Wickets' : 'Outs', r.wickets],
    [MEASURES[measure].label, fmtValue(metricOf(r, measure), MEASURES[measure].format)],
    ['Dots', r.dot_percentage != null ? `${Math.round(r.dot_percentage)}%` : '–'],
    ['Boundaries', r.boundary_percentage != null ? `${Math.round(r.boundary_percentage)}%` : '–'],
    ['False shots', r.control_percentage != null ? `${Math.round(100 - r.control_percentage)}%` : '–'],
  ];
  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 1 }}>
      {cells.map(([l, v]) => (
        <Box key={l} sx={{ border: `1px solid ${colors.borderStrong}`, borderRadius: '12px', px: 1.25, py: 1, minWidth: 0 }}>
          <Box sx={{ fontFamily: fonts.mono, fontSize: 9.5, letterSpacing: '0.08em', textTransform: 'uppercase', color: colors.textLo, whiteSpace: 'nowrap' }}>{l}</Box>
          <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 20 }}>{v}</Box>
        </Box>
      ))}
    </Box>
  );
};

const AnswerCard = ({ answer, results, filters, groupBy, apiQueryString, isMobile, autoGraphic = false }) => {
  const [allCols, setAllCols] = useState(false);
  const [menu, setMenu] = useState(null);
  const [graphic, setGraphic] = useState(false);
  // From the Make a Graphic page (/query?graphic=1): open the graphic maker once the grouped result is in.
  useEffect(() => { if (autoGraphic && groupBy.length) setGraphic(true); }, [autoGraphic, groupBy.length]);
  const [copied, setCopied] = useState(false);
  const Visual = answer.chart ? POST_VISUALS[answer.chart.visual] : null;
  const lowerBetter = MEASURES[answer.measure]?.better === 'lower';
  const copy = () => {
    try { navigator.clipboard.writeText(window.location.href); setCopied(true); setTimeout(() => setCopied(false), 1800); } catch { /* no clipboard */ }
    setMenu(null);
  };
  return (
    <Box component="section" aria-label="Answer"
      sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.borderStrong}`, borderRadius: '18px', p: 1.75, display: 'flex', flexDirection: 'column', gap: 1.25 }}>
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
        <Sentence parts={answer.sentence} />
        {answer.type !== 'empty' && (
          <IconButton aria-label="Share: link or graphic" onClick={(e) => setMenu(e.currentTarget)} sx={{ color: colors.textMed, mt: -0.75, mr: -1 }}>
            <IosShareRoundedIcon fontSize="small" />
          </IconButton>
        )}
        <Menu anchorEl={menu} open={Boolean(menu)} onClose={() => setMenu(null)}>
          <MenuItem onClick={copy}>Copy link</MenuItem>
          {groupBy.length > 0 && <MenuItem onClick={() => { setMenu(null); setGraphic(true); }}>Make a graphic</MenuItem>}
        </Menu>
      </Box>
      {copied && <Box sx={{ color: colors.accent, fontSize: 12.5 }}>Link copied</Box>}
      {Visual && (
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: answer.type === 'pitch' ? 260 : 190 }}>
          <Visual payload={answer.chart.payload} />
        </Box>
      )}
      {answer.type === 'zones' && <ScoringWheel zones={answer.zones} hand={answer.hand} strikeRate={answer.overallSr} />}
      {answer.type === 'single' && answer.tiles && <Tiles r={answer.tiles} measure={answer.measure} />}
      {answer.type === 'ranked' && <Ranked rows={answer.rows} lowerBetter={lowerBetter} />}
      {answer.type !== 'ranked' && answer.rows?.length > 0 && <Rows rows={answer.rows} />}
      {answer.type !== 'empty' && (
        <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, color: colors.textLo, fontSize: 11.5 }}>
          <Box component="span" sx={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {answer.note || `${MEASURES[answer.measure].label}${lowerBetter ? ' · lower is better' : ''}`}
          </Box>
          {groupBy.length > 0 && (
            <Box component="button" type="button" onClick={() => setAllCols((v) => !v)}
              sx={{ all: 'unset', cursor: 'pointer', color: colors.accent, whiteSpace: 'nowrap' }}>
              {allCols ? 'Hide columns' : 'All columns ›'}
            </Box>
          )}
        </Box>
      )}
      {allCols && (
        <Box sx={{ mx: -1 }}>
          <QueryResults results={results} groupBy={groupBy} filters={filters} isMobile={isMobile} recommendedColumns={[]} />
        </Box>
      )}
      {graphic && (
        <GraphicMaker open={graphic} onClose={() => setGraphic(false)} apiQueryString={apiQueryString}
          rows={(results?.data || []).filter((r) => !r.is_summary)} groupBy={groupBy} defaultMetric={answer.measure} minCoverage={0} />
      )}
    </Box>
  );
};

export default AnswerCard;
