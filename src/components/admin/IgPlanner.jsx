import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, Chip, CircularProgress, Typography } from '@mui/material';
import ExpandMoreRoundedIcon from '@mui/icons-material/ExpandMoreRounded';
import config from '../../config';
import { apiErrorText } from '../../utils/apiError';
import { fetchImageFiles, shareFiles, siteOrigin } from '../ui/ChartExportButton';

/**
 * The Instagram tab of /admin as a day list: one row per day with each post's time, kind and topic, and a tick per
 * platform it has gone out on. Tap a post to open it: tabs for Instagram (slides, caption), Reel & YouTube (the video,
 * the Short's title and description) and X (the thread, one slide per tweet, services/ig_x.py). Changes update the
 * post in place; nothing reloads the list.
 *
 * Days and their posts come from GET /admin/content/plan (services/ig_plan.py picks a day's posts, e.g. one trending
 * post); the posts themselves from GET /admin/content/packs?status=all.
 */
export const C = { bg: '#0a0c11', card: '#12151c', line: 'rgba(255,255,255,.08)', hi: '#f3f4f6', mid: '#c3c8d0', lo: '#9aa1ac', lime: '#b6f24a', red: '#e5484d', amber: '#f0b429' };
const KIND_LABELS = { preview: 'Preview', recap: 'Recap', trend: 'Trending', debate: 'Debate', myth: 'Myth', play: 'Play along', weird: 'Weird', record: 'Record' };
const PLATFORMS = [['instagram', 'IG'], ['youtube', 'YT'], ['x', 'X']];
const TABS = [['instagram', 'Instagram'], ['video', 'Reel · YouTube'], ['x', 'X thread']];

// The plan's days are Indian days (routers/content.py instagram_plan).
const todayIso = () => new Date(Date.now() + 5.5 * 3600000).toISOString().slice(0, 10);
const dayLabel = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' });

const SectionLabel = ({ children, sx }) => (
  <Typography sx={{ fontSize: 11, letterSpacing: '.12em', textTransform: 'uppercase', color: C.lo, ...sx }}>{children}</Typography>
);

const CopyRow = ({ label, text, onCopy, multiline }) => (
  <Box sx={{ mt: 1.5 }}>
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
      <SectionLabel>{label}</SectionLabel>
      <Button size="small" onClick={() => onCopy(text, label)} sx={{ color: C.lime, minHeight: 32, fontWeight: 700 }}>Copy</Button>
    </Box>
    <Typography sx={{ fontSize: multiline ? 13 : 15, fontWeight: multiline ? 400 : 600, color: multiline ? C.mid : C.hi,
      whiteSpace: 'pre-wrap', lineHeight: 1.4, overflowWrap: 'anywhere' }}>
      {text}
    </Typography>
  </Box>
);

const slideUrlsOf = (pack) => {
  const facts = pack.facts || {};
  if (facts.carousel_id) {
    return Array.from({ length: facts.slides || 1 }, (_, i) => `${siteOrigin()}/img/${facts.carousel_id}.png?slide=${i + 1}`);
  }
  return pack.snapshot_id ? [`${siteOrigin()}/img/${pack.snapshot_id}.png`] : [];
};

/** A tick per platform; tapping one marks the post done (or not) there. */
const PlatformTicks = ({ postedOn, onToggle, size = 'small' }) => (
  <Box sx={{ display: 'flex', gap: 0.5 }}>
    {PLATFORMS.map(([p, label]) => {
      const done = postedOn.includes(p);
      return (
        <Box key={p} component={onToggle ? 'button' : 'span'} type={onToggle ? 'button' : undefined}
          onClick={onToggle ? (e) => { e.stopPropagation(); onToggle(p); } : undefined}
          aria-label={onToggle ? `${done ? 'Unmark' : 'Mark'} posted on ${label}` : undefined}
          sx={{ fontSize: size === 'small' ? 10 : 12, fontWeight: 700, px: size === 'small' ? 0.6 : 1, py: size === 'small' ? 0.1 : 0.5,
            borderRadius: 1, border: `1px solid ${done ? C.lime : C.line}`, color: done ? C.bg : C.lo,
            bgcolor: done ? C.lime : 'transparent', cursor: onToggle ? 'pointer' : 'default', fontFamily: 'inherit' }}>
          {done ? '✓ ' : ''}{label}
        </Box>
      );
    })}
  </Box>
);

