import React, { useCallback, useEffect, useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { Box, Button, Chip, CircularProgress, Snackbar, TextField, Typography } from '@mui/material';
import axios from 'axios';
import config from '../../config';
import { shareImage, siteOrigin } from '../ui/ChartExportButton';
import GraphicPromptList from '../GraphicPromptList';
import { apiErrorText } from '../../utils/apiError';

/**
 * /admin: the phone-first admin queue. "Social" lists content packs (services/content_packs.py):
 * a stat image, a title, where to post it and the first comment with the link, each one tap to
 * copy or share, so a friend can post it from their own account. Needs the admin token (kept in
 * this browser's localStorage).
 */
const TOKEN_KEY = 'hindsight_admin_token';
const C = { bg: '#0a0c11', card: '#12151c', line: 'rgba(255,255,255,.08)', hi: '#f3f4f6', mid: '#c3c8d0', lo: '#9aa1ac', lime: '#b6f24a', red: '#e5484d', amber: '#f0b429' };
const STATUSES = ['ready', 'posted', 'skipped', 'expired'];

const readToken = () => { try { return localStorage.getItem(TOKEN_KEY) || ''; } catch { return ''; } };

const api = (token) => axios.create({ baseURL: config.API_URL, headers: { 'X-Admin-Token': token } });

const deadlineText = (postBy) => {
  if (!postBy) return 'No deadline';
  const d = new Date(postBy);
  const hours = Math.round((d - Date.now()) / 36e5);
  const when = d.toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  if (hours < 0) return `Deadline passed (${when})`;
  return `Post by ${when} · ${hours < 48 ? `${hours}h` : `${Math.round(hours / 24)}d`} left`;
};

// Best Reddit window, 12:00-18:00 UTC, in the viewer's own time.
const bestWindow = () => {
  const fmt = (h) => { const d = new Date(); d.setUTCHours(h, 0, 0, 0); return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }); };
  return `${fmt(12)}–${fmt(18)}`;
};

const CopyBlock = ({ label, text, onCopy, multiline }) => (
  <Box sx={{ mt: 1.5 }}>
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
      <Typography sx={{ fontSize: 11, letterSpacing: '.12em', textTransform: 'uppercase', color: C.lo }}>{label}</Typography>
      <Button size="small" onClick={() => onCopy(text, label)} sx={{ color: C.lime, minHeight: 32, fontWeight: 700 }}>Copy</Button>
    </Box>
    <Typography sx={{ fontSize: multiline ? 13 : 15, fontWeight: multiline ? 400 : 600, color: multiline ? C.mid : C.hi, whiteSpace: 'pre-wrap', lineHeight: 1.4,
      // The first comment carries a long query URL with no spaces; let it break so it cannot widen
      // the page (it made the admin page side-scroll and zoom out on phones).
      overflowWrap: 'anywhere' }}>
      {text}
    </Typography>
  </Box>
);

