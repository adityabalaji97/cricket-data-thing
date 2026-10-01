import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import { Box, Button, Chip, CircularProgress, MenuItem, Snackbar, TextField, Typography } from '@mui/material';
import axios from 'axios';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { NoteArticle } from './NotePage';
import { KIND_LABEL, formatNoteDate } from './noteMarkdown.mjs';

/**
 * /admin/notes: the phone-first Notes queue (routers/notes.py).
 *
 * The admin token (shared with /admin, kept in localStorage) sees every draft, edits, publishes
 * and rejects, and adds friends as authors. A friend's personal token opens the same page limited
 * to "New article" and their own notes; whatever they write lands as a draft for the admin.
 */
const ADMIN_KEY = 'hindsight_admin_token';
const AUTHOR_KEY = 'hindsight_author_token';
const TABS = [['draft', 'Drafts'], ['published', 'Published'], ['rejected', 'Rejected'], ['authors', 'Authors']];
const ADMIN_KINDS = ['article', 'analysis', 'recap', 'preview'];
const AUTHOR_KINDS = ['article', 'analysis'];
const STATUS_COLOR = { draft: colors.gold, published: colors.accent, rejected: colors.red };

const store = {
  get: (k) => { try { return localStorage.getItem(k) || ''; } catch { return ''; } },
  set: (k, v) => { try { if (v) localStorage.setItem(k, v); else localStorage.removeItem(k); } catch { /* private mode */ } },
};

const fieldSx = {
  '& .MuiInputBase-root': { color: colors.textHi, bgcolor: colors.input },
  '& .MuiInputLabel-root': { color: colors.textLo },
  '& .MuiOutlinedInput-notchedOutline': { borderColor: colors.borderStrong },
};
const primarySx = { bgcolor: colors.accent, color: colors.bg, fontWeight: 700, minHeight: 44, '&:hover': { bgcolor: colors.accentHover } };
const outlineSx = { color: colors.textHi, borderColor: colors.borderStrong, minHeight: 44 };

/** The two token kinds talk to different routes; this hides which. */
function makeApi(mode, token) {
  const http = axios.create({ baseURL: config.API_URL, headers: mode === 'admin' ? { 'X-Admin-Token': token } : { 'X-Author-Token': token } });
  const admin = mode === 'admin';
  return {
    mode,
    list: async (status) => (admin
      ? (await http.get('/admin/notes', { params: { status } })).data.notes
      : (await http.get('/author/me')).data.notes),
    me: async () => (admin ? null : (await http.get('/author/me')).data.author),
    get: async (id) => (await http.get(admin ? `/admin/notes/${id}` : `/author/notes/${id}`)).data,
    create: async (body) => (await http.post(admin ? '/admin/notes' : '/author/notes', body)).data,
    update: async (id, body) => (await http.patch(admin ? `/admin/notes/${id}` : `/author/notes/${id}`, body)).data,
    status: async (id, action) => (await http.post(`/admin/notes/${id}/${action}`)).data,
    chart: async (url, kind) => (await http.post(admin ? '/admin/notes/charts' : '/author/charts', { url, kind })).data,
    authors: async () => (await http.get('/admin/authors')).data.authors,
    addAuthor: async (body) => (await http.post('/admin/authors', body)).data,
    rotate: async (id) => (await http.post(`/admin/authors/${id}/token`)).data.token,
  };
}

const errorText = (err, fallback) => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return fallback;
};

// ----------------------------------------------------------------------------------- sign in

