// Hypothesis share cards (scripts/notes/render_cards.mjs) follow the share-image legibility floor:
// no text under MIN_FONT.footer px at 1080 wide. Run: node --test tests/js/hypothesis_cards.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { cardTree } from '../../scripts/notes/render_cards.mjs';
import { MIN_FONT } from '../../api/img.mjs';

function sizes(node, inherited, out = []) {
  if (node == null || node === false) return out;
  if (typeof node === 'string' || typeof node === 'number') {
    if (String(node).trim()) out.push({ text: String(node).slice(0, 30), size: inherited });
    return out;
  }
  if (Array.isArray(node)) { node.forEach((n) => sizes(n, inherited, out)); return out; }
  sizes(node.props?.children, node.props?.style?.fontSize ?? inherited, out);
  return out;
}

const spec = { footer: 'Data: Hindsight · hindsightcricket.com', credits: 'Cricsheet (ODC-By) · ...', cards: [] };
const cards = [
  { kind: 'claim', kicker: 'HYPOTHESIS LAB · H0', eyebrow: 'A common claim', title: 'x'.repeat(200), verdict: 'Partly',
    verdict_colour: 'amber', parts: [{ label: 'a. first over', value: 'Supported' }] },
  { kind: 'number', kicker: 'HYPOTHESIS LAB · H0', eyebrow: 'Q?', stat: '-0.60', stat_label: 'RAA per over', sub: '95% CI',
    rows: [{ label: 'mean_10+', value: '-0.20' }], verdict: 'Supported', verdict_colour: 'lime' },
];

for (const card of cards) {
  test(`${card.kind} card: all text at least ${MIN_FONT.footer}px, footer present`, () => {
    const tree = cardTree(spec, card);
    assert.equal(tree.props.style.width, 1080);
    assert.equal(tree.props.style.height, 1350);
    const all = sizes(tree, undefined);
    const small = all.filter((t) => !(t.size >= MIN_FONT.footer));
    assert.deepEqual(small, []);
    assert.ok(all.some((t) => t.text.startsWith('Data: Hindsight')));
  });
}
