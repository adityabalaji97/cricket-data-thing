import React, { useEffect, useState } from 'react';
import { Box, Drawer, TextField } from '@mui/material';
import { colors, fonts } from '../../../theme/hindsightDark';

// The filters behind the profile's filters icon (PROFILE_SIMPLIFY_PLAN.md P1): one window and scope for the whole
// page (the verdict, its peers, plays like and the role cards). Format, period (recent, career or custom dates) and
// strong sides or every match.

const Seg = ({ label, options, value, onChange, light }) => (
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
    <Box sx={{ fontFamily: fonts.mono, fontSize: 10.5, letterSpacing: '0.12em', textTransform: 'uppercase', color: colors.textLo }}>{label}</Box>
    <Box role="radiogroup" aria-label={label} sx={{ display: 'inline-flex', alignSelf: 'flex-start', border: `1px solid ${colors.borderStrong}`, borderRadius: '999px', p: '2px' }}>
      {options.map(([key, name]) => (
        <Box key={key} component="button" type="button" role="radio" aria-checked={key === value} onClick={() => onChange(key)}
          sx={{
            all: 'unset', cursor: 'pointer', fontFamily: fonts.display, fontWeight: 600, fontSize: 14, px: 1.5, py: '4px', borderRadius: '999px',
            bgcolor: key === value ? (light ? colors.textHi : colors.accent) : 'transparent', color: key === value ? colors.bg : colors.textMed,
            '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 },
          }}>
          {name}
        </Box>
      ))}
    </Box>
  </Box>
);

const ProfileFilters = ({ open, onClose, value, onApply }) => {
  const [draft, setDraft] = useState(value);
  useEffect(() => { if (open) setDraft(value); }, [open, value]);
  const set = (patch) => setDraft((d) => ({ ...d, ...patch }));
  const customOk = draft.period !== 'custom' || (draft.start && (!draft.end || draft.end >= draft.start));

  return (
    <Drawer anchor="bottom" open={open} onClose={onClose}
      PaperProps={{ sx: { bgcolor: colors.surface2, color: colors.textHi, borderTopLeftRadius: 20, borderTopRightRadius: 20, maxWidth: 560, mx: 'auto', px: 2, pt: 1.5, pb: 'calc(16px + env(safe-area-inset-bottom, 0px))' } }}>
      <Box sx={{ width: 40, height: 4, borderRadius: 2, bgcolor: colors.borderStrong, alignSelf: 'center', mb: 1.5 }} />
      <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 20, mb: 1.5 }}>Filters</Box>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.75 }}>
        <Seg label="Format" value={draft.fmt} onChange={(fmt) => set({ fmt })} options={[['T20', 'T20'], ['ODI', 'ODI']]} />
        <Seg label="Period" light value={draft.period} onChange={(period) => set({ period })}
          options={[['recent', 'Recent'], ['career', 'Career'], ['custom', 'Custom dates']]} />
        {draft.period === 'custom' && (
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            {[['start', 'From'], ['end', 'To']].map(([k, label]) => (
              <TextField key={k} type="date" label={label} size="small" value={draft[k] || ''} InputLabelProps={{ shrink: true }}
                onChange={(e) => set({ [k]: e.target.value })} sx={{ flex: 1 }} />
            ))}
          </Box>
        )}
        <Seg label="Against" light value={draft.scope} onChange={(scope) => set({ scope })}
          options={[['strong', 'Strong sides'], ['all', 'Every match']]} />
        <Box component="button" type="button" disabled={!customOk} onClick={() => { onApply(draft); onClose(); }}
          sx={{
            all: 'unset', cursor: customOk ? 'pointer' : 'default', textAlign: 'center', bgcolor: customOk ? colors.accent : colors.borderStrong,
            color: colors.bg, borderRadius: '999px', py: 1, fontWeight: 600, fontSize: 15, mt: 0.5,
            '&:focus-visible': { outline: `2px solid ${colors.textHi}`, outlineOffset: 2 },
          }}>
          Apply to the whole page
        </Box>
      </Box>
    </Drawer>
  );
};

export default ProfileFilters;
