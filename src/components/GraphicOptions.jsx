import React, { useEffect, useState } from 'react';
import { Box, Button, Typography } from '@mui/material';
import { shareImage, siteOrigin } from './ui/ChartExportButton';
import { track } from '../utils/analytics';
import { colors as hs } from '../theme/hindsightDark';

export const FORM_NAMES = {
  bars: 'Ranked bars', line: 'Trend line', scatter: 'Scatter', stat: 'Big number',
  diverging: 'Above / below', dumbbell: 'Dumbbell', stacked: 'Stacked', field: 'Field map',
};

/** A graphic's chart options: thumbnails to switch, the chosen image large, Share / Download / Copy link. */
const GraphicOptions = ({ options, source }) => {
  const [selected, setSelected] = useState(options[0] || null);
  const [copied, setCopied] = useState(false);
  useEffect(() => { setSelected(options[0] || null); }, [options]);
  if (!selected) return null;
  const imageUrl = `${siteOrigin()}/img/${selected.snapshot_id}.png`;
  const pageUrl = `${window.location.origin}/g/${selected.snapshot_id}`;
  const outline = { minHeight: 44, flex: 1, color: hs.textHi, borderColor: 'rgba(255,255,255,0.2)' };

  return (
    <Box sx={{ display: 'grid', gap: 1.5 }}>
      {options.length > 1 && (
        <Box>
          <Typography sx={{ fontSize: 12, color: hs.textLo, mb: 0.75 }}>Chart · tap to switch</Typography>
          <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', pb: 0.5 }}>
            {options.map((o) => {
              const active = selected.snapshot_id === o.snapshot_id;
              return (
                <Box key={o.snapshot_id} component="button" type="button" onClick={() => setSelected(o)}
                  sx={{ flex: '0 0 auto', width: 92, p: 0.5, bgcolor: 'transparent', cursor: 'pointer', color: hs.textHi,
                    border: `2px solid ${active ? hs.accent : 'rgba(255,255,255,0.12)'}`, borderRadius: 2 }}>
                  <Box component="img" src={`${siteOrigin()}/img/${o.snapshot_id}.png`} alt={FORM_NAMES[o.form] || o.form} loading="lazy"
                    sx={{ width: '100%', aspectRatio: '4 / 5', display: 'block', borderRadius: 1, bgcolor: hs.surface2 }} />
                  <Typography sx={{ fontSize: 12, mt: 0.5 }}>{FORM_NAMES[o.form] || o.form}</Typography>
                </Box>
              );
            })}
          </Box>
        </Box>
      )}
      <Box component="img" src={imageUrl} alt={selected.title}
        sx={{ width: '100%', maxWidth: 420, aspectRatio: '4 / 5', display: 'block', mx: 'auto', borderRadius: 2, bgcolor: hs.surface2 }} />
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        <Button variant="contained"
          sx={{ minHeight: 44, flex: 1, bgcolor: hs.accent, color: hs.bg, fontWeight: 700, '&:hover': { bgcolor: hs.accentHover } }}
          onClick={() => {
            // 'share' is the usage report's existing share count; kind tells graphics apart.
            track('share', { kind: 'graphic', form: selected.form, source });
            shareImage(imageUrl, `hindsight-${selected.snapshot_id}.png`, selected.title, `${selected.title} · hindsightcricket.com`);
          }}>
          Share
        </Button>
        <Button variant="outlined" href={`${imageUrl}?download=1`} onClick={() => track('graphic_download', { form: selected.form, source })} sx={outline}>
          Download
        </Button>
        <Button variant="outlined" sx={outline}
          onClick={() => { navigator.clipboard?.writeText(pageUrl); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>
          {copied ? 'Copied' : 'Copy link'}
        </Button>
      </Box>
    </Box>
  );
};

export default GraphicOptions;