const SignIn = ({ onSignedIn }) => {
  const [value, setValue] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    const token = value.trim();
    if (!token) return;
    setBusy(true);
    setError('');
    // Try it as the admin token first, then as a friend's author token.
    for (const mode of ['admin', 'author']) {
      try {
        const api = makeApi(mode, token);
        await (mode === 'admin' ? api.list('draft') : api.me());
        store.set(mode === 'admin' ? ADMIN_KEY : AUTHOR_KEY, token);
        onSignedIn(mode, token);
        setBusy(false);
        return;
      } catch { /* try the next kind */ }
    }
    setError('That token was not recognised.');
    setBusy(false);
  };

  return (
    <Box component="form" onSubmit={submit}>
      <Typography sx={{ color: colors.textMed, fontSize: 14, mb: 1.5 }}>Paste your admin or author token. It stays in this browser.</Typography>
      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField size="small" type="password" fullWidth placeholder="Token" value={value} onChange={(e) => setValue(e.target.value)} sx={fieldSx} />
        <Button type="submit" variant="contained" disabled={busy} sx={primarySx}>Open</Button>
      </Box>
      {error && <Typography sx={{ color: colors.red, fontSize: 13, mt: 1 }}>{error}</Typography>}
    </Box>
  );
};

// ----------------------------------------------------------------------------------- editor

const InsertChart = ({ api, onInsert, toast }) => {
  const [url, setUrl] = useState('');
  const [kind, setKind] = useState('win_prob');
  const [busy, setBusy] = useState(false);
  const isScorecard = /\/scorecard\//.test(url);

  const insert = async () => {
    setBusy(true);
    try {
      const chart = await api.chart(url.trim(), isScorecard ? kind : undefined);
      onInsert(chart);
      setUrl('');
      toast(`Chart added: ${chart.title || chart.id}`);
    } catch (err) {
      toast(errorText(err, 'Could not make a chart from that link'));
    }
    setBusy(false);
  };

  return (
    <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: colors.surface2, border: `1px solid ${colors.border}` }}>
      <Typography sx={{ fontSize: 12, letterSpacing: '.1em', textTransform: 'uppercase', color: colors.textLo, mb: 1 }}>Insert chart</Typography>
      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField size="small" fullWidth value={url} onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste a Hindsight query, scorecard or embed link" sx={fieldSx} />
        <Button variant="outlined" onClick={insert} disabled={busy || url.trim().length < 8} sx={{ ...outlineSx, minWidth: 72 }}>
          {busy ? <CircularProgress size={16} sx={{ color: colors.accent }} /> : 'Add'}
        </Button>
      </Box>
      {isScorecard && (
        <Box sx={{ display: 'flex', gap: 0.75, mt: 1 }}>
          {[['win_prob', 'Win probability'], ['recap', 'How it was won']].map(([value, label]) => (
            <Chip key={value} size="small" label={label} onClick={() => setKind(value)}
              sx={{ bgcolor: kind === value ? colors.accent : colors.surface3, color: kind === value ? colors.bg : colors.textMed, fontWeight: 600 }} />
          ))}
        </Box>
      )}
      <Typography sx={{ fontSize: 12, color: colors.textLo, mt: 1 }}>A query can take up to a minute the first time.</Typography>
    </Box>
  );
};

