import { noteDateLabel, previewPassed, previewStart } from '../noteDates';

const preview = (dek, published = '2026-10-01T10:00:45+05:30') => ({ kind: 'preview', dek, published_at: published });

test('reads the match start from a preview dek, in IST', () => {
  const start = previewStart(preview('Indian Premier League · T20 · M Chinnaswamy Stadium · Fri 2 Oct, 05:30 IST (00:00 GMT)'));
  expect(start.toISOString()).toBe('2026-10-02T00:00:00.000Z');
});

test('a January match previewed in December is next year', () => {
  const start = previewStart(preview('BBL · T20 · MCG · Thu 1 Jan, 14:00 IST (08:30 GMT)', '2026-12-30T10:00:00+05:30'));
  expect(start.toISOString()).toBe('2027-01-01T08:30:00.000Z');
});

test('a December match previewed in January is the previous year', () => {
  const start = previewStart(preview('BBL · T20 · SCG · Wed 30 Dec, 13:45 IST (08:15 GMT)', '2027-01-02T10:00:00+05:30'));
  expect(start.toISOString()).toBe('2026-12-30T08:15:00.000Z');
});

test('a preview passes five hours after a T20 starts, ten after an ODI', () => {
  const t20 = preview('IPL · T20 · Wankhede · Fri 2 Oct, 19:30 IST (14:00 GMT)');
  expect(previewPassed(t20, Date.parse('2026-10-02T18:30:00Z'))).toBe(false);
  expect(previewPassed(t20, Date.parse('2026-10-02T19:30:00Z'))).toBe(true);
  const odi = preview('Australia v England · ODI · Hobart · Fri 2 Oct, 09:00 IST (03:30 GMT)');
  expect(previewPassed(odi, Date.parse('2026-10-02T13:00:00Z'))).toBe(false);
  expect(previewPassed(odi, Date.parse('2026-10-02T14:00:00Z'))).toBe(true);
});

test('recaps, articles and previews without a start never count as passed', () => {
  expect(previewPassed({ kind: 'recap', dek: 'Fri 2 Oct, 05:30 IST' }, Date.parse('2030-01-01'))).toBe(false);
  expect(previewPassed({ kind: 'preview', dek: 'Work in progress', published_at: '2026-10-01' }, Date.parse('2030-01-01'))).toBe(false);
});

test('date label drops the year only in the current year', () => {
  const now = new Date('2026-11-24T12:00:00Z');
  expect(noteDateLabel({ published_at: '2026-10-01T10:00:45+05:30' }, now)).toBe('1 Oct');
  expect(noteDateLabel({ published_at: '2025-10-01T10:00:45+05:30' }, now)).toBe('1 Oct 2025');
  expect(noteDateLabel({}, now)).toBe('');
});
