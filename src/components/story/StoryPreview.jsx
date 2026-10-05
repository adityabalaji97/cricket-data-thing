import React, { useState } from 'react';
import { Box, Button, CircularProgress } from '@mui/material';
import AutoStoriesOutlinedIcon from '@mui/icons-material/AutoStoriesOutlined';
import StoryViewer from './StoryViewer';
import StoryGrid from './StoryGrid';
import useIsMobile from '../../hooks/useIsMobile';
import { colors } from '../../theme/hindsightDark';

/**
 * The story-style preview: on phones the viewer opens straight away; on desktop the cards sit in
 * a grid and a click opens the viewer at that card. "Preview settings" and "Classic page" close
 * the viewer, leaving the classic page with a button to reopen the story.
 */
const StoryPreview = ({ chapters, fixtureLabel, onSettings, onClassic, classicPage, loading = false }) => {
  const { isMobile } = useIsMobile();
  const [open, setOpen] = useState(isMobile);
  const [startCardId, setStartCardId] = useState(null);
  const [classic, setClassic] = useState(false);

  if (loading && !chapters.length) {
    return (
      <Box role="status" aria-label="Loading the preview" sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress size={28} sx={{ color: colors.accent }} />
      </Box>
    );
  }
  // No cards (no fixture picked, or nothing to show): the classic page.
  if (!chapters.some((c) => c.cards.length)) return classicPage;

  const viewer = open && (
    <StoryViewer
      chapters={chapters}
      fixtureLabel={fixtureLabel}
      startCardId={startCardId}
      onClose={isMobile ? undefined : () => setOpen(false)}
      onSettings={onSettings ? () => { setOpen(false); setClassic(true); if (onClassic) onClassic(); onSettings(); } : undefined}
      onClassic={() => { setOpen(false); setClassic(true); if (onClassic) onClassic(); }}
    />
  );

  const reopen = (
    <Button
      onClick={() => { setStartCardId(null); setClassic(false); setOpen(true); }}
      startIcon={<AutoStoriesOutlinedIcon />}
      sx={{ minHeight: 40, color: colors.accent, textTransform: 'none', fontWeight: 600 }}
    >
      Story view
    </Button>
  );

  if (classic || (isMobile && !open)) {
    return (
      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', px: 1 }}>{reopen}</Box>
        {classicPage}
        {viewer}
      </Box>
    );
  }

  return (
    <Box>
      {!isMobile && (
        <StoryGrid chapters={chapters} onOpen={(id) => { setStartCardId(id); setOpen(true); }} />
      )}
      {viewer}
    </Box>
  );
};

export default StoryPreview;
