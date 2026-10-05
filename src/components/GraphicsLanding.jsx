import React, { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import axios from 'axios';
import { Alert, Box, Button, Chip, CircularProgress, TextField, Typography } from '@mui/material';
import config from '../config';
import GraphicOptions from './GraphicOptions';
import GraphicPromptList from './GraphicPromptList';
import { track } from '../utils/analytics';
import { colors as hs, fonts } from '../theme/hindsightDark';
import { apiErrorText } from '../utils/apiError';

const FORMATS = [['', 'Auto'], ['T20', 'T20'], ['ODI', 'ODI']];

const pathOf = (url) => {
  try {
    const u = new URL(url);
    return `${u.pathname}${u.search}`;
  } catch {
    return null;
  }
};

/**
 * /graphics — "Make a Graphic": the admin idea box for everyone. A plain-English idea is parsed,
 * run on ball-by-ball data and drawn as share-ready chart options right here; the query behind it
 * opens in the query builder. Server side: POST /snapshots/idea (daily per-person limit).
 */
const GraphicsLanding = () => {
  const [text, setText] = useState('');
  const [format, setFormat] = useState('');
  const [state, setState] = useState({ loading: false, error: null, result: null });

  const make = async (idea = text, fmt = format) => {
    const value = (idea || '').trim();
    if (value.length < 6) return;
    setText(value);
    setFormat(fmt);
    setState({ loading: true, error: null, result: null });
    try {
      const { data } = await axios.post(`${config.API_URL}/snapshots/idea`, { text: value, format: fmt || null }, { timeout: 60000 });
      setState({ loading: false, error: null, result: data });
      track('graphic_made', { source: 'idea', forms: (data.options || []).map((o) => o.form).join(',') });
    } catch (err) {
      setState({ loading: false, result: null,
        error: apiErrorText(err, null) || 'Could not make that one. Try rewording it, or build it in the query builder.' });
    }
  };

  const queryPath = state.result?.query_url ? pathOf(state.result.query_url) : null;

  return (
    <Box sx={{ maxWidth: 560, mx: 'auto', px: 2, py: 3, display: 'grid', gap: 2 }}>
      <Box>
        <Typography component="h1" sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 28, color: hs.textHi }}>
          Make a cricket graphic
        </Typography>
        <Typography sx={{ color: hs.textMed, mt: 0.5 }}>
          Describe a stat. We run it on ball-by-ball data and draw a phone-sized graphic, titled from the real
          numbers, ready to share.
        </Typography>
      </Box>
      <TextField
        multiline
        minRows={2}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="e.g. Virat Kohli runs by wagon zone since 2024"
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); make(); } }}
      />
      <Box sx={{ display: 'flex', gap: 0.75, alignItems: 'center', flexWrap: 'wrap' }}>
        {FORMATS.map(([value, label]) => (
          <Chip key={label} label={label} onClick={() => setFormat(value)}
            sx={{ bgcolor: format === value ? hs.accent : hs.surface2, color: format === value ? hs.bg : hs.textMed, fontWeight: 600 }} />
        ))}
        <Button variant="contained" onClick={() => make()} disabled={state.loading || text.trim().length < 6}
          sx={{ ml: 'auto', minHeight: 44, px: 3, bgcolor: hs.accent, color: hs.bg, fontWeight: 700, '&:hover': { bgcolor: hs.accentHover } }}>
          Make graphic
        </Button>
      </Box>

      {state.loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, color: hs.textMed }}>
          <CircularProgress size={20} />
          <Typography sx={{ fontSize: 14 }}>Reading your idea, running it on the data and drawing the charts…</Typography>
        </Box>
      )}
      {state.error && <Alert severity="warning">{state.error}</Alert>}

      {state.result && (
        <Box sx={{ display: 'grid', gap: 1.5 }}>
          {(state.result.chips || []).length > 0 && (
            <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', alignItems: 'center' }}>
              <Typography sx={{ fontSize: 13, color: hs.textLo }}>What we ran:</Typography>
              {state.result.chips.map((c) => (
                <Chip key={c} size="small" label={c} sx={{ bgcolor: hs.surface2, color: hs.textMed }} />
              ))}
            </Box>
          )}
          <GraphicOptions options={state.result.options || []} source="idea" />
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {queryPath && (
              <Button component={RouterLink} to={queryPath} variant="outlined" sx={{ flex: 1, minHeight: 44 }}>
                View the query results
              </Button>
            )}
            <Button onClick={() => { setState({ loading: false, error: null, result: null }); setText(''); }} sx={{ flex: 1, minHeight: 44 }}>
              Try another idea
            </Button>
          </Box>
        </Box>
      )}

      {!state.loading && (
        <GraphicPromptList onPick={(prompt, fmt) => { window.scrollTo({ top: 0, behavior: 'smooth' }); make(prompt, fmt); }} />
      )}
    </Box>
  );
};

export default GraphicsLanding;
