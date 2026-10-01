// node --test tests/js/notes_render.test.mjs
// The note renderer shared by the site and crawlers: sanitising, chart fences, bot HTML.
import test from 'node:test';
import assert from 'node:assert/strict';
import { markdownToHtml, plainExcerpt, splitBody } from '../../src/components/notes/noteMarkdown.mjs';
import { chartHtml, noteArticleHtml } from '../../api/_lib/note_html.mjs';

test('raw HTML is shown as text and unsafe links are dropped', () => {
  const html = markdownToHtml('Hi <script>alert(1)</script> [x](javascript:alert(1)) [y](https://espn.com) [z](/query?a=1) ![i](http://x/a.png)');
  assert.ok(!html.includes('<script>'));
  assert.ok(html.includes('&lt;script&gt;'));
  assert.ok(!html.includes('javascript:'));
  assert.ok(html.includes('href="https://espn.com" target="_blank" rel="noopener noreferrer"'));
  assert.ok(html.includes('<a href="/query?a=1">z</a>'));
  assert.ok(!html.includes('<img'));
});

test('body headings start at h2 (the page title is the h1)', () => {
  assert.match(markdownToHtml('# Big'), /<h2>Big<\/h2>/);
});

test('chart fences split out in order; other code fences stay markdown', () => {
  const body = 'A\n\n```hindsight\nchart: Abc123XYZ\n```\n\n```js\nchart: Nope12345\n```\n\nB';
  const parts = splitBody(body);
  assert.deepEqual(parts.map((p) => p.type), ['md', 'chart', 'md']);
  assert.equal(parts[1].id, 'Abc123XYZ');
  assert.ok(parts[2].text.includes('Nope12345'));
});

test('excerpt skips headings and markdown syntax', () => {
  assert.equal(plainExcerpt('## Head\n\n**Gill** and [Kohli](/x) added 200.'), 'Gill and Kohli added 200.');
});

test('crawler view renders query charts as tables, batter wickets left out', () => {
  const chart = {
    kind: 'query', title: 'IPL batters by strike rate',
    data: { group_by: ['batter'], chart: { metric: 'strike_rate' }, metric_columns: ['runs', 'balls', 'strike_rate', 'wickets'],
      rows: [{ batter: 'A <b>', runs: 10, balls: 5, strike_rate: 200, wickets: 1 }], hindsight_url: 'https://hindsightcricket.com/query?x=1' },
  };
  const html = chartHtml(chart, 'https://hindsightcricket.com');
  assert.ok(html.includes('<th>Batter</th><th>Strike rate</th><th>Runs</th><th>Balls</th>'));
  assert.ok(!html.includes('Wickets'));
  assert.ok(html.includes('A &lt;b&gt;'));
  assert.ok(html.includes('Open the live chart'));
});

test('crawler article carries title, byline, body and charts; dollar signs survive', () => {
  const note = {
    title: 'T', dek: 'D', kind: 'recap', match_id: '42', published_at: '2026-10-01T10:00:00Z',
    author: { name: 'Hindsight Bot', is_bot: true },
    body_md: "Won by $1 & 10 runs ($' $&)\n\n```hindsight\nchart: Abc123XYZ\n```",
    charts: { Abc123XYZ: { kind: 'recap', title: 'R', data: { recap: { headline: 'H', bullets: ['b1'] } } } },
  };
  const html = noteArticleHtml(note, 'https://hindsightcricket.com');
  assert.ok(html.includes('<h1>T</h1>'));
  assert.ok(html.includes('an AI analyst'));
  assert.ok(html.includes("$1 &amp; 10 runs ($&#39; $&amp;)") || html.includes("$1 &amp; 10 runs ($' $&amp;)"));
  assert.ok(html.includes('<li>b1</li>'));
  assert.ok(html.includes('/scorecard/42'));
});
