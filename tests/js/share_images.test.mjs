// Share images (api/img.mjs) must stay legible in a phone feed: every text node in the
// feed-sized templates (portrait 4:5 and square) is at least MIN_FONT.footer at 1080px wide,
// which is ~9.5pt on a 390px phone. Run: node --test tests/js/share_images.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { renderSnapshot, SIZES, MIN_FONT } from '../../api/img.mjs';

const fixtures = JSON.parse(readFileSync(new URL('./snapshot_fixtures.json', import.meta.url), 'utf8'));

// Walk the element tree, carrying the inherited fontSize down to every text child.
function textSizes(node, inherited, out = []) {
  if (node == null || node === false) return out;
  if (typeof node === 'string' || typeof node === 'number') {
    if (String(node).trim()) out.push({ text: String(node).slice(0, 40), size: inherited });
    return out;
  }
  if (Array.isArray(node)) { node.forEach((n) => textSizes(n, inherited, out)); return out; }
  if (node.type === 'svg') return out; // chart geometry, no text
  const size = node.props?.style?.fontSize ?? inherited;
  textSizes(node.props?.children, size, out);
  return out;
}

for (const kind of Object.keys(fixtures)) {
  for (const sizeName of ['portrait', 'square']) {
    test(`${kind} @ ${sizeName}: all text at least ${MIN_FONT.footer}px, headline at least ${MIN_FONT.headline}px`, () => {
      const tree = renderSnapshot(fixtures[kind], sizeName);
      const sizes = textSizes(tree, undefined);
      assert.ok(sizes.length > 3, 'template rendered no text');
      for (const { text, size } of sizes) {
        assert.ok(size >= MIN_FONT.footer, `"${text}" is ${size}px`);
      }
      assert.ok(SIZES[sizeName].headline >= MIN_FONT.headline);
    });
  }
}
