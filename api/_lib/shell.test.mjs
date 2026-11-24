// node --test api/_lib/shell.test.mjs
// Checks the crawler root replacement against the BUILT index.html (minified, comments stripped) when a build exists,
// and against public/index.html otherwise. Run `npm run build` first for the real check.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { ROOT, rootFor } from './shell.mjs';

const repo = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const built = join(repo, 'build', 'index.html');
const source = join(repo, 'public', 'index.html');
const html = readFileSync(existsSync(built) ? built : source, 'utf8');

test(`the shell is in #root (${existsSync(built) ? 'build' : 'public'}/index.html)`, () => {
  assert.match(html, /id="shell"/);
  assert.match(html, ROOT);
});

test('a crawler body replaces the whole root, shell included', () => {
  const out = rootFor(html, '/notes/x', '<article>NOTE</article>');
  assert.ok(out.includes('<div id="root"><article>NOTE</article></div>'));
  assert.ok(!out.includes('id="shell"'));
  assert.ok(out.includes('</body>'));
});

test('other pages drop the shell; the home page keeps it', () => {
  assert.ok(!rootFor(html, '/player', null).includes('id="shell"'));
  assert.ok(rootFor(html, '/player', null).includes('<div id="root"></div>'));
  assert.equal(rootFor(html, '/', null), html);
});

test('an older, empty root still matches', () => {
  assert.equal(rootFor('<body><div id="root"></div></body>', '/notes', 'B'), '<body><div id="root">B</div></body>');
});
