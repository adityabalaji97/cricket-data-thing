import React, { useEffect, useMemo, useState } from 'react';
import { flushSync } from 'react-dom';
import { useParams } from 'react-router-dom';
import { Box, Typography } from '@mui/material';
import axios from 'axios';
import config from '../../../config';
import { colors } from '../../../theme/hindsightDark';
import Captions from './Captions';
import ReelFrame from './ReelFrame';
import SceneHost from './SceneHost';
import { PAGE, REEL_FACES, activeScene, captionsFromTiming, setDrift, teamTone } from './motion';

/**
 * /ig/reel and /ig/:carouselId/reel: a 9:16 motion Reel drawn purely from a clock (MOTION_REEL_PLAN.md, M1).
 *
 * One input, a reel spec: snap.data.reel when the route has a carousel id, or window.setReel(spec) from the recorder
 * (scripts/record_ig_reel.mjs), so a Reel can be previewed with no snapshot and no deploy. window.renderAt(t) draws
 * the frame for t synchronously and returns true; every position, opacity and count is computed from t, so frames can
 * be rendered in any order. data-reel-ready="true" on the root once the spec and the fonts are in. ?t=12.5 shows one
 * moment in a browser; ?guides=1 draws the keep-clear zones.
 */
const IgReel = () => {
  const { carouselId } = useParams();
  const search = new URLSearchParams(window.location.search);
  const guides = search.get('guides') === '1';
  setDrift(search.get('nodrift') !== '1'); // the still check records with the bob off (M7)
  const [spec, setSpec] = useState(null);
  const [t, setT] = useState(Number(search.get('t')) || 0);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    window.setReel = (s) => { flushSync(() => { setReady(false); setSpec(s); }); return true; };
    window.renderAt = (time) => { flushSync(() => setT(Number(time) || 0)); return true; };
    return () => { delete window.setReel; delete window.renderAt; };
  }, []);

  useEffect(() => {
    if (!carouselId) return undefined;
    let live = true;
    axios.get(`${config.API_URL}/snapshots/${carouselId}`)
      .then(({ data }) => {
        if (!live) return;
        if (data?.data?.reel) setSpec(data.data.reel);
        else setError('This carousel has no reel spec');
      })
      .catch(() => { if (live) setError('Carousel not found'); });
    return () => { live = false; };
  }, [carouselId]);

  useEffect(() => {
    if (!spec) return undefined;
    let live = true;
    window.REEL_DURATION = spec.duration;
    window.REEL_SCENE_STARTS = (spec.scenes || []).map((x) => x.start);
    // Load every face and weight the scenes use before the first frame: document.fonts.ready alone resolves before a
    // face's first use, so a scene first drawn late (the closing card) would be laid out in the fallback font.
    // Google Fonts splits each face into unicode-range subsets loaded on first use (₹, −, · sit outside basic Latin),
    // so each face is loaded for every character the spec contains, plus the digits and signs count-ups draw and the
    // non-Latin glyphs the visuals write themselves (postVisuals / visuals: · × Δ – — ’ … ← ↑ → − ≤ │).
    const chars = [...new Set(`${JSON.stringify(spec)}0123456789+-.,%*₹·×Δ–—’…←↑→−≤│`)].join('');
    const loads = document.fonts ? REEL_FACES.map((f) => document.fonts.load(f, chars).catch(() => null)) : [];
    Promise.all(loads).then(() => document.fonts?.ready).then(() => requestAnimationFrame(() => requestAnimationFrame(() => {
      if (live) setReady(true);
    })));
    return () => { live = false; };
  }, [spec]);

  // Captions as given, or built from a voice timing file (lines, starts, lengths, words) as the finished Reels did.
  const captions = useMemo(() => (spec ? spec.captions || (spec.timing ? captionsFromTiming(spec.timing) : []) : []), [spec]);

  if (error) return <Typography sx={{ color: colors.red, p: 2 }}>{error}</Typography>;
  if (!spec) return <Box sx={{ width: PAGE.w, height: PAGE.h, bgcolor: colors.bg }} />;

  const scene = (spec.scenes || [])[activeScene(spec.scenes, t)] || {};
  const tone = teamTone(spec.team);
  const glow = teamTone(scene.team || spec.team).fill;
  return (
    // Library components bring their own CSS transitions (MUI's SvgIcon fades its fill): off for everything in the
    // Reel, so a frame depends on t alone and not on what was drawn before it.
    <Box data-ig-reel data-reel-ready={ready ? 'true' : undefined}
      sx={{ width: PAGE.w, height: PAGE.h, overflow: 'hidden', m: 0, '& *, & *::before, & *::after': { transition: 'none !important', animation: 'none !important' } }}>
      <ReelFrame t={t} tone={tone} glow={glow} chapters={spec.chapters} guides={guides}
        caption={<Captions captions={captions} scenes={spec.scenes} t={t} litColour={spec.caption_colour === 'team' ? tone.light : undefined} />}>
        <SceneHost spec={spec} t={t} />
      </ReelFrame>
    </Box>
  );
};

export default IgReel;
