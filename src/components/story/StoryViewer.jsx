import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Box, Button, IconButton, Typography } from '@mui/material';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import IosShareRoundedIcon from '@mui/icons-material/IosShareRounded';
import TableChartOutlinedIcon from '@mui/icons-material/TableChartOutlined';
import StoryCard from './StoryCard';
import LogoMenu from './LogoMenu';
import { STORY_BOTTOM, STORY_TOP, useStoryCoreSize } from './storyLayout';
import { colors, fonts } from '../../theme/hindsightDark';
import { track } from '../../utils/analytics';

const SWIPE_PX = 50;

/** Flatten chapters into one ordered list of cards, remembering each card's chapter. */
export const flattenChapters = (chapters) =>
  chapters.flatMap((chapter, chapterIndex) =>
    chapter.cards.map((card, indexInChapter) => ({ ...card, chapterIndex, indexInChapter })));

const hashCardId = () => (window.location.hash || '').replace(/^#/, '') || null;

/**
 * Story-style preview: one card per screen, chapters with progress segments, tap the left/right
 * edge or swipe sideways to move, arrow keys on a keyboard, no auto-advance. The middle of the
 * card is left to the chart (its taps open detail sheets). Covers the app's own top and bottom
 * bars while open; the floating logo button opens the chapter index and settings.
 *
 * Only the current card and its neighbours are mounted (CARTA Timely). Each card has its own
 * URL hash, so a shared link opens on that card.
 */
const StoryViewer = ({ chapters, fixtureLabel, startCardId, onClose, onSettings, onClassic }) => {
  const cards = useMemo(() => flattenChapters(chapters), [chapters]);
  // The card asked for (deep link or grid click). Cards arrive as their data loads, so a card
  // that is not there yet is remembered and opened when it appears -- unless the reader has
  // already moved on.
  //
  // Position is tracked by card id, not index: cards arriving later can be inserted ahead of the
  // one on screen, and an index would then point at a different card.
  const wanted = useRef(startCardId || hashCardId());
  const [currentId, setCurrentId] = useState(() => (cards.some((c) => c.id === wanted.current) ? wanted.current : null));
  useEffect(() => {
    if (wanted.current && cards.some((c) => c.id === wanted.current)) {
      setCurrentId(wanted.current);
      wanted.current = null;
    }
  }, [cards]);
  const found = cards.findIndex((c) => c.id === currentId);
  const index = found >= 0 ? found : 0;
  const [menuOpen, setMenuOpen] = useState(false);
  const { width, height } = useStoryCoreSize();
  const pointer = useRef(null);

  const current = cards[index];
  const chapter = chapters[current?.chapterIndex ?? 0];

  const go = useCallback((delta) => {
    wanted.current = null;
    const next = cards[Math.max(0, Math.min(cards.length - 1, index + delta))];
    if (next) setCurrentId(next.id);
  }, [cards, index]);

  // Deep link: keep the hash on the card being shown.
  // Card-level usage (MATCH_PREVIEW_VIZ_PLAN.md chunk 0 found none): which cards get read.
  useEffect(() => {
    if (current && !wanted.current) track('card_view', { card: current.id, chapter: chapter?.id });
  }, [current, chapter]);

  useEffect(() => {
    if (current && !wanted.current) window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}#${current.id}`);
  }, [current]);

  // Keyboard, and no page scroll behind the story.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'ArrowRight') go(1);
      if (e.key === 'ArrowLeft') go(-1);
      if (e.key === 'Escape' && onClose) onClose();
    };
    window.addEventListener('keydown', onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = previous;
    };
  }, [go, onClose]);

  const onPointerDown = (e) => {
    if (e.target.closest('[data-story-noswipe]')) return;
    pointer.current = { x: e.clientX, y: e.clientY };
  };
  const onPointerUp = (e) => {
    const start = pointer.current;
    pointer.current = null;
    if (!start) return;
    const dx = e.clientX - start.x;
    const dy = e.clientY - start.y;
    if (Math.abs(dx) > SWIPE_PX && Math.abs(dx) > Math.abs(dy) * 1.5) go(dx < 0 ? 1 : -1);
  };

  const share = async () => {
    track('card_share', { card: current.id });
    const url = `${window.location.origin}${window.location.pathname}${window.location.search}#${current.id}`;
    try {
      if (navigator.share) await navigator.share({ title: current.title, url });
      else await navigator.clipboard.writeText(url);
    } catch (err) { /* dismissed */ }
  };

  if (!current) return null;
  const firstOfChapter = cards.findIndex((c) => c.chapterIndex === current.chapterIndex);

  return (
    <Box
      role="dialog"
      aria-label={`Match preview: ${chapter.title}`}
      onPointerDown={onPointerDown}
      onPointerUp={onPointerUp}
      sx={{
        position: 'fixed',
        inset: 0,
        zIndex: 1250, // above the app bars (1100), below sheets (1300)
        bgcolor: colors.bg,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        pt: 'env(safe-area-inset-top, 0px)',
        pb: 'env(safe-area-inset-bottom, 0px)',
        touchAction: 'pan-y',
        userSelect: 'none',
      }}
    >
      {/* Progress segments for this chapter, and where we are. Outside the share crop. */}
      <Box sx={{ width, height: STORY_TOP, pt: 1, flexShrink: 0 }}>
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          {chapter.cards.map((c, i) => (
            <Box
              key={c.id}
              sx={{
                flex: 1,
                height: 3,
                borderRadius: 2,
                bgcolor: i <= current.indexInChapter ? colors.accent : colors.borderStrong,
              }}
            />
          ))}
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 0.75 }}>
          <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, letterSpacing: '0.08em', color: colors.accent, textTransform: 'uppercase' }}>
            {chapter.title}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, minWidth: 0 }}>
            <Typography noWrap sx={{ fontSize: 12, color: colors.textLo }}>{fixtureLabel}</Typography>
            {onClose && (
              <IconButton aria-label="Close story" onClick={onClose} data-story-noswipe sx={{ width: 36, height: 36, color: colors.textLo }}>
                <CloseRoundedIcon fontSize="small" />
              </IconButton>
            )}
          </Box>
        </Box>
      </Box>

      {/* The card, with edge tap zones. The middle stays free for chart taps. */}
      <Box sx={{ position: 'relative', width, height, flexShrink: 0 }}>
        {cards.map((card, i) => (Math.abs(i - index) <= 1 ? (
          <Box key={card.id} sx={{ position: 'absolute', inset: 0, visibility: i === index ? 'visible' : 'hidden' }} aria-hidden={i !== index}>
            <StoryCard card={card} width={width} height={height} />
          </Box>
        ) : null))}
        <Box
          component="button"
          aria-label="Previous card"
          onClick={() => go(-1)}
          disabled={index === 0}
          sx={{ position: 'absolute', left: 0, top: 64, bottom: 64, width: '18%', bgcolor: 'transparent', border: 0, p: 0, cursor: index === 0 ? 'default' : 'w-resize' }}
        />
        <Box
          component="button"
          aria-label="Next card"
          onClick={() => go(1)}
          disabled={index === cards.length - 1}
          sx={{ position: 'absolute', right: 0, top: 64, bottom: 64, width: '18%', bgcolor: 'transparent', border: 0, p: 0, cursor: index === cards.length - 1 ? 'default' : 'e-resize' }}
        />
      </Box>

      {/* Actions: outside the share crop. */}
      <Box data-story-noswipe sx={{ width, height: STORY_BOTTOM, flexShrink: 0, display: 'flex', alignItems: 'center', gap: 1, pr: 7 }}>
        {current.queryUrl && (
          <Button
            href={current.queryUrl}
            startIcon={<TableChartOutlinedIcon />}
            sx={{ minHeight: 40, color: colors.textMed, textTransform: 'none', fontSize: 14 }}
          >
            Open in query builder
          </Button>
        )}
        <Button onClick={share} startIcon={<IosShareRoundedIcon />} sx={{ minHeight: 40, color: colors.textMed, textTransform: 'none', fontSize: 14 }}>
          Share
        </Button>
        <Typography sx={{ ml: 'auto', fontSize: 12, color: colors.textFaint, fontFamily: fonts.mono }}>
          {index - firstOfChapter + 1}/{chapter.cards.length}
        </Typography>
      </Box>

      <LogoMenu
        open={menuOpen}
        onOpen={() => setMenuOpen(true)}
        onClose={() => setMenuOpen(false)}
        chapters={chapters}
        currentChapter={current.chapterIndex}
        onJump={(chapterIndex) => {
          wanted.current = null;
          setCurrentId(cards.find((c) => c.chapterIndex === chapterIndex)?.id || null);
          setMenuOpen(false);
        }}
        onSettings={onSettings ? () => { setMenuOpen(false); onSettings(); } : undefined}
        onClassic={onClassic ? () => { setMenuOpen(false); onClassic(); } : undefined}
      />
    </Box>
  );
};

export default StoryViewer;