const PackCard = ({ pack, client, onChanged, toast }) => {
  const [postedUrl, setPostedUrl] = useState('');
  const [marking, setMarking] = useState(false);
  const navigate = useNavigate();
  // The pack becomes a draft note (or reopens the one it already became) in /admin/notes.
  const makeNote = async () => {
    try {
      const { data } = await client.post(`/admin/content/packs/${pack.id}/note`);
      navigate(`/admin/notes?open=${data.id}`);
    } catch (err) { toast(apiErrorText(err, null) || 'Could not make a note'); }
  };
  const facts = pack.facts || {};
  const imageUrl = `${siteOrigin()}/img/${pack.snapshot_id}.png`;

  const copy = async (text, what) => {
    try { await navigator.clipboard.writeText(text); toast(`${what} copied`); } catch { toast('Copy blocked'); }
  };
  const update = async (body, done) => {
    try { await client.patch(`/admin/content/packs/${pack.id}`, body); toast(done); onChanged(); }
    catch (err) { toast(apiErrorText(err, null) || 'Update failed'); }
  };

  return (
    <Box sx={{ bgcolor: C.card, border: `1px solid ${C.line}`, borderRadius: 3, p: 2, mb: 2 }}>
      <Typography sx={{ fontSize: 12, color: C.lo, mb: 1 }}>
        {pack.team1 ? `${pack.team1} v ${pack.team2} · ${pack.competition} · ${pack.match_date}`
          : pack.source === 'tally' ? `Season tally · ${String(pack.created_at).slice(0, 10)}`
            : `From an idea · ${String(pack.created_at).slice(0, 10)}`}
      </Typography>
      {pack.data_source === 'cricsheet' && (
        // Loaded from Cricsheet ahead of the ball-by-ball CSV: scorecard numbers only, no Impact,
        // control % or win probability until the CSV arrives and the match is upgraded.
        <Chip size="small" label="Basic data · ball-by-ball pending" sx={{ mb: 1, bgcolor: 'rgba(240,180,41,0.14)', color: C.amber, fontWeight: 600 }} />
      )}
      <Box component="img" src={imageUrl} alt={pack.title} loading="lazy"
        sx={{ display: 'block', width: '100%', maxWidth: 420, aspectRatio: '4 / 5', borderRadius: 2, bgcolor: '#14171e', border: `1px solid ${C.line}` }} />
      {(facts.chart_options || []).length > 1 && (
        // Other chart forms this pack was built with; Jev's (or the rules') top pick leads.
        <Box sx={{ mt: 1.5 }}>
          <Typography sx={{ fontSize: 12, color: C.lo, mb: 0.75 }}>
            Chart · {{ jev: "Jev's pick first", 'shape+jev': 'led by the data shape, then Jev', shape: 'led by the data shape' }[facts.chart_picked_by] || 'rule order'} · tap to switch
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', pb: 0.5 }}>
            {facts.chart_options.map((o, i) => {
              const active = o.snapshot_id === pack.snapshot_id;
              return (
                <Box key={o.snapshot_id} component="button" type="button"
                  onClick={() => !active && update({ snapshot_id: o.snapshot_id }, `Switched to ${o.form}`)}
                  sx={{ flex: '0 0 auto', width: 96, p: 0.5, bgcolor: 'transparent', cursor: active ? 'default' : 'pointer',
                    border: `2px solid ${active ? C.lime : C.line}`, borderRadius: 2, color: C.hi, textAlign: 'center' }}>
                  <Box component="img" src={`${siteOrigin()}/img/${o.snapshot_id}.png?size=portrait`} alt={o.form} loading="lazy"
                    sx={{ width: '100%', aspectRatio: '4 / 5', borderRadius: 1, display: 'block', bgcolor: '#14171e' }} />
                  <Typography sx={{ fontSize: 12, mt: 0.5, color: active ? C.lime : C.mid }}>
                    {o.form}{i === 0 && String(facts.chart_picked_by || '').includes('jev') && o.p != null ? ' ★' : ''}{o.p != null ? ` ${Math.round(o.p * 100)}%` : ''}
                  </Typography>
                </Box>
              );
            })}
          </Box>
        </Box>
      )}
      <Box sx={{ display: 'flex', gap: 1, mt: 1.5, flexWrap: 'wrap' }}>
        <Button variant="contained" onClick={() => shareImage(imageUrl, `hindsight-${pack.snapshot_id}.png`, pack.title, pack.title)}
          sx={{ bgcolor: C.lime, color: C.bg, fontWeight: 700, minHeight: 44, '&:hover': { bgcolor: '#a3dc3f' } }}>
          Share image
        </Button>
        <Button variant="outlined" href={`${imageUrl}?download=1`} sx={{ color: C.hi, borderColor: C.line, minHeight: 44 }}>Download</Button>
        <Button variant="outlined" onClick={makeNote} sx={{ color: C.hi, borderColor: C.line, minHeight: 44 }}>Make note</Button>
      </Box>

      <CopyBlock label="Title" text={pack.title} onCopy={copy} />
      <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mt: 1 }}>
        <Chip size="small" label={`${pack.subreddit} · ${pack.flair} flair`} sx={{ bgcolor: '#1d212b', color: C.hi }} />
        {(facts.alternates || []).map((a) => <Chip key={a} size="small" label={`or ${a}`} sx={{ bgcolor: '#1d212b', color: C.mid }} />)}
      </Box>
      <CopyBlock label="First comment (has the link)" text={pack.first_comment} onCopy={copy} multiline />

      <Typography sx={{ mt: 1.5, fontSize: 13, color: new Date(pack.post_by) < new Date() ? C.red : C.amber }}>
        {deadlineText(pack.post_by)} · best {bestWindow()}
      </Typography>
      {(pack.rule_warnings || []).map((w) => (
        <Typography key={w} sx={{ fontSize: 12, color: C.amber, mt: 0.5 }}>⚠ {w}</Typography>
      ))}

      {pack.status === 'ready' ? (
        <Box sx={{ mt: 2 }}>
          {marking ? (
            <Box sx={{ display: 'flex', gap: 1 }}>
              <TextField size="small" fullWidth placeholder="Reddit post URL (optional)" value={postedUrl}
                onChange={(e) => setPostedUrl(e.target.value)}
                sx={{ '& .MuiInputBase-root': { color: C.hi, bgcolor: '#14171e' } }} />
              <Button variant="contained" onClick={() => update({ status: 'posted', posted_url: postedUrl }, 'Marked posted')}
                sx={{ bgcolor: C.lime, color: C.bg, fontWeight: 700 }}>Save</Button>
            </Box>
          ) : (
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button variant="outlined" onClick={() => setMarking(true)} sx={{ color: C.hi, borderColor: C.line, minHeight: 40, flex: 1 }}>Mark posted</Button>
              <Button variant="outlined" onClick={() => update({ status: 'skipped' }, 'Skipped')} sx={{ color: C.lo, borderColor: C.line, minHeight: 40, flex: 1 }}>Skip</Button>
            </Box>
          )}
        </Box>
      ) : (
        <Typography sx={{ mt: 1.5, fontSize: 12, color: C.lo }}>
          {pack.status}{pack.posted_url ? ' · ' : ''}{pack.posted_url && <a href={pack.posted_url} style={{ color: C.lime }} target="_blank" rel="noopener noreferrer">post</a>}
        </Typography>
      )}
    </Box>
  );
};

