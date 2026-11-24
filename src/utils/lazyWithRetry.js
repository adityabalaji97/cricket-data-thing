import React from 'react';

// React.lazy for the app's pages (landing plan L6), with one recovery: after a deploy, a tab opened before it asks for
// the old chunk hashes, gets a 404 and throws ChunkLoadError, which would blank the page. The first time, reload once
// (the new index.html names the new chunks); if it fails again, the error reaches ChunkErrorBoundary.

const FLAG = 'chunk-reload';
export const CHUNK_ERROR = /Loading chunk|ChunkLoadError|dynamically imported module/i;

// sessionStorage can throw (private mode, blocked storage): every access is guarded.
const readFlag = () => { try { return window.sessionStorage.getItem(FLAG); } catch { return null; } };
const writeFlag = () => { try { window.sessionStorage.setItem(FLAG, '1'); return true; } catch { return false; } };

// Cleared when a page's code does load, so a later stale chunk (after another deploy) may reload once again. Not on
// app mount: the app mounts before the failing page's chunk is asked for, so clearing there would reload forever.
export const clearChunkReloadFlag = () => { try { window.sessionStorage.removeItem(FLAG); } catch { /* ignore */ } };

export const retryImport = (factory, reload = () => window.location.reload()) => factory().then((module) => {
  if (readFlag()) clearChunkReloadFlag();
  return module;
}, (error) => {
  const message = `${error?.name || ''} ${error?.message || ''}`;
  if (CHUNK_ERROR.test(message) && !readFlag() && writeFlag()) {
    reload();
    return new Promise(() => {}); // the page is going away; don't render the error meanwhile
  }
  throw error;
});

const lazyWithRetry = (factory) => React.lazy(() => retryImport(factory));

export default lazyWithRetry;
