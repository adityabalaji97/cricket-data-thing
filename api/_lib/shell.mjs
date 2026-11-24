// public/index.html draws the home page's first screen inside #root (landing plan L6), ending with
// <template id="shell-end"></template>: a real element, because the production build minifies index.html and drops
// comments. Crawler heads (api/meta.mjs) replace #root with a page's own body, or strip the shell off any page that
// isn't the home page. The empty <div id="root"></div> of an older build matches too.
export const ROOT = /<div id="root">(?:[\s\S]*?<template id="shell-end"><\/template>)?<\/div>/i;

export function rootFor(html, path, body) {
  if (body) return html.replace(ROOT, () => `<div id="root">${body}</div>`);
  if (path !== '/') return html.replace(ROOT, '<div id="root"></div>');
  return html;
}
