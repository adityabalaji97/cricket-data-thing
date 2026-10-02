import React, { useMemo, useState } from 'react';
import axios from 'axios';
import {
  Alert, Autocomplete, Box, Button, CircularProgress, Dialog, IconButton, MenuItem, TextField, Typography,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import config from '../config';
import { shareImage, siteOrigin } from './ui/ChartExportButton';
import useIsMobile from '../hooks/useIsMobile';
import { track } from '../utils/analytics';
import { qbButtonSx, qbColors, qbFonts } from './queryBuilderTheme';

const FORM_NAMES = {
  bars: 'Ranked bars', line: 'Trend line', scatter: 'Scatter', stat: 'Big number',
  diverging: 'Above / below', dumbbell: 'Dumbbell', stacked: 'Stacked', field: 'Field map',
};

const SKIP = new Set(['percent_balls', 'innings_count', 'metric_balls']);
const label = (key) => key.replace(/_/g, ' ').replace(/\bpercentage\b/, '%');

/**
 * "Make a graphic" from the result on screen: the same chart forms and phone-sized share images
 * as the admin idea packs, from the query the viewer already ran (no LLM). The server re-runs the
 * query from its query string, so the numbers in a graphic are always real.
 */
const GraphicMaker = ({ open, onClose, apiQueryString, rows, groupBy, defaultMetric }) => {
  const { isMobile } = useIsMobile();
  const metrics = useMemo(() => {
    const first = rows?.[0] || {};
    return Object.keys(first).filter((k) => !groupBy.includes(k) && !SKIP.has(k) && typeof first[k] === 'number');
  }, [rows, groupBy]);
  const labelKey = groupBy.find((g) => !['match_id', 'innings'].includes(g)) || groupBy[0];
  const names = useMemo(
    () => [...new Set((rows || []).map((r) => r[labelKey]).filter((v) => v !== null && v !== undefined).map(String))],
    [rows, labelKey],
  );
  const [metric, setMetric] = useState(metrics.includes(defaultMetric) ? defaultMetric : (metrics.includes('runs') ? 'runs' : metrics[0] || ''));
  const [highlight, setHighlight] = useState(null);
  const [state, setState] = useState({ loading: false, error: null, options: [], pickedBy: null });
  const [selected, setSelected] = useState(null);

  const make = async () => {
    setState({ loading: true, error: null, options: [], pickedBy: null });
    setSelected(null);
    try {
      const { data } = await axios.post(`${config.API_URL}/snapshots/graphic`, {
        query_string: apiQueryString, metric, highlight: highlight || null,
      });
      setState({ loading: false, error: null, options: data.options || [], pickedBy: data.picked_by });
      track('graphic_made', { metric, forms: (data.options || []).map((o) => o.form).join(','), highlight: Boolean(highlight) });
      setSelected((data.options || [])[0] || null);
    } catch (err) {
      setState({ loading: false, error: err.response?.data?.detail || 'Could not make a graphic for this result.', options: [], pickedBy: null });
    }
  };

  const imageUrl = selected ? `${siteOrigin()}/img/${selected.snapshot_id}.png` : null;

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
        <Autocomplete
          size="small"
          options={names}
          value={highlight}
          onChange={(_, v) => setHighlight(v)}
          renderInput={(params) => <TextField {...params} label={`Highlight (optional): ${label(labelKey)}`} />}
        />
        <Button variant="contained" onClick={make} disabled={!metric || state.loading} sx={{ ...qbButtonSx, minHeight: 44 }}>
          {state.loading ? <CircularProgress size={20} color="inherit" /> : 'Make graphic'}
        </Button>
        {state.error && <Alert severity="warning">{state.error}</Alert>}

        {state.options.length > 0 && (
          <>
            {state.options.length > 1 && (
              <Box>
                <Typography sx={{ fontSize: 12, color: qbColors.textLo, mb: 0.75 }}>Chart · tap to switch</Typography>
                <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', pb: 0.5 }}>
                  {state.options.map((o) => {
                    const active = selected?.snapshot_id === o.snapshot_id;
                    return (
                      <Box key={o.snapshot_id} component="button" type="button" onClick={() => setSelected(o)}
                        sx={{ flex: '0 0 auto', width: 92, p: 0.5, bgcolor: 'transparent', cursor: 'pointer', color: qbColors.textHi,
                          border: `2px solid ${active ? qbColors.accent || '#b6f24a' : 'rgba(255,255,255,0.12)'}`, borderRadius: 2 }}>
                        <Box component="img" src={`${siteOrigin()}/img/${o.snapshot_id}.png`} alt={FORM_NAMES[o.form] || o.form} loading="lazy"
                          sx={{ width: '100%', aspectRatio: '4 / 5', display: 'block', borderRadius: 1, bgcolor: '#14171e' }} />
                        <Typography sx={{ fontSize: 12, mt: 0.5 }}>{FORM_NAMES[o.form] || o.form}</Typography>
                      </Box>
                    );
                  })}
                </Box>
              </Box>
            )}
            {selected && (
              <Box>
                <Box component="img" src={imageUrl} alt={selected.title}
                  sx={{ width: '100%', maxWidth: 420, aspectRatio: '4 / 5', display: 'block', mx: 'auto', borderRadius: 2, bgcolor: '#14171e' }} />
                <Box sx={{ display: 'flex', gap: 1, mt: 1.5, flexWrap: 'wrap' }}>
                  <Button variant="contained" sx={{ ...qbButtonSx, minHeight: 44, flex: 1 }}
                    onClick={() => {
                      // 'share' is the usage report's existing share count; kind tells graphics apart.
                      track('share', { kind: 'graphic', form: selected.form });
                      shareImage(imageUrl, `hindsight-${selected.snapshot_id}.png`, selected.title, `${selected.title} · hindsightcricket.com`);
                    }}>
                    Share
                  </Button>
                  <Button variant="outlined" href={`${imageUrl}?download=1`} onClick={() => track('graphic_download', { form: selected.form })} sx={{ minHeight: 44, flex: 1, color: qbColors.textHi, borderColor: 'rgba(255,255,255,0.2)' }}>
                    Download
                  </Button>
                  <Button variant="outlined" onClick={() => navigator.clipboard?.writeText(`${window.location.origin}/g/${selected.snapshot_id}`)}
                    sx={{ minHeight: 44, flex: 1, color: qbColors.textHi, borderColor: 'rgba(255,255,255,0.2)' }}>
                    Copy link
                  </Button>
                </Box>
              </Box>
            )}
          </>
        )}
      </Box>
    </Dialog>
  );
};

export default GraphicMaker;