const IDEA_STATUS_COLOR = { pending: C.lo, parked: C.amber, resolved: C.lime, failed: C.red };

// One worked example per chart form (services/pack_charts.py). A form is offered only when the
// parsed query has the right shape, and Jev may still lead with another valid form.

// "Idea -> pack": a hunch in plain English becomes a query, a highlighted chart and a pack. Ideas
// about matches not loaded yet are parked and retried after each nightly load.
const IdeaBox = ({ client, toast, onPackCreated }) => {
  const [textValue, setTextValue] = useState('');
  const [format, setFormat] = useState('');
  const [ideas, setIdeas] = useState([]);
  const [sending, setSending] = useState(false);
  const [showExamples, setShowExamples] = useState(false);

  const loadIdeas = useCallback(async () => {
    try {
      const { data } = await client.get('/admin/content/ideas', { params: { limit: 6 } });
      setIdeas(data.ideas);
      return data.ideas;
    } catch { return []; }
  }, [client]);

  useEffect(() => { loadIdeas(); }, [loadIdeas]);

  // Poll while an idea is being worked on (parsing + a cold query can take a minute).
  useEffect(() => {
    if (!ideas.some((i) => i.status === 'pending')) return undefined;
    const timer = setTimeout(async () => {
      const next = await loadIdeas();
      if (next.some((i) => i.status === 'resolved' && ideas.find((o) => o.id === i.id)?.status === 'pending')) onPackCreated();
    }, 5000);
    return () => clearTimeout(timer);
  }, [ideas, loadIdeas, onPackCreated]);

  const submit = async () => {
    if (textValue.trim().length < 8) return;
    setSending(true);
    try {
      await client.post('/admin/content/ideas', { text: textValue.trim(), format: format || null });
      setTextValue('');
      toast('Working on it…');
      loadIdeas();
    } catch (err) { toast(err.response?.data?.detail?.[0]?.msg || 'Could not submit the idea'); }
    setSending(false);
  };

  return (
    <Box sx={{ bgcolor: C.card, border: `1px solid ${C.line}`, borderRadius: 3, p: 2, mb: 2 }}>
      <Typography sx={{ fontSize: 13, fontWeight: 700, mb: 1 }}>Idea → pack</Typography>
      <TextField multiline minRows={2} fullWidth value={textValue} onChange={(e) => setTextValue(e.target.value)}
        placeholder="e.g. Gill and Kohli control % compared to other ODI partnerships since 2019, 1000+ balls"
        sx={{ '& .MuiInputBase-root': { color: C.hi, bgcolor: '#14171e', fontSize: 14 } }} />
      <Box sx={{ display: 'flex', gap: 0.75, mt: 1, alignItems: 'center', flexWrap: 'wrap' }}>
        {[['', 'Auto'], ['T20', 'T20'], ['ODI', 'ODI']].map(([value, label]) => (
          <Chip key={label} size="small" label={label} onClick={() => setFormat(value)}
            sx={{ bgcolor: format === value ? C.lime : '#1d212b', color: format === value ? C.bg : C.mid, fontWeight: 600 }} />
        ))}
        <Button variant="contained" onClick={submit} disabled={sending || textValue.trim().length < 8}
          sx={{ ml: 'auto', bgcolor: C.lime, color: C.bg, fontWeight: 700, '&:hover': { bgcolor: '#a3dc3f' } }}>
          Make pack
        </Button>
      </Box>
      <Button size="small" onClick={() => setShowExamples((v) => !v)} aria-expanded={showExamples}
        sx={{ mt: 1, px: 0, minHeight: 32, color: C.lime, textTransform: 'none', fontWeight: 600 }}>
        {showExamples ? 'Hide prompts' : 'Prompts to try, by chart type'}
      </Button>
      {showExamples && (
        // Same prompt list as the public /graphics page; here a tap only fills the box.
        <Box sx={{ mt: 0.5 }}>
          <GraphicPromptList title="Tap one to fill the box. A chart is offered when the data fits; the rest appear as thumbnails."
            onPick={(prompt, fmt) => { setTextValue(prompt); setFormat(fmt); }} />
        </Box>
      )}
      {ideas.map((i) => (
        <Box key={i.id} sx={{ mt: 1.5, pt: 1.5, borderTop: `1px solid ${C.line}` }}>
          <Typography sx={{ fontSize: 13, color: C.mid }}>{i.text}</Typography>
          <Typography sx={{ fontSize: 12, color: IDEA_STATUS_COLOR[i.status] || C.lo, mt: 0.5 }}>
            {i.status === 'pending' ? 'Working…' : i.status}
            {i.status === 'resolved' && i.pack_title ? ` · pack below: ${i.pack_title}` : i.note && i.status !== 'resolved' ? ` · ${i.note}` : ''}
          </Typography>
        </Box>
      ))}
    </Box>
  );
};

