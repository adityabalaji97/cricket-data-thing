import React from 'react';
import { Box, Button, Typography } from '@mui/material';
import { colors, fonts } from '../../theme/hindsightDark';

// Around the lazily loaded pages (landing plan L6): if a page's code can't load (offline, or a stale chunk after a
// deploy that one reload didn't fix), say so with a Reload button instead of leaving an empty page.
class ChunkErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error) {
    console.error('Page failed to load:', error);
  }

  componentDidUpdate(prev) {
    // A new route gets a fresh try.
    if (this.state.failed && prev.resetKey !== this.props.resetKey) this.setState({ failed: false });
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <Box role="alert" sx={{ minHeight: '60vh', display: 'grid', placeItems: 'center', bgcolor: colors.bg, color: colors.textHi, px: 2 }}>
        <Box sx={{ textAlign: 'center' }}>
          <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 22 }}>Couldn&apos;t load this page</Typography>
          <Typography sx={{ color: colors.textLo, fontSize: 14, mt: 0.5 }}>Check your connection, then reload.</Typography>
          <Button type="button" onClick={() => window.location.reload()}
            sx={{ mt: 2, minHeight: 44, px: 2.5, borderRadius: 2, bgcolor: colors.accent, color: colors.bg, fontFamily: fonts.mono,
              fontWeight: 700, fontSize: 12, letterSpacing: '0.08em', '&:hover': { bgcolor: colors.accentHover } }}>
            Reload
          </Button>
        </Box>
      </Box>
    );
  }
}

export default ChunkErrorBoundary;
