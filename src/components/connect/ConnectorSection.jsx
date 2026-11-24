import React, { useState } from 'react';
import { Box, Button, Typography } from '@mui/material';
import ContentCopyRoundedIcon from '@mui/icons-material/ContentCopyRounded';
import CheckRoundedIcon from '@mui/icons-material/CheckRounded';
import { fonts } from '../../theme/hindsightDark';
import { track } from '../../utils/analytics';
import { SectionHeader, chipSx, kitColors as C, monoSx } from '../landing/sectionKit';

// The Hindsight MCP connector (mcp_server/): lets Claude / ChatGPT query the data directly.
const CONNECTOR_URL = 'https://hindsightcricket.com/mcp';
const CONNECTOR_PROMPTS = [
  "Kohli's strike rate vs pace and spin by year in T20s",
  'Top 10 IPL 2026 strike rates, min 100 balls',
  'Preview South Africa v Australia at Kingsmead in ODIs',
];

// Lives on /connect (ConnectPage) since the landing redesign (L4); its own module since L6: setup instructions aren't a home-page section.
export const ConnectorSection = () => {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(CONNECTOR_URL);
      track('connector_copy');
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };
  const step = (label, text) => (
    <Typography sx={{ color: C.mid, fontFamily: fonts.body, fontSize: 14, lineHeight: 1.5 }}>
      <Box component="span" sx={{ color: C.hi, fontWeight: 700 }}>{label}</Box> {text}
    </Typography>
  );
  return (
    <Box component="section" id="connector" sx={{ mb: { xs: 3.75, md: 5.5 } }}>
      <SectionHeader
        kicker="Connect"
        title="Use Hindsight in Claude or ChatGPT"
        subtitle="Ask questions in plain English and get tables, charts and a link back here."
      />
      <Box sx={{ p: { xs: 2, md: 2.5 }, borderRadius: 3, bgcolor: C.surface, border: `1px solid ${C.hairline}`, display: 'grid', gridTemplateColumns: 'minmax(0, 1fr)', gap: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0, p: 1, pl: 1.5, borderRadius: 2, bgcolor: C.inset, border: `1px solid ${C.hairlineStrong}` }}>
          <Typography sx={{ ...monoSx, color: C.lime, fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', flex: 1, minWidth: 0 }}>
            {CONNECTOR_URL}
          </Typography>
          <Button
            onClick={copy}
            startIcon={copied ? <CheckRoundedIcon /> : <ContentCopyRoundedIcon />}
            sx={{ flexShrink: 0, minHeight: 44, px: 1.5, borderRadius: 2, bgcolor: C.lime, color: C.bg, fontFamily: fonts.mono, fontWeight: 700, fontSize: 12, '&:hover': { bgcolor: C.limeHover } }}
          >
            {copied ? 'Copied' : 'Copy'}
          </Button>
        </Box>
        {step('Claude:', 'Settings → Connectors → Add custom connector → paste the URL.')}
        {step('ChatGPT:', 'Settings → Apps & Connectors → turn on Developer mode → Create → paste the URL, no authentication.')}
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75, pt: 0.5 }}>
          {CONNECTOR_PROMPTS.map((prompt) => (
            <Typography key={prompt} sx={{ ...chipSx, maxWidth: '100%', whiteSpace: 'normal', textTransform: 'none', letterSpacing: 0, fontSize: 12 }}>
              “{prompt}”
            </Typography>
          ))}
        </Box>
        <Typography sx={{ color: C.low, fontFamily: fonts.body, fontSize: 12 }}>
          Read-only and free to use; results are aggregated and rate-limited.
        </Typography>
      </Box>
    </Box>
  );
};

export default ConnectorSection;
