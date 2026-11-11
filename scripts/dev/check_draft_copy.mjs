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
for (const id of ['a1b2c3d4', 'zz9y8x7w', 'k3k3k3k3']) {
  const a = app.deal(data.cards, `season-draft-${id}`); const b = copy.deal(data.cards, `season-draft-${id}`);
  const ba = app.bestFromDeal(a, data.roles, app.costTable(data.cards)); const bb = copy.bestFromDeal(b, data.roles, copy.costTable(data.cards));
  const ra = app.seasonResults(app.profile(ba), data.seasons, data.roles, id).filter((r) => r.made).length;
  const rb = copy.seasonResults(copy.profile(bb), data.seasons, data.roles, id).filter((r) => r.made).length;
  if (JSON.stringify(a.map((s) => s.map((c) => c.name))) !== JSON.stringify(b.map((s) => s.map((c) => c.name))) || ra !== rb) {
    console.error(`MISMATCH on ${id}`); process.exit(1);
  }
  console.log(`${id}: same deal, best XI ${ra}/19 both, ${app.checkPicks(ba, app.costTable(data.cards)).spent} credits`);
}
