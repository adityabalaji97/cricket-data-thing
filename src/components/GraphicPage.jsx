import React, { useEffect, useState } from 'react';
import { Link as RouterLink, useParams } from 'react-router-dom';
import axios from 'axios';
import { Box, Button, CircularProgress, Typography } from '@mui/material';
import config from '../config';
import { shareImage, siteOrigin } from './ui/ChartExportButton';
import { track } from '../utils/analytics';
import { colors as hs, fonts } from '../theme/hindsightDark';

/**
 * /g/:id — a shared graphic. Link previews (WhatsApp, Reddit, X) get its title and image from
 * api/meta.mjs; people get the image, the query behind it, and a way to make their own.
 */
const GraphicPage = () => {
  const { id } = useParams();
  const [snap, setSnap] = useState(undefined);

  useEffect(() => {
    axios.get(`${config.API_URL}/snapshots/${encodeURIComponent(id)}`)
      .then(({ data }) => setSnap(data))
      .catch(() => setSnap(null));
  }, [id]);

  if (snap === undefined) {
    return <Box sx={{ py: 6, display: 'flex', justifyContent: 'center' }}><CircularProgress /></Box>;
  }
  if (!snap) {
    return (
      <Box sx={{ px: 2, py: 6, textAlign: 'center' }}>
        <Typography sx={{ mb: 2 }}>This graphic doesn&apos;t exist (or the link is incomplete).</Typography>
        <Button component={RouterLink} to="/query" variant="outlined">Make a graphic</Button>
      </Box>
    );
  }

  const imageUrl = `${siteOrigin()}/img/${snap.id}.png`;
  const queryLink = (() => {
    try {
      const u = new URL(snap.data?.hindsight_url || '');
      return `${u.pathname}${u.search}`;
    } catch {
      return null;
    }
  })();

  return (
    <Box sx={{ maxWidth: 480, mx: 'auto', px: 2, py: 2, display: 'grid', gap: 1.5 }}>
      <Typography component="h1" sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 22, lineHeight: 1.2, color: hs.textHi }}>
        {snap.title}
      </Typography>
      {(snap.kind === 'carousel' ? (snap.data?.slides || []).map((_, i) => `${imageUrl}?slide=${i + 1}`) : [imageUrl]).map((src, i) => (
        // A carousel (an Instagram post) shows every slide, top to bottom.
        <Box key={src} component="img" src={src} alt={`${snap.title}${snap.kind === 'carousel' ? ` · slide ${i + 1}` : ''}`}
          loading={i ? 'lazy' : 'eager'}
          sx={{ width: '100%', aspectRatio: '4 / 5', display: 'block', borderRadius: 2, bgcolor: hs.surface2 }} />
      ))}
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        <Button variant="contained" sx={{ flex: 1, minHeight: 44, bgcolor: hs.accent, color: hs.bg, fontWeight: 700, '&:hover': { bgcolor: hs.accentHover } }}
          onClick={() => { track('share', { kind: 'graphic_page' }); shareImage(imageUrl, `hindsight-${snap.id}.png`, snap.title, `${snap.title} · hindsightcricket.com`); }}>
          Share
        </Button>
        <Button variant="outlined" href={`${imageUrl}?download=1`} sx={{ flex: 1, minHeight: 44 }}>Download</Button>
      </Box>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        {queryLink && <Button component={RouterLink} to={queryLink} sx={{ flex: 1, minHeight: 44 }}>Open this query</Button>}
        <Button component={RouterLink} to="/query" sx={{ flex: 1, minHeight: 44 }}>Make your own</Button>
      </Box>
      <Typography sx={{ fontSize: 12, color: hs.textLo }}>
        Made on Hindsight from ball-by-ball data. Numbers as of {String(snap.created_at || '').slice(0, 10)}.
      </Typography>
    </Box>
  );
};

export default GraphicPage;
