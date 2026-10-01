import React, { useEffect, useState } from 'react';
import { Link as RouterLink, useParams } from 'react-router-dom';
import { Box, CircularProgress, Typography } from '@mui/material';
import axios from 'axios';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { track } from '../../utils/analytics';
import ShareButton from '../ui/ShareButton';
import NoteBody from './NoteBody';
import { Byline } from './NotesList';
import { KIND_LABEL } from './noteMarkdown.mjs';

/** The article view, shared by /notes/:slug and the admin preview. */
export const NoteArticle = ({ note, preview = false }) => (
  <Box component="article" sx={{ maxWidth: 680, mx: 'auto' }}>
    <Typography sx={{ fontFamily: fonts.mono, fontSize: 11, letterSpacing: '.14em', textTransform: 'uppercase', color: colors.accent, mb: 1 }}>
      {KIND_LABEL[note.kind] || 'Note'}
    </Typography>
    <Typography component="h1" sx={{ fontFamily: fonts.display, fontWeight: 700, color: colors.textHi, fontSize: { xs: 28, md: 38 }, lineHeight: 1.12, overflowWrap: 'anywhere' }}>
      {note.title}
    </Typography>
    {note.dek && (
      <Typography sx={{ color: colors.textMed, fontSize: { xs: 17, md: 19 }, mt: 1.25, lineHeight: 1.45 }}>{note.dek}</Typography>
    )}
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, mt: 2, pb: 2, borderBottom: `1px solid ${colors.border}` }}>
      <Byline author={note.author} date={note.published_at || note.updated_at} />
      {!preview && <ShareButton title={note.title} text={note.dek || note.title} kind="note" variant="icon" sx={{ color: colors.textMed }} />}
    </Box>
    <NoteBody body={note.body_md} charts={note.charts} />
    <Box sx={{ mt: 3, pt: 2, borderTop: `1px solid ${colors.border}`, color: colors.textLo, fontSize: 13.5, lineHeight: 1.55 }}>
      {note.author?.is_bot ? (
        <>Written by <b style={{ color: colors.textMed }}>{note.author.name}</b>, an AI analyst: its sentences are written by code
          from Hindsight's ball-by-ball numbers and reviewed by a person before publishing. Charts are frozen at the time of
          writing; open one to see it live.</>
      ) : (
        <>{note.author?.bio ? `${note.author.name}: ${note.author.bio} ` : ''}Numbers from Hindsight's ball-by-ball data. Charts are frozen at the time of writing; open one to see it live.</>
      )}
      {note.match_id && note.kind !== 'preview' && (
        <Box sx={{ mt: 1.5 }}>
          <RouterLink to={`/scorecard/${note.match_id}`} style={{ color: colors.accent, fontWeight: 600 }}>Full scorecard →</RouterLink>
        </Box>
      )}
    </Box>
  </Box>
);

const NotePage = () => {
  const { slug } = useParams();
  const [note, setNote] = useState(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    let live = true;
    setNote(null);
    setMissing(false);
    axios.get(`${config.API_URL}/notes/${encodeURIComponent(slug)}`)
      .then(({ data }) => {
        if (!live) return;
        setNote(data);
        document.title = `${data.title} | Hindsight`;
        track('note_view', { slug, kind: data.kind, author: data.author?.slug });
      })
      .catch(() => live && setMissing(true));
    return () => { live = false; };
  }, [slug]);

  if (missing) {
    return (
      <Box sx={{ maxWidth: 680, mx: 'auto', py: 4 }}>
        <Typography sx={{ color: colors.textHi, fontSize: 20, fontWeight: 700 }}>Note not found</Typography>
        <Typography sx={{ color: colors.textLo, mt: 1 }}>It may have been moved or unpublished. <RouterLink to="/notes" style={{ color: colors.accent }}>All notes</RouterLink></Typography>
      </Box>
    );
  }
  if (!note) return <CircularProgress size={22} sx={{ color: colors.accent, display: 'block', mx: 'auto', my: 4 }} />;
  return (
    <Box sx={{ pb: 4 }}>
      <NoteArticle note={note} />
      <Box sx={{ maxWidth: 680, mx: 'auto', mt: 3 }}>
        <RouterLink to="/notes" style={{ color: colors.textLo, fontSize: 14 }}>← All notes</RouterLink>
      </Box>
    </Box>
  );
};

export default NotePage;
