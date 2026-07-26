/**
 * Header control for choosing the cricket format.
 *
 * Four flat entries rather than separate format and gender toggles: the product of the two would
 * advertise combinations that do not exist (there is no women's Test data here), and a flat list
 * matches how people actually think about it.
 *
 * Formats whose data has not been loaded come back from the API as `available: false`. They are
 * shown disabled rather than hidden, so it is clear what is coming rather than looking like the
 * app only ever does one format.
 */

import React, { useState } from 'react';
import { Box, Button, Menu, MenuItem, Typography } from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import { colors, fonts } from '../theme/hindsightDark';
import { useFormat } from '../context/FormatContext';

const FormatSwitcher = ({ isMobile = false }) => {
  const { formats, active, selectFormat } = useFormat();
  const [anchorEl, setAnchorEl] = useState(null);

  // Nothing to switch between until a second format has data.
  if (!active || formats.length < 2) return null;

  const close = () => setAnchorEl(null);

  return (
    <>
      <Button
        onClick={(event) => setAnchorEl(event.currentTarget)}
        endIcon={<KeyboardArrowDownIcon sx={{ fontSize: 18 }} />}
        sx={{
          color: colors.textMed,
          fontFamily: fonts.mono,
          fontSize: isMobile ? 11 : 12,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          border: `1px solid ${colors.border}`,
          borderRadius: '8px',
          px: isMobile ? 1 : 1.5,
          py: 0.5,
          minWidth: 0,
          '&:hover': { borderColor: colors.borderStrong, color: colors.textHi },
        }}
      >
        {active.label}
      </Button>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={close}
        slotProps={{
          paper: {
            sx: {
              bgcolor: colors.surface2,
              border: `1px solid ${colors.border}`,
              borderRadius: '12px',
              mt: 0.5,
            },
          },
        }}
      >
        {formats.map((format) => (
          <MenuItem
            key={format.slug}
            disabled={!format.available}
            selected={format.slug === active.slug}
            onClick={() => {
              selectFormat(format.slug);
              close();
            }}
            sx={{
              fontFamily: fonts.body,
              fontSize: 14,
              color: colors.textHi,
              '&.Mui-selected': { bgcolor: colors.accentSoft },
              '&.Mui-disabled': { opacity: 1, color: colors.textGhost },
              gap: 2,
              justifyContent: 'space-between',
            }}
          >
            {format.label}
            {!format.available && (
              <Typography
                component="span"
                sx={{
                  fontFamily: fonts.mono,
                  fontSize: 10,
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase',
                  color: colors.textGhost,
                }}
              >
                soon
              </Typography>
            )}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
};

export default FormatSwitcher;