const SlideStrip = ({ urls, title }) => (
  <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', scrollSnapType: 'x mandatory', pb: 0.5 }}>
    {urls.map((u, i) => (
      <Box key={u} component="a" href={`${u}&download=1`} target="_blank" rel="noopener noreferrer"
        sx={{ flex: '0 0 auto', width: urls.length > 1 ? '62%' : '100%', maxWidth: 280, scrollSnapAlign: 'start' }}>
        <Box component="img" src={u} alt={`${title} · slide ${i + 1}`} loading="lazy"
          sx={{ display: 'block', width: '100%', aspectRatio: '4 / 5', borderRadius: 2, bgcolor: '#14171e', border: `1px solid ${C.line}` }} />
      </Box>
    ))}
  </Box>
);

// Sharing files has to happen inside a tap (iOS), and fetching them first can outlast it: the first tap fetches,
// the second opens the share sheet.
const useTwoTapShare = (load, title, toast) => {
  const [files, setFiles] = useState(null);
  const [busy, setBusy] = useState(false);
  const tap = async () => {
    if (files) {
      const shared = await shareFiles(files, title);
      if (shared === 'downloaded') toast(`${files.length} file${files.length > 1 ? 's' : ''} downloaded`);
      return;
    }
    setBusy(true);
    try { setFiles(await load()); } catch { toast('Could not load the files'); }
    setBusy(false);
  };
  return { files, busy, tap };
};

const InstagramTab = ({ pack, copy, toast }) => {
  const urls = slideUrlsOf(pack);
  const facts = pack.facts || {};
  const { files, busy, tap } = useTwoTapShare(
    () => fetchImageFiles(urls, `hindsight-${facts.carousel_id || pack.snapshot_id}`), pack.title, toast);
  return (
    <>
      <SlideStrip urls={urls} title={pack.title} />
      {urls.length > 0 && (
        <Box sx={{ display: 'flex', gap: 1, mt: 1.5, alignItems: 'center', flexWrap: 'wrap' }}>
          <Button variant="contained" onClick={tap} disabled={busy}
            sx={{ bgcolor: C.lime, color: C.bg, fontWeight: 700, minHeight: 44, '&:hover': { bgcolor: '#a3dc3f' } }}>
            {busy ? 'Loading slides…' : files ? `Share ${files.length} slide${files.length > 1 ? 's' : ''}` : 'Get slides'}
          </Button>
          <Typography sx={{ fontSize: 12, color: C.lo }}>{files ? 'Pick Instagram in the share sheet' : 'Tap a slide to save just that one'}</Typography>
        </Box>
      )}
      <CopyRow label="Caption" text={pack.caption || pack.title} onCopy={copy} multiline />
    </>
  );
};

const VideoTab = ({ pack, copy, toast }) => {
  const id = (pack.facts || {}).carousel_id;
  const yt = (pack.facts || {}).youtube;
  const { files, busy, tap } = useTwoTapShare(async () => {
    const res = await fetch(`${config.API_URL}/snapshots/${id}/reel.mp4`);
    if (!res.ok) throw new Error('no reel');
    return [new File([await res.blob()], `hindsight-${id}.mp4`, { type: 'video/mp4' })];
  }, pack.title, toast);
  if (!id) return <Typography sx={{ fontSize: 13, color: C.lo }}>This post has no carousel, so no Reel.</Typography>;
  return (
    <>
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
        <Button variant="contained" onClick={tap} disabled={busy}
          sx={{ bgcolor: C.lime, color: C.bg, fontWeight: 700, minHeight: 44, '&:hover': { bgcolor: '#a3dc3f' } }}>
          {busy ? 'Loading reel…' : files ? 'Share reel' : 'Get reel'}
        </Button>
        <Typography sx={{ fontSize: 12, color: C.lo }}>Same video for an Instagram Reel and a YouTube Short</Typography>
      </Box>
      {yt ? (
        <>
          <CopyRow label="YouTube Short · title" text={yt.title} onCopy={copy} />
          <CopyRow label="YouTube Short · description" text={yt.description} onCopy={copy} multiline />
        </>
      ) : <Typography sx={{ fontSize: 13, color: C.lo, mt: 1.5 }}>YouTube copy arrives with the next nightly run.</Typography>}
    </>
  );
};

