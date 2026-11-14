import { cleanDates, datePresetOf, datePresets } from '../qbWords';
import { followLabel, questionAfterEdit } from '../qbWords';

const today = new Date('2026-11-14T10:00:00');

test('a today-to-today range (a phone date picker opened and closed) is dropped', () => {
  expect(cleanDates({ start_date: '2026-11-14', end_date: '2026-11-14' }, today)).toMatchObject({ start_date: null, end_date: null });
});

test('a future end stays ("IPL 2026" ends 31 Dec), and a backwards range is turned round', () => {
  expect(cleanDates({ start_date: '2026-01-01', end_date: '2026-12-31' }, today)).toMatchObject({ start_date: '2026-01-01', end_date: '2026-12-31' });
  expect(cleanDates({ start_date: '2025-06-01', end_date: '2024-01-01' }, today)).toMatchObject({ start_date: '2024-01-01', end_date: '2025-06-01' });
});

test('presets: Any time, this year and the three before, read back from the dates', () => {
  expect(datePresets(today).map(([l]) => l)).toEqual(['Any time', 'This year', 'Since 2025', 'Since 2024', 'Since 2023']);
  expect(datePresetOf({}, today)).toBe('Any time');
  expect(datePresetOf({ start_date: '2024-01-01' }, today)).toBe('Since 2024');
  expect(datePresetOf({ start_date: '2024-03-01' }, today)).toBe('custom');
  expect(datePresetOf({ start_date: '2026-01-01', end_date: '2026-12-31' }, today)).toBe('custom');
});

test('a filter changed by hand drops the question; a new grouping alone keeps it', () => {
  const q = 'Sanju Samson vs pace heavy sides';
  expect(questionAfterEdit(q, { batters: ['Sanju Samson'] }, { batters: ['Axar Patel'] })).toBeNull();
  expect(questionAfterEdit(q, { batters: ['Sanju Samson'] }, { batters: ['Sanju Samson'] })).toBe(q);
});

test('a follow-up label is the first question and the latest follow-up', () => {
  expect(followLabel('Sanju Samson … Powerplay … Batting at 3,4,5', 'x', 'since 2024')).toBe('Sanju Samson … since 2024');
  expect(followLabel('', 'Virat Kohli, by year', 'v spin')).toBe('Virat Kohli, by year … v spin');
});

test('a one-day range reads as the day', () => {
  const { queryChips } = require('../qbWords');
  expect(queryChips({ start_date: '2026-11-09', end_date: '2026-11-09' }, []).find((c) => c.key === 'dates').label).toBe('9 Nov 2026');
});
