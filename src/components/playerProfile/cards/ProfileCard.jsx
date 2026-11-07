import React from 'react';
import { Box } from '@mui/material';
import { colors, fonts } from '../../../theme/hindsightDark';
import ShareButton from '../../ui/ShareButton';

// One card on the player profile (PROFILE_SIMPLIFY_PLAN.md P1): its name as the title, a share button that links to
// the card on its own, one picture, and a short note only where it adds something ("15+ balls a cell"). No site name,
// link or data credit on a card: the logo carries the brand and the page foot carries the credit (user, 3 Nov 2026).
// Every line fits one line at phone width (390px): notes and labels never wrap. `action`: an icon beside share (a card's
// own filter), drawn only on the cards that have one.
const ProfileCard = ({ id, title, player, note, action, children }) => {
  const url = typeof window !== 'undefined' ? `${window.location.origin}${window.location.pathname}${window.location.search}#${id}` : undefined;
  return (
    <Box component="section" id={id} aria-label={title}
      sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.borderStrong}`, borderRadius: '18px', px: 1.75, pt: 1.25, pb: 1.5,
        scrollMarginTop: '72px', display: 'flex', flexDirection: 'column', gap: 1 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box component="h2" sx={{ m: 0, fontFamily: fonts.display, fontWeight: 700, fontSize: 19, lineHeight: 1.2, flex: 1, minWidth: 0, whiteSpace: 'nowrap' }}>
          {title}
        </Box>
        {action}
        <ShareButton variant="icon" kind="player-card" url={url} title={player ? `${player}: ${title.toLowerCase()} on Hindsight` : undefined}
          sx={{ color: colors.textMed, mr: -1 }} />
      </Box>
      {children}
      {note && (
        <Box sx={{ fontSize: 11.5, color: colors.textLo, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{note}</Box>
      )}
    </Box>
  );
};

export default ProfileCard;