const Editor = ({ api, noteId, onClose, toast }) => {
  const isAdmin = api.mode === 'admin';
  const [note, setNote] = useState(null);
  const [form, setForm] = useState({ title: '', dek: '', body_md: '', kind: 'article', slug: '' });
  const [view, setView] = useState('edit');
  const [busy, setBusy] = useState(false);
  const bodyRef = useRef(null);
  const charts = useRef({});

  useEffect(() => {
    if (!noteId) return;
    api.get(noteId).then((n) => {
      setNote(n);
      charts.current = n.charts || {};
      setForm({ title: n.title, dek: n.dek || '', body_md: n.body_md, kind: n.kind, slug: n.slug });
    }).catch((err) => { toast(errorText(err, 'Could not open the note')); onClose(); });
  }, [api, noteId, onClose, toast]);

  const editable = !note || isAdmin || note.status === 'draft';
  const dirty = !note || ['title', 'dek', 'body_md', 'kind', 'slug'].some((k) => (form[k] || '') !== (note[k] || ''));
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const insertFence = (chart) => {
    charts.current = { ...charts.current, [chart.id]: { id: chart.id, kind: chart.kind, title: chart.title, embed: { query: 'q', ranking: 'q', win_prob: 'wp', recap: 'recap' }[chart.kind] || 'q' } };
    setForm((f) => {
      const el = bodyRef.current;
      const at = el && document.activeElement === el ? el.selectionStart : f.body_md.length;
      const before = f.body_md.slice(0, at).replace(/\s*$/, '');
      const after = f.body_md.slice(at).replace(/^\s*/, '');
      return { ...f, body_md: `${before}${before ? '\n\n' : ''}${chart.fence}\n\n${after}` };
    });
  };

  const save = async () => {
    const body = { title: form.title, dek: form.dek, body_md: form.body_md, kind: form.kind };
    if (isAdmin && note && form.slug !== note.slug) body.slug = form.slug;
    const saved = note ? await api.update(note.id, body) : await api.create(body);
    setNote(saved);
    charts.current = saved.charts || {};
    setForm({ title: saved.title, dek: saved.dek || '', body_md: saved.body_md, kind: saved.kind, slug: saved.slug });
    return saved;
  };

  const run = async (fn, done) => {
    setBusy(true);
    try { await fn(); if (done) toast(done); } catch (err) { toast(errorText(err, 'That did not work')); }
    setBusy(false);
  };

  const setStatus = (action, done) => run(async () => {
    const saved = dirty ? await save() : note;
    setNote(await api.status(saved.id, action));
  }, done);

  const previewNote = { ...(note || {}), ...form, author: note?.author || { name: 'You' }, charts: charts.current };

  if (noteId && !note) return <CircularProgress size={22} sx={{ color: colors.accent }} />;
  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2, flexWrap: 'wrap' }}>
        <Button onClick={onClose} sx={{ color: colors.textLo, minHeight: 40, px: 1 }}>← Back</Button>
        {note && <Chip size="small" label={note.status} sx={{ bgcolor: colors.surface2, color: STATUS_COLOR[note.status], fontWeight: 700, textTransform: 'capitalize' }} />}
        <Box sx={{ ml: 'auto', display: 'flex', gap: 0.5 }}>
          {[['edit', 'Edit'], ['preview', 'Preview']].map(([v, label]) => (
            <Chip key={v} label={label} onClick={() => setView(v)}
              sx={{ bgcolor: view === v ? colors.accent : colors.surface2, color: view === v ? colors.bg : colors.textMed, fontWeight: 600 }} />
          ))}
        </Box>
      </Box>

      {!editable && (
        <Typography sx={{ color: colors.gold, fontSize: 13, mb: 2 }}>This note is {note.status}; only drafts can be edited.</Typography>
      )}

      {view === 'preview' ? (
        <Box sx={{ border: `1px solid ${colors.border}`, borderRadius: 3, p: { xs: 1.5, md: 3 } }}><NoteArticle note={previewNote} preview /></Box>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.75 }}>
          <TextField label="Title" value={form.title} onChange={set('title')} fullWidth multiline disabled={!editable} sx={fieldSx} />
          <TextField label="One-line summary (dek)" value={form.dek} onChange={set('dek')} fullWidth multiline disabled={!editable} sx={fieldSx} />
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <TextField select size="small" label="Kind" value={form.kind} onChange={set('kind')} disabled={!editable} sx={{ ...fieldSx, minWidth: 150 }}>
              {(isAdmin ? ADMIN_KINDS : AUTHOR_KINDS).map((k) => <MenuItem key={k} value={k}>{KIND_LABEL[k]}</MenuItem>)}
            </TextField>
            {isAdmin && note && (
              <TextField size="small" label="URL slug" value={form.slug} onChange={set('slug')} sx={{ ...fieldSx, flex: 1, minWidth: 180 }}
                helperText={note.status === 'published' ? 'Changing it breaks links already shared' : 'Follows the title until published'}
                FormHelperTextProps={{ sx: { color: colors.textLo } }} />
            )}
          </Box>
          <TextField label="Body (markdown)" value={form.body_md} onChange={set('body_md')} inputRef={bodyRef} fullWidth multiline minRows={12}
            disabled={!editable} sx={{ ...fieldSx, '& textarea': { fontFamily: fonts.mono, fontSize: 13.5, lineHeight: 1.5 } }} />
          {editable && <InsertChart api={api} onInsert={insertFence} toast={toast} />}
        </Box>
      )}

      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 2.5 }}>
        {editable && (
          <Button variant="contained" disabled={busy || !dirty || !form.title.trim()} onClick={() => run(save, 'Saved')} sx={{ ...primarySx, flex: { xs: 1, sm: 'none' } }}>
            {note ? 'Save' : 'Create draft'}
          </Button>
        )}
        {isAdmin && note && note.status !== 'published' && (
          <Button variant="outlined" disabled={busy} onClick={() => setStatus('publish', 'Published')} sx={{ ...outlineSx, color: colors.accent, borderColor: 'rgba(182,242,74,.5)', flex: { xs: 1, sm: 'none' } }}>
            {dirty ? 'Save & publish' : 'Publish'}
          </Button>
        )}
        {isAdmin && note && note.status !== 'rejected' && (
          <Button variant="outlined" disabled={busy} onClick={() => setStatus('reject', note.status === 'published' ? 'Unpublished' : 'Rejected')} sx={{ ...outlineSx, color: colors.red, flex: { xs: 1, sm: 'none' } }}>
            {note.status === 'published' ? 'Unpublish' : 'Reject'}
          </Button>
        )}
        {isAdmin && note && note.status === 'rejected' && (
          <Button variant="outlined" disabled={busy} onClick={() => setStatus('draft', 'Back in drafts')} sx={outlineSx}>Back to drafts</Button>
        )}
        {note?.status === 'published' && (
          <Button component={RouterLink} to={`/notes/${note.slug}`} sx={{ color: colors.accent, minHeight: 44 }}>View live ↗</Button>
        )}
      </Box>
      {!isAdmin && !note && (
        <Typography sx={{ color: colors.textLo, fontSize: 13, mt: 1.5 }}>Drafts are reviewed before they appear on the site.</Typography>
      )}
    </Box>
  );
};

