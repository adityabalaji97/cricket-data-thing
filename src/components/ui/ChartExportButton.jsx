import React, { useState } from 'react';
import {
  Box, Button, CircularProgress, Dialog, DialogContent, DialogTitle, IconButton, Snackbar,
  ToggleButton, ToggleButtonGroup, Typography,
} from '@mui/material';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import ImageOutlinedIcon from '@mui/icons-material/ImageOutlined';
import axios from 'axios';
import config from '../../config';
import { track } from '../../utils/analytics';

/**
 * "Image & embed": freezes what the viewer is looking at as a chart snapshot (POST /snapshots)
 * and offers it three ways:
 *   - a share image (/img/:id.png), sized for phone feeds, to download or send via the share sheet
 *   - an iframe snippet (/embed/{q|wp|recap}/:id) for blogs and newsletters
 *   - a direct link to the embed page
 *
 * `request` is the POST /snapshots body ({kind, params, query_string}); it is sent when the dialog
 * opens, so nothing runs until someone asks.
 */
const SITE = 'https://hindsightcricket.com';
// Local dev has no /img or /embed functions; point at production there.
export const siteOrigin = () => (/^(localhost|127\.)/.test(window.location.hostname) ? SITE : window.location.origin);

// Phones: hand the PNG itself to the share sheet (WhatsApp, Reddit app, Photos), with the title
// as text where the target takes it. Elsewhere: download it. Returns false if the user cancelled.
export const shareImage = async (imageUrl, fileName, title, text) => {
  try {
    const blob = await (await fetch(imageUrl)).blob();
    const file = new File([blob], fileName, { type: 'image/png' });
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      await navigator.share({ files: [file], title: title || 'Hindsight', ...(text ? { text } : {}) });
      return true;
    }
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = file.name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 5000);
    return true;
  } catch (err) {
    if (err?.name === 'AbortError') return false;
    window.open(`${imageUrl}${imageUrl.includes('?') ? '&' : '?'}download=1`, '_blank', 'noopener');
    return true;
  }
};

const EMBED_PATH = { query: 'q', win_prob: 'wp', recap: 'recap' };
const EMBED_HEIGHT = { query: 520, win_prob: 400, recap: 420 };
const SIZES = [
  { key: 'portrait', label: '4:5', hint: 'Reddit, Instagram, X' },
  { key: 'square', label: '1:1', hint: 'WhatsApp, Instagram' },
  { key: 'card', label: 'Wide', hint: 'Link cards, slides' },
];

const embedSnippet = (id, kind, title) => {
  const src = `${SITE}/embed/${EMBED_PATH[kind]}/${id}`;
  return `<iframe src="${src}" title="${(title || 'Hindsight chart').replace(/"/g, '&quot;')}" width="100%" height="${EMBED_HEIGHT[kind]}" style="border:0;max-width:680px" loading="lazy"></iframe>\n`
    + `<script>addEventListener("message",function(e){if(e.origin==="${SITE}"&&e.data&&e.data.type==="hindsight:resize")document.querySelectorAll('iframe[src^="${SITE}/embed/"]').forEach(function(f){if(f.contentWindow===e.source)f.style.height=e.data.height+"px"})})</script>`;
};

