import React from 'react';
import { Box, Dialog, Drawer, IconButton, Typography } from '@mui/material';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import { colors, fonts } from '../../theme/hindsightDark';
import useIsMobile from '../../hooks/useIsMobile';

/**
 * "Tap for the full numbers." The replacement for hover-only detail.
 *
 * Matrix cells, form chips, wagon-wheel zones and table rows used to keep their full stats in a
 * hover tooltip (or an SVG <title>, which touch never shows). Tap one and this opens: a bottom
 * sheet on phones, a small dialog on desktop.
 *
 * Pass `rows` ([{ label, value, hint }]) for the common stat list, `children` for anything else,
 * or both (children render under the rows).
 */
const DetailSheet = ({ open, onClose, title, subtitle, rows = [], footer, children }) => {
  const { isMobile } = useIsMobile();

  const body = (
    <Box sx={{ px: 2.5, pt: isMobile ? 1 : 2.5, pb: 'calc(20px + env(safe-area-inset-bottom, 0px))' }}>
      {isMobile && (
        <Box sx={{ width: 40, height: 4, borderRadius: 2, bgcolor: colors.borderStrong, mx: 'auto', mb: 1.5 }} />
      )}
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: rows.length || children ? 1.5 : 0 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography sx={{ fontWeight: 700, fontSize: 17, color: colors.textHi }}>{title}</Typography>
          {subtitle && (
            <Typography sx={{ fontSize: 13, color: colors.textLo, mt: 0.25 }}>{subtitle}</Typography>
          )}
        </Box>
        <IconButton onClick={onClose} aria-label="Close" sx={{ mt: -0.5, mr: -1, width: 40, height: 40 }}>
          <CloseRoundedIcon />
        </IconButton>
      </Box>
      {rows.length > 0 && (
        <Box
          component="dl"
          sx={{
            m: 0,
            display: 'grid',
            gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
            gap: 1,
          }}
        >
          {rows.map((row) => (
            <Box
              key={row.label}
              sx={{ bgcolor: colors.surface2, border: `1px solid ${colors.border}`, borderRadius: 2, px: 1.5, py: 1 }}
            >
              <Typography component="dt" sx={{ fontSize: 12, color: colors.textLo }}>{row.label}</Typography>
              <Typography
                component="dd"
                sx={{ m: 0, fontFamily: fonts.mono, fontSize: 17, fontWeight: 600, color: colors.textHi }}
              >
                {row.value ?? '–'}
              </Typography>
              {row.hint && (
                <Typography sx={{ fontSize: 12, color: colors.textFaint }}>{row.hint}</Typography>
              )}
            </Box>
          ))}
        </Box>
      )}
      {children && <Box sx={{ mt: rows.length ? 2 : 0 }}>{children}</Box>}
      {footer && <Box sx={{ mt: 2 }}>{footer}</Box>}
    </Box>
  );

  if (isMobile) {
    return (
      <Drawer
        anchor="bottom"
        open={open}
        onClose={onClose}
        PaperProps={{
          sx: {
            bgcolor: colors.surface1,
            backgroundImage: 'none',
            borderTopLeftRadius: 16,
            borderTopRightRadius: 16,
            maxHeight: '85vh',
          },
        }}
      >
        {body}
      </Drawer>
    );
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{ sx: { bgcolor: colors.surface1, backgroundImage: 'none', borderRadius: 3 } }}
    >
      {body}
    </Dialog>
  );
};

export default DetailSheet;
