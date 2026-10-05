import React, { useMemo, useState } from 'react';
import axios from 'axios';
import {
  Alert, Box, Button, ButtonBase, CircularProgress, Dialog, IconButton, MenuItem, TextField, Typography,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import config from '../config';
import useIsMobile from '../hooks/useIsMobile';
import { track } from '../utils/analytics';
import GraphicOptions from './GraphicOptions';
import { qbButtonSx, qbColors, qbFonts } from './queryBuilderTheme';


const SKIP = new Set(['percent_balls', 'innings_count', 'metric_balls']);
const label = (key) => key.replace(/_/g, ' ').replace(/\bpercentage\b/, '%');
const SHOWN = 8;

// Same order the server ranks by (content_ideas._ascending): lower is better for economy, and for
// a bowler's average / strike rate.
const ascending = (metric, groupBy) => metric === 'economy'
  || (groupBy.some((g) => g === 'bowler' || g === 'bowling_team') && ['average', 'strike_rate'].includes(metric));
const fmt = (v) => (Number.isInteger(v) ? String(v) : Number(v).toFixed(Math.abs(v) >= 100 ? 0 : 1));

/**
 * "Make a graphic" from the result on screen: the same chart forms and phone-sized share images
 * as the admin idea packs, from the query the viewer already ran (no LLM). The server re-runs the
 * query from its query string, so the numbers in a graphic are always real.
 */
const GraphicMaker = ({ open, onClose, apiQueryString, rows, groupBy, defaultMetric, scatter, minCoverage }) => {
  const { isMobile } = useIsMobile();
  const metrics = useMemo(() => {
    const first = rows?.[0] || {};
    return Object.keys(first).filter((k) => !groupBy.includes(k) && !SKIP.has(k) && !k.endsWith('_tagged') && typeof first[k] === 'number');
  }, [rows, groupBy]);
  const labelKey = groupBy.find((g) => !['match_id', 'innings'].includes(g)) || groupBy[0];
  const [metric, setMetric] = useState(metrics.includes(defaultMetric) ? defaultMetric : (metrics.includes('runs') ? 'runs' : metrics[0] || ''));
  const [highlight, setHighlight] = useState(null);
  const [showAll, setShowAll] = useState(false);
  // One row per name, ranked by the chosen metric: tap one to highlight it in the graphic.
  const ranked = useMemo(() => {
    const seen = new Set();
    const list = (rows || []).filter((r) => {
      const name = r[labelKey];
      if (name === null || name === undefined || typeof r[metric] !== 'number' || seen.has(String(name))) return false;
      seen.add(String(name));
      return true;
    }).map((r) => ({ name: String(r[labelKey]), value: r[metric] }));
    const asc = ascending(metric, groupBy);
    return list.sort((a, b) => (asc ? a.value - b.value : b.value - a.value));
  }, [rows, labelKey, metric, groupBy]);
  const shown = showAll ? ranked : ranked.slice(0, SHOWN);
  const pinned = highlight && !shown.some((r) => r.name === highlight) ? ranked.find((r) => r.name === highlight) : null;
  const [state, setState] = useState({ loading: false, error: null, options: [], pickedBy: null });

  const make = async () => {
    setState({ loading: true, error: null, options: [], pickedBy: null });
    try {
      const { data } = await axios.post(`${config.API_URL}/snapshots/graphic`, {
        query_string: apiQueryString, metric, highlight: highlight || null,
        // The table's coverage floor (services/coverage.py): the graphic ranks among the same rows.
        ...(minCoverage !== undefined ? { min_coverage: minCoverage } : {}),
        // Two metrics in the question (parser's scatter): offer a scatter of them.
        chart: scatter && scatter.x_axis && scatter.y_axis ? { type: 'scatter', x_axis: scatter.x_axis, y_axis: scatter.y_axis } : null,
      });
      setState({ loading: false, error: null, options: data.options || [], pickedBy: data.picked_by, warnings: data.warnings || [] });
      track('graphic_made', { metric, forms: (data.options || []).map((o) => o.form).join(','), highlight: Boolean(highlight) });
    } catch (err) {
      setState({ loading: false, error: err.response?.data?.detail || 'Could not make a graphic for this result.', options: [], pickedBy: null });
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullScreen={isMobile} maxWidth="sm" fullWidth
      PaperProps={{ sx: { bgcolor: qbColors.surface1 || '#101319', backgroundImage: 'none', color: qbColors.textHi } }}>
      <Box sx={{ p: 2, pb: 'calc(16px + env(safe-area-inset-bottom, 0px))', display: 'grid', gap: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Typography sx={{ fontFamily: qbFonts.display, fontWeight: 700, fontSize: 20, flex: 1 }}>Make a graphic</Typography>
          <IconButton onClick={onClose} aria-label="Close"><CloseIcon /></IconButton>
        </Box>
        <Typography sx={{ fontSize: 13, color: qbColors.textLo }}>
          A phone-sized image of this result, titled from the numbers, ready to share. Pick what to rank by and,
          optionally, who to highlight.
        </Typography>
        <TextField select size="small" label="Rank by" value={metric} onChange={(e) => setMetric(e.target.value)}>
          {metrics.map((m) => <MenuItem key={m} value={m}>{label(m)}</MenuItem>)}
        </TextField>
        {ranked.length > 1 && (
          <Box>
            <Typography sx={{ fontSize: 12, color: qbColors.textLo, mb: 0.5 }}>
              {highlight ? `Highlighting ${highlight} · tap again to clear` : `Tap a ${label(labelKey)} to highlight it (optional)`}
            </Typography>
            <Box role="listbox" aria-label={`Highlight a ${label(labelKey)}`}
              sx={{ border: `1px solid ${qbColors.border}`, borderRadius: 1 }}>
              {[...shown, ...(pinned ? [pinned] : [])].map((r) => {
                const on = r.name === highlight;
                return (
                  <ButtonBase key={r.name} role="option" aria-selected={on}
                    onClick={() => setHighlight(on ? null : r.name)}
                    sx={{
                      width: '100%', minHeight: 40, px: 1.5, display: 'flex', gap: 1, justifyContent: 'flex-start',
                      borderTop: `1px solid ${qbColors.border}`, '&:first-of-type': { borderTop: 'none' },
                      bgcolor: on ? qbColors.accentSoft : 'transparent',
                    }}>
                    <Typography sx={{ width: 24, fontSize: 12, color: qbColors.textLo, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                      {ranked.indexOf(r) + 1}
                    </Typography>
                    <Typography sx={{ flex: 1, fontSize: 14, textAlign: 'left', fontWeight: on ? 700 : 400,
                      color: on ? qbColors.accent : qbColors.textHi, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {r.name}
                    </Typography>
                    <Typography sx={{ fontSize: 13, color: qbColors.textLo, fontVariantNumeric: 'tabular-nums' }}>{fmt(r.value)}</Typography>
                  </ButtonBase>
                );
              })}
            </Box>
            {ranked.length > SHOWN && (
              <Button size="small" onClick={() => setShowAll((v) => !v)} sx={{ mt: 0.5, minHeight: 32 }}>
                {showAll ? 'Show top 8' : `Show all ${ranked.length}`}
              </Button>
            )}
          </Box>
        )}
        <Button variant="contained" onClick={make} disabled={!metric || state.loading} sx={{ ...qbButtonSx, minHeight: 44 }}>
          {state.loading ? <CircularProgress size={20} color="inherit" /> : 'Make graphic'}
        </Button>
        {state.error && <Alert severity="warning">{state.error}</Alert>}
        {(state.warnings || []).length > 0 && (
          // Coverage: a tag filter counts only tagged balls, so a short-tagged leader may be short.
          <Alert severity="warning">
            Check before sharing: {state.warnings.join(' ')}
          </Alert>
        )}

        {state.options.length > 0 && <GraphicOptions options={state.options} source="query" />}
      </Box>
    </Dialog>
  );
};

export default GraphicMaker;