const ChartExportButton = ({ request, label = 'Image & embed', sx, disabled }) => {
  const [open, setOpen] = useState(false);
  const [snap, setSnap] = useState(null);
  const [error, setError] = useState(null);
  const [size, setSize] = useState('portrait');
  const [toast, setToast] = useState(null);
  const [requestKey, setRequestKey] = useState(null);

  const openDialog = async () => {
    setOpen(true);
    const body = typeof request === 'function' ? request() : request;
    const key = JSON.stringify(body);
    if (snap && key === requestKey) return;
    setSnap(null);
    setError(null);
    setRequestKey(key);
    try {
      const { data } = await axios.post(`${config.API_URL}/snapshots`, body);
      setSnap(data);
      track('snapshot_create', { kind: data.kind });
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not create the chart. Try again in a moment.');
    }
  };

  const imageUrl = snap ? `${siteOrigin()}/img/${snap.id}.png?size=${size}` : null;

  const copy = async (text, what) => {
    try {
      await navigator.clipboard.writeText(text);
      setToast(`${what} copied`);
      track('embed_copy', { kind: snap?.kind, what });
    } catch {
      setToast('Copy blocked by the browser');
    }
  };

  const saveImage = async () => {
    track('image_download', { kind: snap.kind, size });
    await shareImage(imageUrl, `hindsight-${snap.id}.png`, snap.title);
  };

  return (
    <>
      <Button size="small" variant="outlined" startIcon={<ImageOutlinedIcon />} onClick={openDialog}
        disabled={disabled} sx={{ minHeight: 36, ...sx }}>
        {label}
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm"
        PaperProps={{ sx: { bgcolor: '#0a0c11', color: '#f3f4f6', backgroundImage: 'none', m: 2, width: 'calc(100% - 32px)' } }}>
        <DialogTitle sx={{ pr: 6, fontSize: 17, fontWeight: 700 }}>
          Image & embed
          <IconButton aria-label="Close" onClick={() => setOpen(false)} sx={{ position: 'absolute', right: 8, top: 8, color: '#9aa1ac' }}>
            <CloseRoundedIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ pb: 3 }}>
          {!snap && !error && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 4, color: '#9aa1ac' }}>
              <CircularProgress size={20} sx={{ color: '#b6f24a' }} /> Freezing this chart…
            </Box>
          )}
          {error && <Typography sx={{ color: '#e5484d', py: 2 }}>{error}</Typography>}
          {snap && (
            <>
              <ToggleButtonGroup exclusive size="small" value={size} onChange={(e, v) => v && setSize(v)}
                sx={{ mb: 1.5, '& .MuiToggleButton-root': { color: '#c3c8d0', borderColor: 'rgba(255,255,255,.15)', px: 1.5 },
                  '& .Mui-selected': { color: '#0a0c11 !important', bgcolor: '#b6f24a !important' } }}>
                {SIZES.map((s) => <ToggleButton key={s.key} value={s.key}>{s.label}</ToggleButton>)}
              </ToggleButtonGroup>
              <Typography sx={{ fontSize: 12, color: '#9aa1ac', mb: 1 }}>
                {SIZES.find((s) => s.key === size)?.hint}
              </Typography>
              <Box component="img" src={imageUrl} alt={snap.title || 'Chart image'}
                sx={{ display: 'block', width: '100%', maxWidth: size === 'card' ? 520 : 360, borderRadius: 1.5,
                  border: '1px solid rgba(255,255,255,.08)', bgcolor: '#14171e', aspectRatio: size === 'portrait' ? '4 / 5' : size === 'square' ? '1 / 1' : '1200 / 630' }} />
              <Button variant="contained" onClick={saveImage}
                sx={{ mt: 1.5, minHeight: 44, bgcolor: '#b6f24a', color: '#0a0c11', fontWeight: 700, '&:hover': { bgcolor: '#a3dc3f' } }}>
                {navigator.canShare ? 'Share / save image' : 'Download image'}
              </Button>

              <Typography sx={{ mt: 3, mb: 0.75, fontSize: 13, fontWeight: 700 }}>Embed on your site</Typography>
              <Box component="textarea" readOnly value={embedSnippet(snap.id, snap.kind, snap.title)} rows={4}
                onFocus={(e) => e.target.select()}
                sx={{ width: '100%', resize: 'none', fontFamily: 'ui-monospace, monospace', fontSize: 11, color: '#c3c8d0',
                  bgcolor: '#14171e', border: '1px solid rgba(255,255,255,.1)', borderRadius: 1, p: 1 }} />
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                <Button size="small" variant="outlined" onClick={() => copy(embedSnippet(snap.id, snap.kind, snap.title), 'Embed code')}
                  sx={{ color: '#f3f4f6', borderColor: 'rgba(255,255,255,.2)', minHeight: 36 }}>Copy embed code</Button>
                <Button size="small" variant="outlined" onClick={() => copy(`${SITE}/embed/${EMBED_PATH[snap.kind]}/${snap.id}`, 'Link')}
                  sx={{ color: '#f3f4f6', borderColor: 'rgba(255,255,255,.2)', minHeight: 36 }}>Copy link</Button>
              </Box>
              <Typography sx={{ mt: 1.5, fontSize: 11, color: '#9aa1ac' }}>
                The image and embed are frozen at today's numbers, so they never change under your post.
              </Typography>
            </>
          )}
        </DialogContent>
      </Dialog>
      <Snackbar open={!!toast} autoHideDuration={2000} onClose={() => setToast(null)} message={toast}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }} />
    </>
  );
};

export default ChartExportButton;