const PILLAR_LABELS = { debate: 'Debate', myth: 'Myth-busting', weird: 'Weird & wonderful', play: 'Play along', reactive: 'Trending' };

// An Instagram post from the planned calendar (services/ig_backlog.py): the day it is meant for, its pillar, the
// image (or the note's finding, for a text post), and the caption to paste.
const IgPackCard = ({ pack, client, onChanged, toast }) => {
  const facts = pack.facts || {};
  const imageUrl = pack.snapshot_id ? `${siteOrigin()}/img/${pack.snapshot_id}.png` : null;
  const copy = async (text, what) => {
    try { await navigator.clipboard.writeText(text); toast(`${what} copied`); } catch { toast('Copy blocked'); }
  };
  const update = async (body, done) => {
    try { await client.patch(`/admin/content/packs/${pack.id}`, body); toast(done); onChanged(); }
    catch (err) { toast(apiErrorText(err, null) || 'Update failed'); }
  };
  const day = pack.planned_for
    ? new Date(`${pack.planned_for}T12:00:00`).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' })
    : 'Bench (fills an open day)';
  return (
    <Box sx={{ bgcolor: C.card, border: `1px solid ${C.line}`, borderRadius: 3, p: 2, mb: 2 }}>
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mb: 1, flexWrap: 'wrap' }}>
        <Typography sx={{ fontSize: 13, color: pack.planned_for ? C.hi : C.lo, fontWeight: 700 }}>{day}</Typography>
        <Chip size="small" label={PILLAR_LABELS[pack.pillar] || pack.pillar} sx={{ bgcolor: '#1d212b', color: C.mid }} />
      </Box>
      {imageUrl ? (
        <Box component="img" src={imageUrl} alt={pack.title} loading="lazy"
          sx={{ display: 'block', width: '100%', maxWidth: 420, aspectRatio: '4 / 5', borderRadius: 2, bgcolor: '#14171e', border: `1px solid ${C.line}` }} />
      ) : (
        <Box sx={{ p: 2, maxWidth: 420, borderRadius: 2, bgcolor: '#14171e', border: `1px solid ${C.line}` }}>
          <Typography sx={{ fontSize: 18, fontWeight: 700, color: C.hi }}>{pack.title}</Typography>
          {facts.finding && <Typography sx={{ fontSize: 14, color: C.mid, mt: 1 }}>{facts.finding}</Typography>}
          <Typography sx={{ fontSize: 12, color: C.lo, mt: 1 }}>Text carousel: slides come with the carousel export.</Typography>
        </Box>
      )}
      {imageUrl && (
        <Box sx={{ display: 'flex', gap: 1, mt: 1.5, flexWrap: 'wrap' }}>
          <Button variant="contained" onClick={() => shareImage(imageUrl, `hindsight-${pack.snapshot_id}.png`, pack.title, pack.title)}
            sx={{ bgcolor: C.lime, color: C.bg, fontWeight: 700, minHeight: 44, '&:hover': { bgcolor: '#a3dc3f' } }}>
            Share image
          </Button>
          <Button variant="outlined" href={`${imageUrl}?download=1`} sx={{ color: C.hi, borderColor: C.line, minHeight: 44 }}>Download</Button>
        </Box>
      )}
      <CopyBlock label="Caption" text={pack.caption || pack.title} onCopy={copy} multiline />
      {(pack.rule_warnings || []).map((w) => (
        <Typography key={w} sx={{ fontSize: 12, color: C.amber, mt: 0.5 }}>⚠ {w}</Typography>
      ))}
      {pack.status === 'ready' ? (
        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
          <Button variant="outlined" onClick={() => update({ status: 'posted' }, 'Marked posted')} sx={{ color: C.hi, borderColor: C.line, minHeight: 40, flex: 1 }}>Mark posted</Button>
          <Button variant="outlined" onClick={() => update({ status: 'skipped' }, 'Skipped')} sx={{ color: C.lo, borderColor: C.line, minHeight: 40, flex: 1 }}>Skip</Button>
        </Box>
      ) : (
        <Typography sx={{ mt: 1.5, fontSize: 12, color: C.lo }}>{pack.status}</Typography>
      )}
    </Box>
  );
};

