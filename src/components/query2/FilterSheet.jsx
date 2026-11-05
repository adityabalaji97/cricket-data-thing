import React, { useEffect, useMemo, useState } from 'react';
import { Autocomplete, Box, Drawer, TextField } from '@mui/material';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import { colors, fonts } from '../../theme/hindsightDark';
import { GROUP_WORDS, KIND_WORDS, LENGTH_WORDS, LINE_WORDS, ZONE_WORDS } from './qbWords';

// "Add filter" (QUERY_BUILDER_PLAN.md Q3): every filter the query builder has, in five plain groups, with a search
// box. Tapping a filter opens its control in place; "Show results" applies them all and runs the query.

const multi = (key, label, optionsKey, words) => ({ key, label, type: 'multi', optionsKey, words });
const GROUPS = [
  ['Who', [multi('batters', 'Batters', 'batters'), multi('bowlers', 'Bowlers', 'bowlers'),
    multi('batting_teams', 'Batting team', 'batting_teams'), multi('bowling_teams', 'Bowling team', 'bowling_teams')]],
  ['Where and when', [{ key: 'dates', label: 'Dates', type: 'dates' }, { key: 'venue', label: 'Venue', type: 'single', optionsKey: 'venues' },
    multi('leagues', 'Competitions', 'competitions'), { key: 'include_international', label: 'Internationals', type: 'toggle' }]],
  ['Match situation', [{ key: 'innings', label: 'Innings', type: 'choice', choices: [['', 'Either'], ['1', '1st'], ['2', '2nd']] },
    { key: 'is_chase', label: 'Chasing', type: 'choice', choices: [['', 'Either'], ['true', 'Chasing'], ['false', 'Setting']] },
    multi('match_outcome', 'Result', 'match_outcome_options', (v) => ({ win: 'Won', loss: 'Lost', tie: 'Tied', no_result: 'No result' }[v] || v)),
    multi('toss_decision', 'Toss', 'toss_decision_options', (v) => `Chose to ${v}`)]],
  ['The ball', [multi('bowl_kind', 'Pace or spin', 'bowl_kind_options', (v) => KIND_WORDS[v] || v),
    multi('bowl_style', 'Bowling type', 'bowl_style_options'),
    multi('line', 'Line', 'line_options', (v) => LINE_WORDS[v] || v), multi('length', 'Length', 'length_options', (v) => LENGTH_WORDS[v] || v),
    multi('shot_family', 'Shot', 'shot_family_options'), { key: 'control', label: 'Control', type: 'choice', choices: [['', 'All balls'], ['1', 'In control'], ['0', 'False shots']] },
    multi('wagon_zone', 'Scoring zone', 'wagon_zone_all', (v) => ZONE_WORDS[v] || `Zone ${v}`),
    { key: 'bat_hand', label: 'Batting hand', type: 'choice', choices: [['', 'Both'], ['RHB', 'Right'], ['LHB', 'Left']] }]],
  ['Show', [{ key: 'group_by', label: 'Group by', type: 'groupby' }, { key: 'min_balls', label: 'Minimum balls', type: 'number' }]],
];
const GROUPABLE = ['year', 'season', 'phase', 'bowl_kind', 'bowl_style', 'line', 'length', 'wagon_zone', 'shot', 'venue', 'batter', 'bowler',
  'batting_team', 'bowling_team', 'competition', 'innings', 'bat_hand', 'dismissal', 'partnership', 'match_id'];

const Choice = ({ choices, value, onChange }) => (
  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
    {choices.map(([v, l]) => {
      const on = String(value ?? '') === v;
      return (
        <Box key={v} component="button" type="button" onClick={() => onChange(v)}
          sx={{ all: 'unset', cursor: 'pointer', border: `1px solid ${on ? colors.accent : colors.borderStrong}`, color: on ? colors.accent : colors.textMed,
            borderRadius: '999px', px: 1.5, py: 0.5, fontSize: 13.5, '&:focus-visible': { outline: `2px solid ${colors.accent}` } }}>{l}</Box>
      );
    })}
  </Box>
);

const Control = ({ item, draft, set, options, groupBy, setGroupBy }) => {
  const opts = item.optionsKey === 'wagon_zone_all' ? [1, 2, 3, 4, 5, 6, 7, 8] : (options?.[item.optionsKey] || []).filter((v) => v !== '-' && v !== '');
  const words = item.words || ((v) => (item.key === 'shot_family' ? options?.shot_family_definitions?.[v]?.label || v : String(v)));
  if (item.type === 'multi') {
    return (
      <Autocomplete multiple size="small" options={opts} value={draft[item.key] || []} getOptionLabel={(v) => words(v)}
        onChange={(_, v) => set({ [item.key]: v })} renderInput={(p) => <TextField {...p} placeholder={`Any ${item.label.toLowerCase()}`} />} />
    );
  }
  if (item.type === 'single') {
    return (
      <Autocomplete size="small" options={opts} value={draft[item.key] || null} onChange={(_, v) => set({ [item.key]: v })}
        renderInput={(p) => <TextField {...p} placeholder={`Any ${item.label.toLowerCase()}`} />} />
    );
  }
  if (item.type === 'dates') {
    return (
      <Box sx={{ display: 'flex', gap: 1 }}>
        {[['start_date', 'From'], ['end_date', 'To']].map(([k, l]) => (
          <TextField key={k} type="date" size="small" label={l} InputLabelProps={{ shrink: true }} value={draft[k] || ''}
            onChange={(e) => set({ [k]: e.target.value || null })} sx={{ flex: 1 }} />
        ))}
      </Box>
    );
  }
  if (item.type === 'toggle') {
    return <Choice choices={[['false', 'Leagues only'], ['true', 'Include internationals']]} value={String(Boolean(draft.include_international))}
      onChange={(v) => set({ include_international: v === 'true' })} />;
  }
  if (item.type === 'choice') {
    return <Choice choices={item.choices} value={draft[item.key]} onChange={(v) => set({ [item.key]: v === '' ? null : v })} />;
  }
  if (item.type === 'number') {
    return <TextField type="number" size="small" value={draft.min_balls || ''} placeholder="e.g. 60" onChange={(e) => set({ min_balls: e.target.value ? Number(e.target.value) : null })} />;
  }
  return (
    <Autocomplete multiple size="small" options={GROUPABLE} value={groupBy} getOptionLabel={(v) => GROUP_WORDS[v] || v}
      onChange={(_, v) => setGroupBy(v)} renderInput={(p) => <TextField {...p} placeholder="No grouping: one total" />} />
  );
};

