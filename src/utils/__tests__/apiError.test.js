import { apiErrorText } from '../apiError';

const err = (detail) => ({ response: { data: { detail } } });

test('passes a string detail through', () => {
  expect(apiErrorText(err('Unknown venue'), 'x')).toBe('Unknown venue');
});

test('turns a FastAPI validation list into one line of text', () => {
  const detail = [{ type: 'less_than_equal', loc: ['query', 'limit'], msg: 'Input should be less than or equal to 10000',
    input: '20000', ctx: { le: 10000 } }];
  expect(apiErrorText(err(detail), 'x')).toBe('limit: Input should be less than or equal to 10000');
});

test('falls back when there is no detail', () => {
  expect(apiErrorText(new Error('network'), 'Failed to execute query')).toBe('Failed to execute query');
  expect(apiErrorText(err({}), 'Failed')).toBe('Failed');
});
