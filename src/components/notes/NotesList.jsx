import React, { useCallback, useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, Chip, CircularProgress, Typography } from '@mui/material';
import axios from 'axios';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { embedOrigin } from './NoteBody';
import { KIND_LABEL, formatNoteDate } from './noteMarkdown.mjs';

/** /notes: published Hindsight Notes, newest first. Phone-first cards. */
const PAGE = 12;
const FILTERS = [['', 'All'], ['recap', 'Recaps'], ['preview', 'Previews'], ['analysis', 'Analysis'], ['article', 'Articles']];

export const Byline = ({ author, date, sx }) => (
  <Typography component="div" sx={{ fontSize: 13, color: colors.textLo, display: 'flex', alignItems: 'center', gap: 0.75, flexWrap: 'wrap', ...sx }}>
    <span style={{ color: colors.textMed, fontWeight: 600 }}>{author?.name}</span>
    {author?.is_bot && (
      <Box component="span" title="Written by code from Hindsight's numbers"
        sx={{ fontFamily: fonts.mono, fontSize: 10, letterSpacing: '.08em', px: 0.6, py: 0.1, borderRadius: 1, border: `1px solid ${colors.borderStrong}`, color: colors.textLo }}>
        AI
      </Box>
    )}
    {date && <span>· {formatNoteDate(date)}</span>}
  </Typography>
);

export const NoteCard = ({ note, compact = false }) => (
  <Box component={RouterLink} to={`/notes/${note.slug}`}
    sx={{
      display: 'flex', gap: 1.75, textDecoration: 'none', color: 'inherit', p: compact ? 1.5 : 2,
      bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '16px',
      '&:hover': { borderColor: 'rgba(182,242,74,.35)' },
    }}>
    <Box sx={{ minWidth: 0, flex: 1 }}>
      <Typography sx={{ fontFamily: fonts.mono, fontSize: 10.5, letterSpacing: '.12em', textTransform: 'uppercase', color: colors.accent, mb: 0.75 }}>
        {KIND_LABEL[note.kind] || 'Note'}
      </Typography>
      <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, color: colors.textHi, fontSize: compact ? 17 : { xs: 19, md: 21 }, lineHeight: 1.2 }}>
        {note.title}
      </Typography>
      {note.dek && !compact && (
        <Typography sx={{ color: colors.textMed, fontSize: 14.5, mt: 0.75, lineHeight: 1.45 }}>{note.dek}</Typography>
      )}
      <Byline author={note.author} date={note.published_at} sx={{ mt: 1 }} />
    </Box>
    {note.cover && (
      <Box component="img" alt="" loading="lazy" src={`${embedOrigin()}/img/${note.cover}.png?size=square`}
        sx={{ width: compact ? 64 : { xs: 76, md: 110 }, height: compact ? 64 : { xs: 76, md: 110 }, flexShrink: 0, borderRadius: '10px', objectFit: 'cover', bgcolor: colors.surface2, alignSelf: 'center' }} />
    )}
  </Box>
);

const NotesList = () => {
  const [kind, setKind] = useState('');
  const [notes, setNotes] = useState(null);
  const [more, setMore] = useState(false);
  const [error, setError] = useState(false);

  const load = useCallback(async (offset) => {
    try {
      const { data } = await axios.get(`${config.API_URL}/notes`, { params: { kind: kind || undefined, limit: PAGE, offset } });
      setNotes((prev) => (offset ? [...(prev || []), ...data.notes] : data.notes));
      setMore(data.notes.length === PAGE);
      setError(false);
    } catch {
      setError(true);
      setNotes((prev) => prev || []);
    }
  }, [kind]);

  useEffect(() => { setNotes(null); load(0); }, [load]);
  useEffect(() => { document.title = 'Notes | Hindsight'; }, []);

  return (
    <Box sx={{ maxWidth: 720, mx: 'auto', pb: 4 }}>
      <Typography sx={{ color: colors.textMed, fontSize: 15, mb: 2, lineHeight: 1.5 }}>
        Match recaps, previews and analysis from ball-by-ball data. Every chart is live data, frozen at the moment of writing.
      </Typography>
      <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mb: 2 }}>
        {FILTERS.map(([value, label]) => (
          <Chip key={label} label={label} onClick={() => setKind(value)}
            sx={{ fontWeight: 600, bgcolor: kind === value ? colors.accent : colors.surface2, color: kind === value ? colors.bg : colors.textMed, '&:hover': { bgcolor: kind === value ? colors.accentHover : colors.surface3 } }} />
        ))}
      </Box>
      {notes === null && <CircularProgress size={22} sx={{ color: colors.accent }} />}
      {notes && notes.length === 0 && (
        <Typography sx={{ color: colors.textLo, py: 4 }}>
          {error ? 'Notes could not be loaded. Try again in a moment.' : 'Nothing here yet.'}
        </Typography>
      )}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {(notes || []).map((n) => <NoteCard key={n.id} note={n} />)}
      </Box>
      {more && (
        <Button onClick={() => load(notes.length)} sx={{ mt: 2, color: colors.accent, fontWeight: 700 }}>Load more</Button>
      )}
    </Box>
  );
};

export default NotesList;