/** One tweet: its slide, its text; "Copy text" also fetches the image, then "Share image" sends it. */
const Tweet = ({ tweet, total, url, copy, toast }) => {
  const { files, busy, tap } = useTwoTapShare(() => fetchImageFiles([url], `hindsight-tweet-${tweet.n}`), `Tweet ${tweet.n}`, toast);
  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: 1.25, py: 1.25, borderTop: `1px solid ${C.line}` }}>
      <Box component="img" src={url} alt={`Slide ${tweet.slide}`} loading="lazy"
        sx={{ width: 72, aspectRatio: '4 / 5', borderRadius: 1, border: `1px solid ${C.line}`, bgcolor: '#14171e' }} />
      <Box sx={{ minWidth: 0 }}>
        <SectionLabel>{tweet.n === 1 ? 'Tweet 1 · the post' : `Reply ${tweet.n - 1} of ${total - 1}`}</SectionLabel>
        <Typography sx={{ fontSize: 13, color: C.hi, whiteSpace: 'pre-wrap', lineHeight: 1.4, overflowWrap: 'anywhere', mt: 0.5 }}>
          {tweet.text}
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, mt: 0.75 }}>
          <Button size="small" onClick={() => copy(tweet.text, `Tweet ${tweet.n}`)} sx={{ color: C.lime, fontWeight: 700, minHeight: 36, px: 0 }}>Copy text</Button>
          <Button size="small" onClick={tap} disabled={busy} sx={{ color: C.mid, minHeight: 36 }}>
            {busy ? 'Loading…' : files ? 'Share image' : 'Get image'}
          </Button>
        </Box>
      </Box>
    </Box>
  );
};

const XTab = ({ pack, copy, toast }) => {
  const thread = (pack.facts || {}).x;
  const urls = slideUrlsOf(pack);
  if (!thread) return <Typography sx={{ fontSize: 13, color: C.lo }}>The X thread arrives with the next nightly run.</Typography>;
  return (
    <>
      <Typography sx={{ fontSize: 12, color: C.lo }}>
        Post tweet 1 with its image, then reply to it with each next tweet. Copy the text, then share the image into the
        same reply.
      </Typography>
      {thread.map((t) => <Tweet key={t.n} tweet={t} total={thread.length} url={urls[t.slide - 1]} copy={copy} toast={toast} />)}
    </>
  );
};

