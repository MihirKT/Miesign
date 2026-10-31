/**
 * Cloudflare Pages Function: forwards /api/* to the Django server so the app lives on one miesign.pages.dev origin.
 * Photo and render links still point at the server directly, which plain <img> tags load fine.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */
const ORIGIN = 'https://136-112-204-89.sslip.io'

export function onRequest({ request }) {
  const url = new URL(request.url)
  return fetch(new Request(ORIGIN + url.pathname + url.search, request))
}