const SocialTab = ({ client, toast, onAuthFail }) => {
  const [channel, setChannel] = useState('reddit');
  const [status, setStatus] = useState('ready');
  const [packs, setPacks] = useState(null);
  const [scanning, setScanning] = useState(false);

  const load = useCallback(async () => {
    setPacks(null);
    try {
      const { data } = await client.get('/admin/content/packs', { params: { status, channel } });
      setPacks(data.packs);
    } catch (err) {
      if (err.response?.status === 403 || err.response?.status === 404) onAuthFail();
      else toast('Could not load packs');
      setPacks([]);
    }
  }, [client, status, channel, toast, onAuthFail]);

  useEffect(() => { load(); }, [load]);

  const scan = async () => {
    setScanning(true);
    try {
      await client.post('/admin/content/generate', { days: 3 });
      toast('Scanning recent matches… new packs appear here in about a minute');
      setTimeout(load, 60000);
    } catch { toast('Scan failed'); }
    setScanning(false);
  };

  return (
    <>
      <Box sx={{ display: 'flex', gap: 0.75, mb: 1.5 }}>
        {[['reddit', 'Reddit / X'], ['instagram', 'Instagram']].map(([c, label]) => (
          <Chip key={c} label={label} onClick={() => setChannel(c)} variant={channel === c ? 'filled' : 'outlined'}
            sx={{ fontWeight: 700, color: channel === c ? C.bg : C.mid, bgcolor: channel === c ? C.hi : 'transparent', borderColor: C.line }} />
        ))}
      </Box>
      <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', alignItems: 'center', mb: 2 }}>
        {STATUSES.map((s) => (
          <Chip key={s} label={s} onClick={() => setStatus(s)}
            sx={{ textTransform: 'capitalize', bgcolor: status === s ? C.lime : '#1d212b', color: status === s ? C.bg : C.mid, fontWeight: 600 }} />
        ))}
        {channel === 'reddit' && (
          <Button size="small" onClick={scan} disabled={scanning} sx={{ ml: 'auto', color: C.lime }}>
            {scanning ? 'Scanning…' : 'Scan new matches'}
          </Button>
        )}
      </Box>
      {status === 'ready' && channel === 'reddit' && <IdeaBox client={client} toast={toast} onPackCreated={load} />}
      {packs === null && <CircularProgress size={22} sx={{ color: C.lime }} />}
      {packs && packs.length === 0 && (
        <Typography sx={{ color: C.lo, py: 4 }}>
          {status !== 'ready' ? `No ${status} packs.`
            : channel === 'instagram' ? 'No Instagram posts lined up. Run scripts/build_ig_backlog.py --write.'
              : 'No packs waiting. New ones arrive after the nightly load.'}
        </Typography>
      )}
      {(packs || []).map((p) => (channel === 'instagram'
        ? <IgPackCard key={p.id} pack={p} client={client} onChanged={load} toast={toast} />
        : <PackCard key={p.id} pack={p} client={client} onChanged={load} toast={toast} />))}
    </>
  );
};