const PostDetail = ({ pack, onUpdate, copy, toast }) => {
  const [tab, setTab] = useState('instagram');
  const facts = pack.facts || {};
  const postedOn = facts.posted_on || [];
  return (
    <Box sx={{ pt: 1.5 }}>
      <Box sx={{ display: 'flex', gap: 0.75, mb: 1.5, flexWrap: 'wrap' }}>
        {TABS.map(([key, label]) => (
          <Chip key={key} label={label} onClick={() => setTab(key)}
            size="small" sx={{ fontWeight: 700, bgcolor: tab === key ? C.hi : '#1d212b', color: tab === key ? C.bg : C.mid }} />
        ))}
      </Box>
      {tab === 'instagram' && <InstagramTab pack={pack} copy={copy} toast={toast} />}
      {tab === 'video' && <VideoTab pack={pack} copy={copy} toast={toast} />}
      {tab === 'x' && <XTab pack={pack} copy={copy} toast={toast} />}
      {pack.post_by && (
        <Typography sx={{ fontSize: 12, color: C.amber, mt: 1.5 }}>
          News until {new Date(pack.post_by).toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
        </Typography>
      )}
      {facts.note_id && (
        <Typography sx={{ fontSize: 13, mt: 1.5 }}>
          <Box component={RouterLink} to={`/admin/notes?open=${facts.note_id}`} sx={{ color: C.lime }}>
            Its note for Google search: review and publish
          </Box>
        </Typography>
      )}
      {(pack.rule_warnings || []).map((w) => <Typography key={w} sx={{ fontSize: 12, color: C.amber, mt: 0.5 }}>⚠ {w}</Typography>)}
      <Box sx={{ mt: 2, pt: 1.5, borderTop: `1px solid ${C.line}` }}>
        <SectionLabel sx={{ mb: 0.75 }}>Posted on · tap to tick</SectionLabel>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <PlatformTicks postedOn={postedOn} size="large" onToggle={(p) => {
            const next = postedOn.includes(p) ? postedOn.filter((x) => x !== p) : [...postedOn, p];
            // Instagram is the post of record: ticking it marks the post posted, unticking puts it back to ready.
            const status = p === 'instagram' ? (next.includes('instagram') ? 'posted' : 'ready') : undefined;
            onUpdate(pack, { posted_on: next, ...(status && status !== pack.status ? { status } : {}) });
          }} />
          {pack.status === 'ready' && (
            <Button size="small" onClick={() => onUpdate(pack, { status: 'skipped' })} sx={{ color: C.lo, ml: 'auto' }}>Skip</Button>
          )}
          {pack.status === 'skipped' && (
            <Button size="small" onClick={() => onUpdate(pack, { status: 'ready' })} sx={{ color: C.lo, ml: 'auto' }}>Un-skip</Button>
          )}
        </Box>
      </Box>
    </Box>
  );
};

/** One post's line in a day: time, kind, topic and its ticks; tap to open. */
const PostRow = ({ pack, time, open, onToggle, onUpdate, copy, toast }) => {
  const postedOn = (pack.facts || {}).posted_on || (pack.status === 'posted' ? ['instagram'] : []);
  const dim = pack.status === 'skipped' || pack.status === 'expired';
  return (
    <Box sx={{ borderTop: `1px solid ${C.line}` }}>
      <Box component="button" type="button" onClick={onToggle} aria-expanded={open}
        sx={{ width: '100%', display: 'grid', gridTemplateColumns: '1fr auto', gap: 1, alignItems: 'center', py: 1.1, px: 0,
          bgcolor: 'transparent', border: 0, textAlign: 'left', cursor: 'pointer', color: 'inherit', fontFamily: 'inherit' }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography sx={{ fontSize: 12, color: C.lo }}>
            <Box component="span" sx={{ color: pack.status === 'posted' ? C.lime : C.amber, fontWeight: 700 }}>{time || '—'}</Box>
            {' · '}{KIND_LABELS[pack.kind] || pack.kind}{dim ? ` · ${pack.status}` : ''}
          </Typography>
          <Typography sx={{ fontSize: 14, fontWeight: 600, color: dim ? C.lo : C.hi, lineHeight: 1.35, mt: 0.25,
            textDecoration: dim ? 'line-through' : 'none' }}>
            {pack.title}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <PlatformTicks postedOn={postedOn} />
          <ExpandMoreRoundedIcon sx={{ color: C.lo, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform .15s' }} />
        </Box>
      </Box>
      {open && <PostDetail pack={{ ...pack, facts: { ...(pack.facts || {}), posted_on: postedOn } }} onUpdate={onUpdate} copy={copy} toast={toast} />}
    </Box>
  );
};

const Day = ({ label, isToday, posts, empty, openId, setOpenId, ...rest }) => (
  <Box sx={{ bgcolor: C.card, border: `1px solid ${isToday ? 'rgba(182,242,74,.35)' : C.line}`, borderRadius: 3, px: 1.75, pt: 1.25, pb: 0.5, mb: 1.25 }}>
    <Typography sx={{ fontSize: 13, fontWeight: 700, color: isToday ? C.lime : C.hi, pb: 0.75 }}>{isToday ? `Today · ${label}` : label}</Typography>
    {posts.length === 0 && <Typography sx={{ fontSize: 13, color: C.lo, pb: 1 }}>{empty || 'Open: a trending or bench post'}</Typography>}
    {posts.map(({ pack, time }) => (
      <PostRow key={pack.id} pack={pack} time={time} open={openId === pack.id}
        onToggle={() => setOpenId(openId === pack.id ? null : pack.id)} {...rest} />
    ))}
  </Box>
);

/** A collapsed group (Earlier, Later, Bench, Comment kit): a header line that opens it. */
const Fold = ({ title, count, children }) => {
  const [open, setOpen] = useState(false);
  return (
    <Box sx={{ mb: 1.25 }}>
      <Box component="button" type="button" onClick={() => setOpen(!open)} aria-expanded={open}
        sx={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', py: 1, px: 0.25,
          bgcolor: 'transparent', border: 0, cursor: 'pointer', color: C.mid, fontFamily: 'inherit' }}>
        <SectionLabel>{title}{count != null ? ` · ${count}` : ''}</SectionLabel>
        <ExpandMoreRoundedIcon sx={{ color: C.lo, transform: open ? 'rotate(180deg)' : 'none' }} />
      </Box>
      {open && children}
    </Box>
  );
};

const IgPlanner = ({ client, toast, onAuthFail }) => {
  const [packs, setPacks] = useState(null);
  const [plan, setPlan] = useState(null);
  const [openId, setOpenId] = useState(null);

  const load = useCallback(async () => {
    try {
      const [p, w] = await Promise.all([
        client.get('/admin/content/packs', { params: { status: 'all', channel: 'instagram', limit: 200 } }),
        client.get('/admin/content/plan'),
      ]);
      setPacks(p.data.packs);
      setPlan(w.data);
    } catch (err) {
      if (err.response?.status === 403 || err.response?.status === 404) onAuthFail();
      else toast('Could not load the plan');
      setPacks([]);
      setPlan({ week: [], comment_kit: [] });
    }
  }, [client, toast, onAuthFail]);
  useEffect(() => { load(); }, [load]);

  const copy = useCallback(async (text, what) => {
    try { await navigator.clipboard.writeText(text); toast(`${what} copied`); } catch { toast('Copy blocked'); }
  }, [toast]);

  // Change one post in place: show it at once, send it, and put it back if the server says no.
  const onUpdate = useCallback(async (pack, body) => {
    const before = pack;
    const after = { ...pack, ...(body.status ? { status: body.status } : {}),
      facts: { ...(pack.facts || {}), ...(body.posted_on ? { posted_on: body.posted_on } : {}) } };
    setPacks((list) => list.map((p) => (p.id === pack.id ? after : p)));
    try {
      await client.patch(`/admin/content/packs/${pack.id}`, body);
    } catch (err) {
      setPacks((list) => list.map((p) => (p.id === pack.id ? before : p)));
      toast(apiErrorText(err, null) || 'Update failed');
    }
  }, [client, toast]);

  const view = useMemo(() => {
    if (!packs || !plan) return null;
    const byId = Object.fromEntries(packs.map((p) => [p.id, p]));
    const today = todayIso();
    const weekDays = plan.week.map((d) => ({
      date: d.date,
      posts: d.posts.map((p) => ({ pack: byId[p.id], time: p.time })).filter((x) => x.pack),
    }));
    const inWeek = new Set(weekDays.map((d) => d.date));
    const lastWeekDay = weekDays.length ? weekDays[weekDays.length - 1].date : today;
    const later = {};
    const earlier = {};
    packs.forEach((p) => {
      if (!p.planned_for || inWeek.has(p.planned_for)) return;
      if (p.planned_for > lastWeekDay && p.status === 'ready') (later[p.planned_for] ||= []).push({ pack: p, time: p.time });
      else if (p.planned_for < today && p.status === 'posted') (earlier[p.planned_for] ||= []).push({ pack: p, time: p.time });
    });
    const bench = packs.filter((p) => !p.planned_for && p.status === 'ready');
    return { today, weekDays, later, earlier, bench };
  }, [packs, plan]);

  if (!view) return <CircularProgress size={22} sx={{ color: C.lime }} />;
  const dayProps = { openId, setOpenId, onUpdate, copy, toast };
  const groups = (obj, sort) => Object.keys(obj).sort(sort).map((d) => (
    <Day key={d} label={dayLabel(d)} posts={obj[d]} {...dayProps} />
  ));

  return (
    <>
      {plan.comment_kit.length > 0 && (
        <Fold title="Comment kit · a stat under big accounts' posts, no links" count={plan.comment_kit.length}>
          {plan.comment_kit.map((k) => (
            <Box key={k} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, py: 0.5 }}>
              <Typography sx={{ flex: 1, fontSize: 13, color: C.hi, lineHeight: 1.4 }}>{k}</Typography>
              <Button size="small" onClick={() => copy(k, 'Comment')} sx={{ color: C.lime, minWidth: 0, fontWeight: 700 }}>Copy</Button>
            </Box>
          ))}
        </Fold>
      )}
      {Object.keys(view.earlier).length > 0 && (
        <Fold title="Earlier" count={Object.values(view.earlier).flat().length}>{groups(view.earlier, (a, b) => b.localeCompare(a))}</Fold>
      )}
      {view.weekDays.map((d) => (
        <Day key={d.date} label={dayLabel(d.date)} isToday={d.date === view.today} posts={d.posts} {...dayProps} />
      ))}
      {Object.keys(view.later).length > 0 && (
        <Fold title="Later" count={Object.values(view.later).flat().length}>{groups(view.later)}</Fold>
      )}
      {view.bench.length > 0 && (
        <Fold title="Bench · fills an open day" count={view.bench.length}>
          <Day label="Not scheduled" posts={view.bench.map((p) => ({ pack: p, time: null }))} {...dayProps} />
        </Fold>
      )}
    </>
  );
};

export default IgPlanner;
