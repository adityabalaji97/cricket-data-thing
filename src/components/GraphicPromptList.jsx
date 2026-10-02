import React, { useState } from 'react';
import { Box, ButtonBase, Typography } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { GRAPHIC_EXAMPLE_GROUPS } from '../utils/graphicExamples';
import { colors as hs, fonts } from '../theme/hindsightDark';

/**
 * Prompts to try, one collapsible group per chart type. Used by /graphics (tapping runs it) and
 * the admin idea box (tapping fills the box). onPick(prompt, format).
 */
const GraphicPromptList = ({ onPick, title = 'Prompts to try, by chart type' }) => {
  const [open, setOpen] = useState(null);
  return (
    <Box>
      <Typography sx={{ fontSize: 13, color: hs.textLo, mb: 1 }}>{title}</Typography>
      {GRAPHIC_EXAMPLE_GROUPS.map((g) => {
        const isOpen = open === g.form;
        return (
          <Box key={g.form} sx={{ border: `1px solid ${hs.border}`, borderRadius: 2, mb: 0.75, bgcolor: hs.surface1, overflow: 'hidden' }}>
            <ButtonBase onClick={() => setOpen(isOpen ? null : g.form)} aria-expanded={isOpen}
              sx={{ width: '100%', minHeight: 48, px: 1.5, justifyContent: 'flex-start', gap: 1, textAlign: 'left' }}>
              <Box sx={{ flex: 1 }}>
                <Typography component="span" sx={{ display: 'block', fontSize: 14, fontWeight: 600, color: hs.textHi }}>{g.form}</Typography>
                <Typography component="span" sx={{ display: 'block', fontSize: 12, color: hs.textLo }}>{g.hint}</Typography>
              </Box>
              <ExpandMoreIcon sx={{ color: hs.textLo, transition: 'transform 160ms', transform: isOpen ? 'rotate(180deg)' : 'none' }} />
            </ButtonBase>
            {isOpen && (
              <Box sx={{ px: 1, pb: 1 }}>
                {g.prompts.map(([prompt, fmt]) => (
                  <ButtonBase key={prompt} onClick={() => onPick(prompt, fmt)}
                    sx={{ display: 'block', width: '100%', textAlign: 'left', borderRadius: 1.5, px: 1, py: 1, minHeight: 40,
                      color: hs.textMed, fontSize: 14, fontFamily: fonts.body, lineHeight: 1.35, '&:hover': { bgcolor: hs.surface2, color: hs.accent } }}>
                    {prompt} <Typography component="span" sx={{ fontSize: 11, color: hs.textFaint }}>· {fmt}</Typography>
                  </ButtonBase>
                ))}
              </Box>
            )}
          </Box>
        );
      })}
    </Box>
  );
};

export default GraphicPromptList;
