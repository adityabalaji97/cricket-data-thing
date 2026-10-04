import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import KeyboardArrowDownRoundedIcon from '@mui/icons-material/KeyboardArrowDownRounded';
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

/** Cards per chapter in the sideways sequence; the rest of a chapter sits below, scrolling down. */
export const FEATURED_PER_CHAPTER = 4;

/** The sideways sequence: each chapter's featured cards (cards arrive ranked), in chapter order. */
export const flattenChapters = (chapters) =>
  chapters.flatMap((chapter, chapterIndex) =>
    chapter.cards.slice(0, FEATURED_PER_CHAPTER).map((card, indexInChapter) => ({ ...card, chapterIndex, indexInChapter })));

/** Cards below the featured ones, by chapter index. */
const extrasOf = (chapter) => (chapter?.cards || []).slice(FEATURED_PER_CHAPTER);

const hashCardId = () => (window.location.hash || '').replace(/^#/, '') || null;

/**
 * Story-style preview: one card per screen, chapters with progress segments, tap the left/right
 * edge or swipe sideways to move, arrow keys on a keyboard, no auto-advance. The middle of the
 * card is left to the chart (its taps open detail sheets). Covers the app's own top and bottom
 * bars while open; the logo at the end of the action row opens the chapter index and settings.
 *
 * Sideways runs through each chapter's FEATURED_PER_CHAPTER most distinctive cards; the rest of
 * the chapter sits below the current card, each a full card, for whoever scrolls down.
 *
 * Only the current card, its neighbours and the current chapter's extra cards are mounted (CARTA
 * Timely). Each card has its own URL hash, so a shared link opens on that card.
 */
const StoryViewer = ({ chapters, fixtureLabel, startCardId, onClose, onSettings, onClassic }) => {
  const cards = useMemo(() => flattenChapters(chapters), [chapters]);
  // An extra card's link opens its chapter's first card and scrolls down to it.
  const ownerOf = useMemo(() => {
    const owners = {};
    chapters.forEach((chapter) => {
      extrasOf(chapter).forEach((extra) => { owners[extra.id] = chapter.cards[0]?.id; });
    });
    return owners;
  }, [chapters]);
  const resolve = useCallback((id) => (cards.some((c) => c.id === id) ? id : ownerOf[id] || null), [cards, ownerOf]);
  const scrollRef = useRef(null);
  const [scrollTo, setScrollTo] = useState(null);
  // The card asked for (deep link or grid click). Cards arrive as their data loads, so a card
  // that is not there yet is remembered and opened when it appears -- unless the reader has
  // already moved on.
  //
  // Position is tracked by card id, not index: cards arriving later can be inserted ahead of the
  // one on screen, and an index would then point at a different card.
  const wanted = useRef(startCardId || hashCardId());
  const [currentId, setCurrentId] = useState(() => resolve(wanted.current));
  useEffect(() => {
    const target = wanted.current && resolve(wanted.current);
    if (target) {
      if (target !== wanted.current) setScrollTo(wanted.current);
      setCurrentId(target);
      wanted.current = null;
    }
  }, [resolve]);
  const found = cards.findIndex((c) => c.id === currentId);
  const index = found >= 0 ? found : 0;
  const [menuOpen, setMenuOpen] = useState(false);
  const { width, height } = useStoryCoreSize();
  const pointer = useRef(null);

  const current = cards[index];
  const chapter = chapters[current?.chapterIndex ?? 0];
  const extras = extrasOf(chapter);

  // A new card starts at the top; a link to an extra card scrolls down to it.
  useEffect(() => {
    const box = scrollRef.current;
    if (!box) return;
    const target = scrollTo && document.getElementById(`story-extra-${scrollTo}`);
    if (target && target.scrollIntoView) target.scrollIntoView({ block: 'start' });
    else box.scrollTop = 0;
    setScrollTo(null);
  }, [currentId]); // eslint-disable-line react-hooks/exhaustive-deps

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

  const share = async (card) => {
    track('card_share', { card: card.id });
    const url = `${window.location.origin}${window.location.pathname}${window.location.search}#${card.id}`;
    try {
      if (navigator.share) await navigator.share({ title: card.title, url });
      else await navigator.clipboard.writeText(url);
    } catch (err) { /* dismissed */ }
  };

  if (!current) return null;

  return (
    <Box
      ref={scrollRef}
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
        // Top-aligned: spare height on tall phones goes below the card, to the chapter's extras.
        justifyContent: 'flex-start',
        overflowY: 'auto',
        overscrollBehavior: 'contain',
        pt: 'env(safe-area-inset-top, 0px)',
        pb: 'env(safe-area-inset-bottom, 0px)',
        touchAction: 'pan-y',
        userSelect: 'none',
      }}
    >
      {/* One progress bar for the whole story: a block per chapter (wider gaps between chapters),
          a segment per card. Outside the share crop. */}
      <Box sx={{ width, height: STORY_TOP, pt: 1, flexShrink: 0, position: 'sticky', top: 0, zIndex: 1, bgcolor: colors.bg }}>
        <Box sx={{ display: 'flex', gap: 1 }} aria-label={`Card ${index + 1} of ${cards.length}`}>
          {chapters.map((ch, ci) => (
            <Box key={ch.id} sx={{ flex: ch.cards.length, display: 'flex', gap: '2px' }}>
              {ch.cards.map((c) => {
                const at = cards.findIndex((x) => x.id === c.id);
                return (
                  <Box
                    key={c.id}
                    sx={{ flex: 1, height: 3, borderRadius: 2, bgcolor: at <= index ? colors.accent : colors.borderStrong }}
                  />
                );
              })}
            </Box>
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

      {/* One row, outside the share crop: Data and Share, then the logo (chapters, settings). */}
      <ActionRow card={current} width={width} onShare={share}>
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
      </ActionRow>

      {extras.length > 0 && (
        <>
          <Box sx={{ width, display: 'flex', alignItems: 'center', gap: 0.5, color: colors.textLo, pb: 2 }}>
            <KeyboardArrowDownRoundedIcon fontSize="small" />
            <Typography sx={{ fontSize: 13, color: colors.textLo }}>
              More in this chapter ({extras.length})
            </Typography>
          </Box>
          {extras.map((card) => (
            <Box key={card.id} id={`story-extra-${card.id}`} sx={{ width, flexShrink: 0, scrollMarginTop: `${STORY_TOP}px` }}>
              <Box sx={{ width, height, position: 'relative' }}>
                <StoryCard card={card} width={width} height={height} />
              </Box>
              <ActionRow card={card} width={width} onShare={share} />
            </Box>
          ))}
        </>
      )}
    </Box>
  );
};

/** Data and Share for a card, outside its share crop; `children` (the logo) sits at the end. */
const ActionRow = ({ card, width, onShare, children }) => (
  <Box data-story-noswipe sx={{ width, height: STORY_BOTTOM, flexShrink: 0, display: 'flex', alignItems: 'center', gap: 1 }}>
    {card.queryUrl && (
      <Button
        href={card.queryUrl}
        startIcon={<TableChartOutlinedIcon />}
        aria-label="See the data in the query builder"
        sx={{ minHeight: 40, color: colors.textMed, textTransform: 'none', fontSize: 14 }}
      >
        Data
      </Button>
    )}
    <Button onClick={() => onShare(card)} startIcon={<IosShareRoundedIcon />} sx={{ minHeight: 40, color: colors.textMed, textTransform: 'none', fontSize: 14 }}>
      Share
    </Button>
    <Box sx={{ ml: 'auto' }} />
    {children}
  </Box>
);

export default StoryViewer;