const FilterSheet = ({ open, onClose, filters, groupBy, options, focus, onApply }) => {
  const [draft, setDraft] = useState(filters);
  const [gb, setGb] = useState(groupBy);
  const [openKey, setOpenKey] = useState(null);
  const [search, setSearch] = useState('');
  useEffect(() => {
    if (open) { setDraft(filters); setGb(groupBy); setOpenKey(focus || null); setSearch(''); }
  }, [open, filters, groupBy, focus]);
  const set = (patch) => setDraft((d) => ({ ...d, ...patch }));
  const groups = useMemo(() => {
    const s = search.trim().toLowerCase();
    if (!s) return GROUPS;
    return GROUPS.map(([g, items]) => [g, items.filter((i) => `${i.label} ${g}`.toLowerCase().includes(s))]).filter(([, items]) => items.length);
  }, [search]);
  const isSet = (i) => {
    if (i.key === 'dates') return Boolean(draft.start_date || draft.end_date);
    if (i.key === 'group_by') return gb.length > 0;
    const v = draft[i.key];
    return Array.isArray(v) ? v.length > 0 : v != null && v !== '' && v !== false;
  };

  return (
    <Drawer anchor="bottom" open={open} onClose={onClose}
      PaperProps={{ sx: { bgcolor: colors.surface2, color: colors.textHi, borderTopLeftRadius: 20, borderTopRightRadius: 20, maxWidth: 560, mx: 'auto',
        maxHeight: '88vh', px: 2, pt: 1.25, pb: 'calc(14px + env(safe-area-inset-bottom, 0px))' } }}>
      <Box sx={{ width: 40, height: 4, borderRadius: 2, bgcolor: colors.borderStrong, alignSelf: 'center', mb: 1.25 }} />
      <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 20, mb: 1 }}>Filters</Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, border: `1px solid ${colors.borderStrong}`, borderRadius: '12px', px: 1.25, py: 0.75, mb: 1 }}>
        <SearchRoundedIcon fontSize="small" sx={{ color: colors.textLo }} />
        <Box component="input" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search filters: “yorker”, “chasing”…" aria-label="Search filters"
          sx={{ all: 'unset', flex: 1, fontSize: 14, color: colors.textHi, '&::placeholder': { color: colors.textLo } }} />
      </Box>
      <Box sx={{ overflowY: 'auto', flex: 1, pb: 1 }}>
        {groups.map(([g, items]) => (
          <Box key={g} sx={{ mt: 1.25 }}>
            <Box sx={{ fontFamily: fonts.mono, fontSize: 10.5, letterSpacing: '0.12em', textTransform: 'uppercase', color: colors.textLo, mb: 0.75 }}>{g}</Box>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
              {items.map((i) => (
                <Box key={i.key} component="button" type="button" onClick={() => setOpenKey(openKey === i.key ? null : i.key)}
                  sx={{ all: 'unset', cursor: 'pointer', borderRadius: '999px', px: 1.5, py: 0.5, fontSize: 13.5,
                    border: `1px solid ${openKey === i.key || isSet(i) ? colors.accent : colors.borderStrong}`,
                    color: isSet(i) ? colors.accent : colors.textHi, bgcolor: openKey === i.key ? 'rgba(182,242,74,0.08)' : 'transparent',
                    '&:focus-visible': { outline: `2px solid ${colors.accent}` } }}>
                  {i.label}{isSet(i) ? ' •' : ''}
                </Box>
              ))}
            </Box>
            {items.some((i) => i.key === openKey) && (
              <Box sx={{ mt: 1 }}>
                <Control item={items.find((i) => i.key === openKey)} draft={draft} set={set} options={options} groupBy={gb} setGroupBy={setGb} />
              </Box>
            )}
          </Box>
        ))}
      </Box>
      <Box component="button" type="button" onClick={() => { onApply(draft, gb); onClose(); }}
        sx={{ all: 'unset', cursor: 'pointer', textAlign: 'center', bgcolor: colors.accent, color: colors.bg, borderRadius: '999px', py: 1, fontWeight: 700,
          fontSize: 15, mt: 1, '&:focus-visible': { outline: `2px solid ${colors.textHi}`, outlineOffset: 2 } }}>
        Show results
      </Box>
    </Drawer>
  );
};

export default FilterSheet;
