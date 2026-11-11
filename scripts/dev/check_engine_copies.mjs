// The link previews run copies of the app's engines (api/_lib/*.mjs; Vercel functions can't import the app's src as
// ESM). Each copy must be its source plus a two-line header. Run after changing either:
//   node scripts/dev/check_engine_copies.mjs
import { readFileSync } from 'node:fs';

const PAIRS = [['src/utils/draftEngine.js', 'api/_lib/draftEngine.mjs'], ['src/utils/xiEngine.js', 'api/_lib/xiEngine.mjs']];
let bad = 0;
for (const [src, copy] of PAIRS) {
  const a = readFileSync(new URL(`../../${src}`, import.meta.url), 'utf8');
  const b = readFileSync(new URL(`../../${copy}`, import.meta.url), 'utf8').split('\n').slice(2).join('\n');
  if (a !== b) { console.error(`DIFFERS: ${copy} is not ${src}; recopy it`); bad += 1; } else console.log(`same: ${copy}`);
}
process.exit(bad ? 1 : 0);