// ----------------------------------------------------------------------------------- lists

const NoteRow = ({ note, onOpen }) => (
  <Box component="button" onClick={() => onOpen(note.id)}
    sx={{ display: 'block', width: '100%', textAlign: 'left', cursor: 'pointer', font: 'inherit', p: 1.75, mb: 1.25,
      bgcolor: colors.surface1, color: 'inherit', border: `1px solid ${colors.border}`, borderRadius: '14px',
      '&:hover': { borderColor: 'rgba(182,242,74,.35)' } }}>
    <Typography sx={{ fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: colors.textLo }}>
      {KIND_LABEL[note.kind]} · <span style={{ color: STATUS_COLOR[note.status] }}>{note.status}</span>
    </Typography>
    <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 17, color: colors.textHi, mt: 0.5, lineHeight: 1.25 }}>{note.title}</Typography>
    <Typography sx={{ fontSize: 12.5, color: colors.textLo, mt: 0.5 }}>
      {note.author?.name}{note.author?.is_bot ? ' (bot)' : ''} · {formatNoteDate(note.published_at || note.updated_at)}
    </Typography>
  </Box>
);

const AuthorsTab = ({ api, toast }) => {
  const [authors, setAuthors] = useState(null);
  const [name, setName] = useState('');
  const [bio, setBio] = useState('');
  const [issued, setIssued] = useState(null);

  const load = useCallback(() => api.authors().then(setAuthors).catch(() => setAuthors([])), [api]);
  useEffect(() => { load(); }, [load]);

  const add = async () => {
    try {
      const created = await api.addAuthor({ name: name.trim(), bio: bio.trim() || null });
      setIssued({ name: created.name, token: created.token });
      setName(''); setBio('');
      load();
    } catch (err) { toast(errorText(err, 'Could not add the author')); }
  };
  const rotate = async (a) => {
    try { setIssued({ name: a.name, token: await api.rotate(a.id) }); } catch (err) { toast(errorText(err, 'Could not issue a token')); }
  };
  const copy = async (t) => { try { await navigator.clipboard.writeText(t); toast('Token copied'); } catch { toast('Copy blocked'); } };

  return (
    <Box>
      {issued && (
        <Box sx={{ p: 1.75, mb: 2, borderRadius: 2, border: `1px solid ${colors.accent}`, bgcolor: colors.accentSoft }}>
          <Typography sx={{ fontSize: 13, color: colors.textHi, mb: 1 }}>
            Token for <b>{issued.name}</b>. It is shown once; send it to them privately. They open <b>/admin/notes</b> and paste it.
          </Typography>
          <Typography sx={{ fontFamily: fonts.mono, fontSize: 13, color: colors.accent, wordBreak: 'break-all' }}>{issued.token}</Typography>
          <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
            <Button size="small" onClick={() => copy(issued.token)} sx={{ color: colors.accent, fontWeight: 700 }}>Copy</Button>
            <Button size="small" onClick={() => setIssued(null)} sx={{ color: colors.textLo }}>Done</Button>
          </Box>
        </Box>
      )}
      <Box sx={{ p: 1.75, mb: 2, borderRadius: 2, bgcolor: colors.surface1, border: `1px solid ${colors.border}`, display: 'flex', flexDirection: 'column', gap: 1.25 }}>
        <Typography sx={{ fontSize: 13, fontWeight: 700, color: colors.textHi }}>Add a writer</Typography>
        <TextField size="small" label="Name" value={name} onChange={(e) => setName(e.target.value)} sx={fieldSx} />
        <TextField size="small" label="Short bio (optional)" value={bio} onChange={(e) => setBio(e.target.value)} sx={fieldSx} />
        <Button variant="contained" onClick={add} disabled={!name.trim()} sx={{ ...primarySx, alignSelf: 'flex-start' }}>Add and get token</Button>
      </Box>
      {authors === null && <CircularProgress size={20} sx={{ color: colors.accent }} />}
      {(authors || []).map((a) => (
        <Box key={a.id} sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 1.25, borderBottom: `1px solid ${colors.border}` }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography sx={{ color: colors.textHi, fontWeight: 600 }}>{a.name}{a.is_bot ? ' (bot)' : ''}</Typography>
            <Typography sx={{ color: colors.textLo, fontSize: 12.5 }}>{a.published} published · {a.drafts} drafts</Typography>
          </Box>
          {!a.is_bot && (
            <Button size="small" onClick={() => rotate(a)} sx={{ color: colors.textMed }}>{a.has_token ? 'New token' : 'Issue token'}</Button>
          )}
        </Box>
      ))}
    </Box>
  );
};