const AdminPage = () => {
  const [token, setToken] = useState(readToken);
  const [draft, setDraft] = useState('');
  const [message, setMessage] = useState(null);
  const toast = useCallback((m) => setMessage(m), []);
  const client = React.useMemo(() => api(token), [token]);

  const save = () => {
    try { localStorage.setItem(TOKEN_KEY, draft.trim()); } catch { /* private mode: keep for this visit */ }
    setToken(draft.trim());
  };
  const signOut = useCallback(() => {
    try { localStorage.removeItem(TOKEN_KEY); } catch { /* ignore */ }
    setToken('');
  }, []);

  return (
    <Box sx={{ maxWidth: 560, mx: 'auto', px: 2, py: 2, color: C.hi }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          <Chip label="Social" sx={{ bgcolor: 'rgba(182,242,74,0.13)', color: C.lime, fontWeight: 700 }} />
          <Chip component={RouterLink} to="/admin/notes" clickable label="Notes" sx={{ bgcolor: '#1d212b', color: C.mid }} />
        </Box>
        {token && <Button size="small" onClick={signOut} sx={{ color: C.lo }}>Sign out</Button>}
      </Box>
      {!token ? (
        <Box component="form" onSubmit={(e) => { e.preventDefault(); save(); }} sx={{ display: 'flex', gap: 1 }}>
          <TextField size="small" type="password" fullWidth placeholder="Admin token" value={draft}
            onChange={(e) => setDraft(e.target.value)} sx={{ '& .MuiInputBase-root': { color: C.hi, bgcolor: '#14171e' } }} />
          <Button type="submit" variant="contained" sx={{ bgcolor: C.lime, color: C.bg, fontWeight: 700 }}>Open</Button>
        </Box>
      ) : (
        <SocialTab client={client} toast={toast} onAuthFail={() => { toast('Token rejected'); signOut(); }} />
      )}
      <Snackbar open={!!message} autoHideDuration={2500} onClose={() => setMessage(null)} message={message}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }} />
    </Box>
  );
};

export default AdminPage;
