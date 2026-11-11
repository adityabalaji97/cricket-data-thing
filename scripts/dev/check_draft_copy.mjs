// The link previews' copy of the draft engine (api/_lib/draftEngine.mjs) gives the same deal and score as the app's
// (src/utils/draftEngine.js): run after changing either.   node scripts/dev/check_draft_copy.mjs
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const dir = mkdtempSync(join(tmpdir(), 'draft-'));
writeFileSync(join(dir, 'app.mjs'), readFileSync(new URL('../../src/utils/draftEngine.js', import.meta.url)));
const app = await import(join(dir, 'app.mjs'));
const copy = await import(new URL('../../api/_lib/draftEngine.mjs', import.meta.url));
const data = JSON.parse(readFileSync(new URL('../../services/pinned/season_draft_IPL.json', import.meta.url)));
for (const day of ['2026-11-12', '2026-11-13', '2026-12-16']) {
  const a = app.deal(data.cards, `season-draft-${day}`); const b = copy.deal(data.cards, `season-draft-${day}`);
  const picks = a.map((s) => s[1]);
  const ra = app.seasonResults(app.profile(picks), data.seasons, data.roles).filter((r) => r.made).length;
  const rb = copy.seasonResults(copy.profile(b.map((s) => s[1])), data.seasons, data.roles).filter((r) => r.made).length;
  if (JSON.stringify(a.map((s) => s.map((c) => c.name))) !== JSON.stringify(b.map((s) => s.map((c) => c.name))) || ra !== rb) {
    console.error(`MISMATCH on ${day}`); process.exit(1);
  }
  console.log(`${day}: same deal, ${ra}/19 both`);
}
