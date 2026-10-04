import React from 'react';
import { Box, ButtonBase, Typography } from '@mui/material';
import TuneRoundedIcon from '@mui/icons-material/TuneRounded';
import ViewAgendaOutlinedIcon from '@mui/icons-material/ViewAgendaOutlined';
import DetailSheet from '../ui/DetailSheet';
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
 * The story's only persistent control: the logo in the bottom-right corner, clear of the card's
 * core. Opens the chapter index, the preview settings and the way back to the classic page.
 */
const LogoMenu = ({ open, onOpen, onClose, chapters, currentChapter, onJump, onSettings, onClassic }) => (
  <>
    <ButtonBase
      aria-label="Chapters and settings"
      onClick={onOpen}
      data-story-noswipe
      sx={{
        position: 'fixed',
        right: 12,
        bottom: 'calc(14px + env(safe-area-inset-bottom, 0px))',
        width: 48,
        height: 48,
        borderRadius: '50%',
        bgcolor: colors.surface2,
        border: `1px solid ${colors.borderStrong}`,
        zIndex: 1251,
      }}
    >
      <Box component="img" src="/cricket-icon.svg" alt="" sx={{ width: 26, height: 26 }} />
    </ButtonBase>
    <DetailSheet open={open} onClose={onClose} title="Match preview">
      <Typography sx={{ fontSize: 12, color: colors.textLo, mb: 1, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        Chapters
      </Typography>
      <Box sx={{ display: 'grid', gap: 0.5 }}>
        {chapters.map((chapter, i) => (
          <Row key={chapter.id} active={i === currentChapter} onClick={() => onJump(i)}>
            <Box component="span" sx={{ width: 22, color: colors.textFaint, fontSize: 14 }}>{i + 1}</Box>
            {chapter.title}
            <Box component="span" sx={{ ml: 'auto', fontSize: 13, color: colors.textFaint }}>{chapter.cards.length}</Box>
          </Row>
        ))}
      </Box>
      {(onSettings || onClassic) && (
        <Box sx={{ display: 'grid', gap: 0.5, mt: 2, pt: 1.5, borderTop: `1px solid ${colors.border}` }}>
          {onSettings && <Row onClick={onSettings} icon={<TuneRoundedIcon fontSize="small" />}>Preview settings</Row>}
          {onClassic && <Row onClick={onClassic} icon={<ViewAgendaOutlinedIcon fontSize="small" />}>Classic page</Row>}
        </Box>
      )}
    </DetailSheet>
  </>
);

export default LogoMenu;
