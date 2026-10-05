import React from 'react';
import { Box, ButtonBase, Portal, Typography } from '@mui/material';
import TuneRoundedIcon from '@mui/icons-material/TuneRounded';
import ViewAgendaOutlinedIcon from '@mui/icons-material/ViewAgendaOutlined';
import { MOBILE_NAV_HEIGHT } from '../nav/navMetrics';
import useIsMobile from '../../hooks/useIsMobile';
import { colors } from '../../theme/hindsightDark';

const Row = ({ onClick, active, icon, children }) => (
  <ButtonBase
    onClick={onClick}
    sx={{
      width: '100%',
      minHeight: 48,
      justifyContent: 'flex-start',
      gap: 1.5,
      px: 1.5,
      borderRadius: 2,
      bgcolor: active ? colors.accentSoft : 'transparent',
      color: active ? colors.accent : colors.textHi,
      fontSize: 16,
    }}
  >
    {icon}
    {children}
  </ButtonBase>
);

/**
 * The story's menu: the logo at the end of the action row. A tap brings back the app's own top and
 * bottom bars (the viewer drops beneath them, see StoryViewer `menuOpen`) so any page is a tap
 * away, with the chapter index, preview settings and the classic page in a panel just above the
 * bottom bar. Tapping the dimmed story, or the logo again, puts the story back on top.
 *
 * Panel and backdrop render in a portal: the lowered viewer is its own stacking context, and the
 * panel has to sit above the app bars (zIndex appBar 1100) while the backdrop sits below them.
 */
const LogoMenu = ({ open, onOpen, onClose, chapters, currentChapter, onJump, onSettings, onClassic }) => {
  const { isMobile } = useIsMobile();
  // Phones have the app's bottom bar (MobileBottomNav); the panel sits just above it.
  const bottom = isMobile ? `calc(${MOBILE_NAV_HEIGHT + 10}px + env(safe-area-inset-bottom, 0px))` : 16;
  return (
    <>
      <ButtonBase
        aria-label={open ? 'Back to the story' : 'Menu, chapters and settings'}
        aria-expanded={open}
        onClick={open ? onClose : onOpen}
        data-story-noswipe
        sx={{
          width: 44,
          height: 44,
          flexShrink: 0,
          borderRadius: '50%',
          bgcolor: colors.surface2,
          border: `1px solid ${open ? colors.accent : colors.borderStrong}`,
        }}
      >
        <Box component="img" src="/cricket-icon.svg" alt="" sx={{ width: 26, height: 26 }} />
      </ButtonBase>
      {open && (
        <Portal>
          <Box
            role="presentation"
            onClick={onClose}
            sx={{ position: 'fixed', inset: 0, zIndex: 1095, bgcolor: 'rgba(5,7,10,0.6)' }}
          />
          <Box
            role="dialog"
            aria-label="Match preview menu"
            sx={{
              position: 'fixed', left: 12, right: 12, bottom, zIndex: 1101, mx: 'auto', maxWidth: 460,
              maxHeight: '60vh', overflowY: 'auto', p: 1.5, borderRadius: '18px',
              bgcolor: colors.surface1, border: `1px solid ${colors.borderStrong}`, boxShadow: '0 12px 40px rgba(0,0,0,0.5)',
            }}
          >
            <Typography sx={{ fontSize: 12, color: colors.textLo, mb: 1, px: 1.5, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Chapters
            </Typography>
            <Box sx={{ display: 'grid', gap: 0.25 }}>
              {chapters.map((chapter, i) => (
                <Row key={chapter.id} active={i === currentChapter} onClick={() => onJump(i)}>
                  <Box component="span" sx={{ width: 22, color: colors.textFaint, fontSize: 14 }}>{i + 1}</Box>
                  {chapter.title}
                  <Box component="span" sx={{ ml: 'auto', fontSize: 13, color: colors.textFaint }}>{chapter.cards.length}</Box>
                </Row>
              ))}
            </Box>
            {(onSettings || onClassic) && (
              <Box sx={{ display: 'grid', gap: 0.25, mt: 1, pt: 1, borderTop: `1px solid ${colors.border}` }}>
                {onSettings && <Row onClick={onSettings} icon={<TuneRoundedIcon fontSize="small" />}>Preview settings</Row>}
                {onClassic && <Row onClick={onClassic} icon={<ViewAgendaOutlinedIcon fontSize="small" />}>Classic page</Row>}
              </Box>
            )}
          </Box>
        </Portal>
      )}
    </>
  );
};

export default LogoMenu;