const Queue = ({ api, me, onOpen, toast, onAuthFail }) => {
  const isAdmin = api.mode === 'admin';
  const [tab, setTab] = useState('draft');
  const [notes, setNotes] = useState(null);

  useEffect(() => {
    if (tab === 'authors') return;
    setNotes(null);
    api.list(tab).then(setNotes).catch((err) => {
      if ([403, 404].includes(err.response?.status)) onAuthFail();
      else toast('Could not load notes');
      setNotes([]);
    });
  }, [api, tab, toast, onAuthFail]);

  return (
    <Box>
      {isAdmin ? (
        <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mb: 2 }}>
          {TABS.map(([value, label]) => (
            <Chip key={value} label={label} onClick={() => setTab(value)}
              sx={{ bgcolor: tab === value ? colors.accent : colors.surface2, color: tab === value ? colors.bg : colors.textMed, fontWeight: 600 }} />
          ))}
        </Box>
      ) : (
        <Typography sx={{ color: colors.textMed, fontSize: 14, mb: 2 }}>Signed in as <b>{me?.name}</b>. Your notes:</Typography>
      )}
      {tab === 'authors' ? <AuthorsTab api={api} toast={toast} /> : (
        <>
          <Button variant="contained" onClick={() => onOpen('new')} sx={{ ...primarySx, mb: 2 }}>New article</Button>
          {notes === null && <CircularProgress size={22} sx={{ color: colors.accent, display: 'block' }} />}
          {notes && notes.length === 0 && (
            <Typography sx={{ color: colors.textLo, py: 3 }}>
              {isAdmin && tab === 'draft' ? 'No drafts. The bot leaves recaps and previews here after the nightly load.' : 'Nothing here.'}
            </Typography>
          )}
          {(notes || []).map((n) => <NoteRow key={n.id} note={n} onOpen={onOpen} />)}
        </>
      )}
    </Box>
  );
};

