import React from 'react';
import { render, screen } from '@testing-library/react';
import { clearChunkReloadFlag, retryImport } from '../lazyWithRetry';
import ChunkErrorBoundary from '../../components/ui/ChunkErrorBoundary';

const chunkError = () => Object.assign(new Error('Loading chunk 123 failed.'), { name: 'ChunkLoadError' });

beforeEach(() => { clearChunkReloadFlag(); });

test('a stale chunk reloads once, then lets the error through', async () => {
  const reload = jest.fn();
  // First failure: reload, and the import never settles.
  const first = retryImport(() => Promise.reject(chunkError()), reload);
  await Promise.resolve();
  await Promise.resolve();
  expect(reload).toHaveBeenCalledTimes(1);
  let settled = false;
  first.then(() => { settled = true; }, () => { settled = true; });
  await new Promise((r) => setTimeout(r, 10));
  expect(settled).toBe(false);
  // Same session, fails again: no second reload, the error reaches the boundary.
  await expect(retryImport(() => Promise.reject(chunkError()), reload)).rejects.toThrow('Loading chunk');
  expect(reload).toHaveBeenCalledTimes(1);
});

test('a page that loads clears the flag, so a later stale chunk reloads once again', async () => {
  const reload = jest.fn();
  retryImport(() => Promise.reject(chunkError()), reload);
  await new Promise((r) => setTimeout(r, 0));
  expect(reload).toHaveBeenCalledTimes(1);
  await retryImport(() => Promise.resolve({ default: () => null }), reload);
  retryImport(() => Promise.reject(chunkError()), reload);
  await new Promise((r) => setTimeout(r, 0));
  expect(reload).toHaveBeenCalledTimes(2);
});

test('other errors are not retried', async () => {
  const reload = jest.fn();
  await expect(retryImport(() => Promise.reject(new Error('boom')), reload)).rejects.toThrow('boom');
  expect(reload).not.toHaveBeenCalled();
});

test('the boundary shows a reload message instead of an empty page', () => {
  const Broken = () => { throw chunkError(); };
  const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
  render(<ChunkErrorBoundary resetKey="/x"><Broken /></ChunkErrorBoundary>);
  spy.mockRestore();
  expect(screen.getByText("Couldn't load this page")).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Reload' })).toBeInTheDocument();
});
