import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Button, TextField, Typography } from '@mui/material';
import { GRAPHIC_EXAMPLES } from '../utils/graphicExamples';
import { colors as hs, fonts } from '../theme/hindsightDark';

/**
 * /graphics: "describe a graphic". The question goes to the query builder's plain-English box
 * (?nl=), whose interpretation chips are the confirm step; with graphic=1 the graphic maker opens
 * as soon as the grouped result is in.
 */
const GraphicsLanding = () => {
  const navigate = useNavigate();
  const [text, setText] = useState('');
  const go = (q) => {
    const value = (q ?? text).trim();
    if (value.length < 6) return;
    navigate(`/query?nl=${encodeURIComponent(value)}&graphic=1`);
  };
  return (
    <Box sx={{ maxWidth: 560, mx: 'auto', px: 2, py: 3, display: 'grid', gap: 2 }}>
      <Box>
        <Typography component="h1" sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 28, color: hs.textHi }}>
          Make a cricket graphic
        </Typography>
        <Typography sx={{ color: hs.textMed, mt: 0.5 }}>
          Describe a stat. We run it on ball-by-ball data, show you what we understood, and draw a phone-sized
          graphic you can share, titled from the real numbers.
        </Typography>
      </Box>
      <TextField
        multiline
        minRows={2}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="e.g. Average v strike rate for T20 batters since 2024 with 1000+ balls"
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); go(); } }}
      />
      <Button variant="contained" onClick={() => go()} disabled={text.trim().length < 6}
        sx={{ minHeight: 48, bgcolor: hs.accent, color: hs.bg, fontWeight: 700, '&:hover': { bgcolor: hs.accentHover } }}>
        Make graphic
      </Button>
      <Box>
        <Typography sx={{ fontSize: 13, color: hs.textLo, mb: 1 }}>Or start from an example</Typography>
        {GRAPHIC_EXAMPLES.map(([form, idea]) => (
          <Box key={form} component="button" type="button" onClick={() => go(idea)}
            sx={{ display: 'block', width: '100%', textAlign: 'left', bgcolor: hs.surface1, border: `1px solid ${hs.border}`,
              borderRadius: 2, p: 1.5, mb: 1, cursor: 'pointer', color: hs.textHi, '&:hover': { borderColor: hs.accent } }}>
            <Typography component="span" sx={{ display: 'block', fontSize: 12, color: hs.accent, fontWeight: 600 }}>{form}</Typography>
            <Typography component="span" sx={{ display: 'block', fontSize: 14, color: hs.textMed }}>{idea}</Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default GraphicsLanding;