// ----------------------------------------------------------------------------------- page

const AdminNotes = () => {
  const [session, setSession] = useState(() => {
    const admin = store.get(ADMIN_KEY);
    if (admin) return { mode: 'admin', token: admin };
    const author = store.get(AUTHOR_KEY);
    return author ? { mode: 'author', token: author } : null;
  });
  const [me, setMe] = useState(null);
  const [params, setParams] = useSearchParams();
  // ?open=<id>: arrive straight in a note's editor (the Social queue's "Make note").
  const [open, setOpenState] = useState(() => Number(params.get('open')) || null);   // note id, 'new', or null
  const setOpen = useCallback((value) => {
    setOpenState(value);
    if (params.has('open')) setParams({}, { replace: true });
  }, [params, setParams]);
  const [message, setMessage] = useState(null);
  const toast = useCallback((m) => setMessage(m), []);
  const api = useMemo(() => (session ? makeApi(session.mode, session.token) : null), [session]);

  useEffect(() => { document.title = 'Notes queue | Hindsight'; }, []);
  useEffect(() => {
    if (api?.mode === 'author') api.me().then(setMe).catch(() => setMe(null));
  }, [api]);

  const signOut = useCallback(() => {
    store.set(session?.mode === 'admin' ? ADMIN_KEY : AUTHOR_KEY, '');
    setSession(null);
    setOpen(null);
  }, [session, setOpen]);
  const onAuthFail = useCallback(() => { toast('Token rejected'); signOut(); }, [toast, signOut]);
  const close = useCallback(() => setOpen(null), [setOpen]);

  return (
    <Box sx={{ maxWidth: 720, mx: 'auto', pb: 4, color: colors.textHi }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        {session?.mode === 'admin' && (
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            <Chip component={RouterLink} to="/admin" clickable label="Social" sx={{ bgcolor: colors.surface2, color: colors.textMed }} />
            <Chip label="Notes" sx={{ bgcolor: colors.accentSoft, color: colors.accent, fontWeight: 700 }} />
          </Box>
        )}
        {session && <Button size="small" onClick={signOut} sx={{ ml: 'auto', color: colors.textLo }}>Sign out</Button>}
      </Box>
      {!api && <SignIn onSignedIn={(mode, token) => setSession({ mode, token })} />}
      {api && open && <Editor key={open} api={api} noteId={open === 'new' ? null : open} onClose={close} toast={toast} />}
      {api && !open && <Queue api={api} me={me} onOpen={setOpen} toast={toast} onAuthFail={onAuthFail} />}
      <Snackbar open={!!message} autoHideDuration={2600} onClose={() => setMessage(null)} message={message}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }} sx={{ bottom: { xs: 80, md: 24 } }} />
    </Box>
  );
};

export default AdminNotes;
