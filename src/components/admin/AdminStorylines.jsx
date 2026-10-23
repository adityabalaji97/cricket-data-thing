import React, { useCallback, useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, Chip, CircularProgress, Link, Snackbar, TextField, Typography } from '@mui/material';
import axios from 'axios';
import config from '../../config';
import { apiErrorText } from '../../utils/apiError';

/**
 * /admin/storylines — the review gate for match-preview storylines (MATCH_PREVIEW_STORYLINES_PLAN.md chunk 7).
 * Each upcoming big fixture's talking points, found in its headlines (services/preview_storylines.py), arrive
 * pending; nothing reaches a preview or a post until it's approved here. Edit = approve in your words. Each point
 * shows the headlines that make it (title, outlet, link). Admin token as on /admin.
 */
const TOKEN_KEY = 'hindsight_admin_token';
const C = { bg: '#0a0c11', card: '#12151c', line: 'rgba(255,255,255,.08)', hi: '#f3f4f6', mid: '#c3c8d0', lo: '#9aa1ac', lime: '#b6f24a', red: '#e5484d', amber: '#f0b429' };
const readToken = () => { try { return localStorage.getItem(TOKEN_KEY) || ''; } catch { return ''; } };
const STATUS_INK = { pending: C.amber, approved: C.lime, dropped: C.lo };
const VERDICT_INK = { supported: C.lime, 'not supported': C.red, partly: C.amber, 'too little data': C.lo, context: C.mid };

/** The data's answer (services/storyline_testers.py): verdict, the finding with its numbers, the query link. */
const TestResult = ({ test }) => (
  <Box sx={{ mt: 0.75, pl: 1.25, borderLeft: `2px solid ${VERDICT_INK[test.verdict] || C.lo}` }}>
    <Typography sx={{ fontSize: 11, fontWeight: 700, color: VERDICT_INK[test.verdict] || C.lo, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
      {`The data: ${test.verdict}`}
    </Typography>
    {test.finding && <Typography sx={{ fontSize: 13.5, color: C.mid, lineHeight: 1.35 }}>{test.finding}</Typography>}
    {test.query_url && (
      <Link href={test.query_url} target="_blank" rel="noopener noreferrer" sx={{ fontSize: 12, color: C.lo }}>Open the query</Link>
    )}
  </Box>
);

const day = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });

const Point = ({ point, client, onChanged, toast }) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(point.edited_claim || point.claim);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const runTest = async () => {
    setBusy(true);
    try { await client.post(`/storylines/admin/${point.id}/test`); onChanged(); } catch (e) { toast(apiErrorText(e)); } finally { setBusy(false); }
  };
  const act = async (action, claim) => {
    setBusy(true);
    try {
      await client.post(`/storylines/admin/${point.id}`, { action, claim });
      setEditing(false);
      onChanged();
    } catch (e) { toast(apiErrorText(e)); } finally { setBusy(false); }
  };
  const reviewed = point.status !== 'pending';
  return (
    <Box sx={{ py: 1.25, borderTop: `1px solid ${C.line}`, opacity: point.status === 'dropped' ? 0.55 : 1 }}>
      <Box sx={{ display: 'flex', gap: 0.75, alignItems: 'center', mb: 0.5, flexWrap: 'wrap' }}>
        <Chip size="small" label={point.kind} sx={{ height: 20, fontSize: 11, bgcolor: '#1d212b', color: C.mid }} />
        <Typography sx={{ fontSize: 11, fontWeight: 700, color: STATUS_INK[point.status], textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {point.status}
        </Typography>
        {(point.players || []).length > 0 && (
          <Typography sx={{ fontSize: 12, color: C.lo }}>{point.players.join(', ')}</Typography>
        )}
      </Box>
      {editing ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <TextField multiline minRows={2} size="small" value={draft} onChange={(e) => setDraft(e.target.value)}
            sx={{ '& .MuiInputBase-root': { color: C.hi, bgcolor: '#14171e', fontSize: 15 } }} />
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button size="small" variant="contained" disabled={busy} onClick={() => act('edit', draft)}
              sx={{ bgcolor: C.lime, color: C.bg, fontWeight: 700 }}>Save & approve</Button>
            <Button size="small" onClick={() => setEditing(false)} sx={{ color: C.lo }}>Cancel</Button>
          </Box>
        </Box>
      ) : (
        <Typography sx={{ fontSize: 15.5, color: C.hi, lineHeight: 1.35 }}>{point.edited_claim || point.claim}</Typography>
      )}
      {point.test && <TestResult test={point.test} />}
      {point.edited_claim && !editing && (
        <Typography sx={{ fontSize: 12, color: C.lo, mt: 0.25 }}>{`Found as: ${point.claim}`}</Typography>
      )}
      <Button size="small" onClick={() => setOpen(!open)} sx={{ color: C.lo, px: 0, minWidth: 0, mt: 0.25, fontSize: 12 }}>
        {`${open ? 'Hide' : 'Show'} ${point.sources.length} headline${point.sources.length === 1 ? '' : 's'}`}
      </Button>
      {open && (point.sources || []).map((s) => (
        <Typography key={s.url} sx={{ fontSize: 13, color: C.mid, lineHeight: 1.35, mb: 0.5 }}>
          <Link href={s.url} target="_blank" rel="noopener noreferrer" sx={{ color: C.hi }}>{s.title}</Link>
          {s.outlet ? <Box component="span" sx={{ color: C.lo }}>{` — ${s.outlet}`}</Box> : null}
        </Typography>
      ))}
      {!editing && (
        <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
          {point.status !== 'approved' && (
            <Button size="small" disabled={busy} onClick={() => act('approve')} sx={{ color: C.lime, fontWeight: 700 }}>Approve</Button>
          )}
          <Button size="small" disabled={busy} onClick={() => setEditing(true)} sx={{ color: C.mid }}>Edit</Button>
          <Button size="small" disabled={busy} onClick={runTest} sx={{ color: C.mid }}>{point.test ? 'Re-test' : 'Test'}</Button>
          {point.status !== 'dropped' && (
            <Button size="small" disabled={busy} onClick={() => act('drop')} sx={{ color: C.red }}>Drop</Button>
          )}
          {reviewed && (
            <Button size="small" disabled={busy} onClick={() => act('pending')} sx={{ color: C.lo, ml: 'auto' }}>Undo</Button>
          )}
        </Box>
      )}
    </Box>
  );
};

