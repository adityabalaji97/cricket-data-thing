// What only the drawn slide can show (SOCIAL_RULES_ENFORCEMENT_PLAN.md chunk 1): run in the page once a slide is
// ready, it measures the card and returns [{rule, message}] (rule ids: services/social_rules.LAYOUT_RULES).
//
//   title_lines    the title runs past 2 lines            title_clipped  the title is cut off (3-line clamp)
//   footer_lines   the scope line wraps                   legend         a legend chip that's a sentence
//   text_clipped   a label is cut short with "…"          label_outside  a chart label cut off by what clips it
//   label_overlap  two chart labels sit on each other     card_overflow  the chart doesn't fit its card
//   small_chart    the chart gets under 35% of the card
//
// Elements are found by the data attributes StoryCard and the Legend components carry (data-card-title,
// data-card-footer, data-legend, data-story-chart, data-story-card).
export const LAYOUT_CHECK = `(() => {
  const root = document.querySelector('[data-ig-slide]');
  if (!root) return '[]';
  const out = [];
  const add = (rule, message) => { if (out.filter((f) => f.rule === rule).length < 3) out.push({ rule, message }); };
  const lines = (el) => {
    const lh = parseFloat(getComputedStyle(el).lineHeight) || parseFloat(getComputedStyle(el).fontSize) * 1.2;
    return Math.round(el.scrollHeight / lh);
  };
  const short = (t) => { t = (t || '').trim().replace(/\\s+/g, ' '); return t.length > 40 ? t.slice(0, 39) + '…' : t; };

  const title = root.querySelector('[data-card-title]');
  if (title) {
    const n = lines(title);
    if (n > 2) add('title_lines', 'the title runs to ' + n + ' lines (2 at most)');
    if (title.scrollHeight > title.clientHeight + 2) add('title_clipped', 'the title is cut off');
  }
  const footer = root.querySelector('[data-card-footer]');
  if (footer && lines(footer) > 1) add('footer_lines', 'the scope line wraps to ' + lines(footer) + ' lines');
  // Legends are colour chips, not sentences (docs/social_rules.md, Card anatomy): flag a chip that's a sentence.
  for (const lg of root.querySelectorAll('[data-legend]')) {
    for (const item of lg.children) {
      const t = (item.textContent || '').trim();
      if (t.split(/\s+/).length > 4 || t.length > 30) add('legend', 'a legend that is a sentence: "' + short(t) + '"');
    }
  }
  if (root.querySelector('[data-story-card][data-overflow="true"]')) add('card_overflow', "the chart doesn't fit its card");

  const card = root.querySelector('[data-story-card]');
  const chart = root.querySelector('[data-story-chart]');
  if (card && chart && chart.getBoundingClientRect().height < 0.35 * card.getBoundingClientRect().height) {
    add('small_chart', 'the chart gets under 35% of the card');
  }

  for (const el of root.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (cs.textOverflow === 'ellipsis' && el.scrollWidth > el.clientWidth + 1) {
      add('text_clipped', 'cut short: "' + short(el.textContent) + '"');
    } else if (el !== title && cs.webkitLineClamp && cs.webkitLineClamp !== 'none' && el.scrollHeight > el.clientHeight + 2) {
      add('text_clipped', 'cut short: "' + short(el.textContent) + '"');
    }
  }

  // A chart label is lost only where something clips it: the SVG itself (unless it draws overflow), else the nearest
  // ancestor that hides overflow, else the slide.
  const clipOf = (svg) => {
    if (getComputedStyle(svg).overflow !== 'visible') return svg.getBoundingClientRect();
    for (let el = svg.parentElement; el && el !== root; el = el.parentElement) {
      const o = getComputedStyle(el);
      if (o.overflow !== 'visible' || o.overflowX !== 'visible' || o.overflowY !== 'visible') return el.getBoundingClientRect();
    }
    return root.getBoundingClientRect();
  };
  for (const svg of root.querySelectorAll('svg')) {
    const s = svg.getBoundingClientRect();
    if (!s.width || !s.height) continue;
    const c = clipOf(svg);
    const boxes = [];
    for (const t of svg.querySelectorAll('text')) {
      const r = t.getBoundingClientRect();
      if (!r.width || !(t.textContent || '').trim()) continue;
      // A text box includes the line's padding above and below the letters: only an overshoot of a third of the
      // label's height or more is ink that's actually cut.
      const tol = Math.max(3, 0.35 * r.height);
      if (r.left < c.left - tol || r.right > c.right + tol || r.top < c.top - tol || r.bottom > c.bottom + tol) {
        add('label_outside', 'cut off at the edge: "' + short(t.textContent) + '"');
      }
      boxes.push([r, t.textContent]);
    }
    for (let i = 0; i < boxes.length; i++) {
      for (let j = i + 1; j < boxes.length; j++) {
        const [a, ta] = boxes[i]; const [b, tb] = boxes[j];
        const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
        const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
        if (w > 0 && h > 0 && w * h > 0.25 * Math.min(a.width * a.height, b.width * b.height)) {
          add('label_overlap', 'labels on each other: "' + short(ta) + '" and "' + short(tb) + '"');
        }
      }
    }
  }
  return JSON.stringify(out);
})()`;
