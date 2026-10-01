import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Box } from '@mui/material';
import { colors, fonts } from '../../theme/hindsightDark';
import { siteOrigin } from '../ui/ChartExportButton';
import { markdownToHtml, splitBody } from './noteMarkdown.mjs';

/**
 * A note's body: markdown, with each ```hindsight chart fence rendered as the /embed/* iframe for
 * its snapshot. One renderer serves our own pages and every other site that embeds the chart.
 * Each embed posts {type:'hindsight:resize', height}; the frame follows it.
 */
export const embedOrigin = siteOrigin;

export const NoteChart = ({ id, chart }) => {
  const ref = useRef(null);
  const [height, setHeight] = useState(chart?.embed === 'recap' ? 260 : 380);
  const origin = embedOrigin();

  useEffect(() => {
    const onMessage = (e) => {
      if (e.origin !== origin || e.source !== ref.current?.contentWindow) return;
      if (e.data?.type === 'hindsight:resize' && e.data.height > 0) setHeight(Math.min(e.data.height, 2400));
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [origin]);

  if (!chart) {
    return <Box sx={{ my: 2, p: 2, borderRadius: 2, border: `1px dashed ${colors.borderStrong}`, color: colors.textLo, fontSize: 13 }}>Chart {id} not found.</Box>;
  }
  return (
    <Box component="figure" sx={{ m: 0, my: 2.5 }}>
      <Box component="iframe" ref={ref} title={chart.title || 'Hindsight chart'} loading="lazy"
        src={`${origin}/embed/${chart.embed}/${id}`}
        sx={{ display: 'block', width: '100%', height, border: `1px solid ${colors.border}`, borderRadius: '14px', bgcolor: colors.bg }} />
    </Box>
  );
};

export const proseSx = {
  color: colors.textMed,
  fontFamily: fonts.body,
  fontSize: { xs: 16.5, md: 17 },
  lineHeight: 1.65,
  overflowWrap: 'anywhere',
  '& p': { my: 1.75 },
  '& h2, & h3, & h4': { fontFamily: fonts.display, color: colors.textHi, lineHeight: 1.2, mt: 3.5, mb: 1.25 },
  '& h2': { fontSize: { xs: 23, md: 26 } },
  '& h3': { fontSize: { xs: 19, md: 21 } },
  '& strong': { color: colors.textHi, fontWeight: 600 },
  '& a': { color: colors.accent, textDecorationColor: 'rgba(182,242,74,.4)', textUnderlineOffset: '3px' },
  '& ul, & ol': { pl: 3, my: 1.75 },
  '& li': { mb: 0.75 },
  '& li::marker': { color: colors.accent },
  '& blockquote': { m: 0, my: 2, pl: 2, borderLeft: `3px solid ${colors.accent}`, color: colors.textHi },
  '& code': { fontFamily: fonts.mono, fontSize: '0.88em', bgcolor: colors.surface2, px: 0.5, borderRadius: 1 },
  '& pre': { overflowX: 'auto', bgcolor: colors.surface2, p: 1.5, borderRadius: 2 },
  '& img': { maxWidth: '100%', height: 'auto', borderRadius: 2 },
  '& hr': { border: 0, borderTop: `1px solid ${colors.border}`, my: 3 },
  // Tables scroll inside themselves; the page never scrolls sideways on a phone.
  '& table': { display: 'block', overflowX: 'auto', borderCollapse: 'collapse', fontSize: 14, my: 2, maxWidth: '100%' },
  '& th, & td': { borderBottom: `1px solid ${colors.border}`, px: 1.25, py: 0.75, textAlign: 'left', whiteSpace: 'nowrap' },
  '& th': { color: colors.textLo, fontWeight: 600, fontSize: 12, textTransform: 'uppercase', letterSpacing: '.06em' },
};

const NoteBody = ({ body, charts = {} }) => {
  const segments = useMemo(() => splitBody(body).map((s) => (
    s.type === 'md' ? { ...s, html: markdownToHtml(s.text) } : s
  )), [body]);
  return (
    <Box sx={proseSx}>
      {segments.map((s, i) => (s.type === 'chart'
        ? <NoteChart key={`${s.id}-${i}`} id={s.id} chart={charts[s.id]} />
        // markdownToHtml escapes raw HTML and unsafe URLs (noteMarkdown.mjs).
        : <div key={i} dangerouslySetInnerHTML={{ __html: s.html }} />))}
    </Box>
  );
};

export default NoteBody;
