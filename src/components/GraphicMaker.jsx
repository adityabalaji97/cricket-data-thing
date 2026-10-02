import React, { useMemo, useState } from 'react';
import axios from 'axios';
import {
  Alert, Autocomplete, Box, Button, CircularProgress, Dialog, IconButton, MenuItem, TextField, Typography,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import config from '../config';
import useIsMobile from '../hooks/useIsMobile';
import { track } from '../utils/analytics';
import GraphicOptions from './GraphicOptions';
import { qbButtonSx, qbColors, qbFonts } from './queryBuilderTheme';


const SKIP = new Set(['percent_balls', 'innings_count', 'metric_balls']);
const label = (key) => key.replace(/_/g, ' ').replace(/\bpercentage\b/, '%');

/**
 * "Make a graphic" from the result on screen: the same chart forms and phone-sized share images
 * as the admin idea packs, from the query the viewer already ran (no LLM). The server re-runs the
 * query from its query string, so the numbers in a graphic are always real.
 */
const GraphicMaker = ({ open, onClose, apiQueryString, rows, groupBy, defaultMetric, scatter }) => {
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

  const make = async () => {
    setState({ loading: true, error: null, options: [], pickedBy: null });
    try {
      const { data } = await axios.post(`${config.API_URL}/snapshots/graphic`, {
        query_string: apiQueryString, metric, highlight: highlight || null,
        // Two metrics in the question (parser's scatter): offer a scatter of them.
        chart: scatter && scatter.x_axis && scatter.y_axis ? { type: 'scatter', x_axis: scatter.x_axis, y_axis: scatter.y_axis } : null,
      });
      setState({ loading: false, error: null, options: data.options || [], pickedBy: data.picked_by });
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

        {state.options.length > 0 && <GraphicOptions options={state.options} source="query" />}
      </Box>
    </Dialog>
  );
};

export default GraphicMaker;