const Fixture = ({ fixture, client, onChanged, toast }) => {
  const [running, setRunning] = useState(false);
  const find = async () => {
    setRunning(true);
    try {
      const { data } = await client.post('/storylines/admin/run', { fixture_key: fixture.fixture_key });
      toast(`${data.points} talking points, ${data.new} new`);
      onChanged();
    } catch (e) { toast(apiErrorText(e)); } finally { setRunning(false); }
  };
  const approved = fixture.points.filter((p) => p.status === 'approved').length;
  return (
    <Box sx={{ bgcolor: C.card, borderRadius: 2, p: 1.75, mb: 1.5, border: `1px solid ${C.line}` }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 1 }}>
        <Typography sx={{ fontWeight: 700, fontSize: 17, color: C.hi }}>{`${fixture.team1} v ${fixture.team2}`}</Typography>
        <Typography sx={{ fontSize: 13, color: C.lo, whiteSpace: 'nowrap' }}>{day(fixture.match_date)}</Typography>
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.25, mb: 0.5 }}>
        <Typography sx={{ fontSize: 12.5, color: C.lo }}>
          {`${fixture.headlines} headlines · ${approved} of ${fixture.points.length} approved`}
        </Typography>
        <Button size="small" disabled={running} onClick={find} sx={{ ml: 'auto', color: C.lime }}>
          {running ? 'Reading…' : fixture.points.length ? 'Refresh' : 'Find talking points'}
        </Button>
      </Box>
      {fixture.points.map((p) => <Point key={p.id} point={p} client={client} onChanged={onChanged} toast={toast} />)}
    </Box>
  );
};

const AdminStorylines = () => {
  const token = readToken();
  const client = React.useMemo(() => axios.create({ baseURL: config.API_URL, headers: { 'X-Admin-Token': token } }), [token]);
  const [fixtures, setFixtures] = useState(null);
  const [message, setMessage] = useState(null);
  const toast = useCallback((m) => setMessage(m), []);
  const load = useCallback(() => {
    client.get('/storylines/admin').then(({ data }) => setFixtures(data.fixtures || []))
      .catch((e) => { setFixtures([]); toast(apiErrorText(e)); });
  }, [client, toast]);
  useEffect(() => { if (token) load(); }, [token, load]);

  return (
    <Box sx={{ maxWidth: 560, mx: 'auto', px: 2, py: 2, color: C.hi }}>
      <Box sx={{ display: 'flex', gap: 0.5, mb: 2 }}>
        <Chip component={RouterLink} to="/admin" clickable label="Social" sx={{ bgcolor: '#1d212b', color: C.mid }} />
        <Chip component={RouterLink} to="/admin/notes" clickable label="Notes" sx={{ bgcolor: '#1d212b', color: C.mid }} />
        <Chip label="Storylines" sx={{ bgcolor: 'rgba(182,242,74,0.13)', color: C.lime, fontWeight: 700 }} />
      </Box>
      {!token && <Typography sx={{ color: C.lo }}>Open /admin and enter the admin token first.</Typography>}
      {token && fixtures === null && <CircularProgress size={22} sx={{ color: C.lime }} />}
      {token && fixtures && fixtures.length === 0 && (
        <Typography sx={{ color: C.lo, py: 4 }}>No big fixtures with headlines in the next few days.</Typography>
      )}
      {(fixtures || []).map((f) => <Fixture key={f.fixture_key} fixture={f} client={client} onChanged={load} toast={toast} />)}
      <Snackbar open={!!message} autoHideDuration={2500} onClose={() => setMessage(null)} message={message}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }} />
    </Box>
  );
};

export default AdminStorylines;
