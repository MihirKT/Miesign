/**
 * Tests the API client: key conversion, error messages and network failure.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

import { afterEach, expect, it, vi } from 'vitest'
import { api } from './api'

afterEach(() => vi.unstubAllGlobals())

function stubFetch(status: number, body: string) {
  const fn = vi.fn().mockResolvedValue(new Response(body, { status, headers: { 'Content-Type': 'application/json' } }))
  vi.stubGlobal('fetch', fn)
  return fn
}

it('sends snake_case bodies and returns camelCase data', async () => {
  const fn = stubFetch(200, JSON.stringify({ designs: [{ id: 'd', render_url: null }] }))
  const designs = await api.designFromText('p1', 'grey walls')
  expect(fn).toHaveBeenCalledWith('/api/design/from-text?project_id=p1', expect.objectContaining({
    method: 'POST', body: JSON.stringify({ text: 'grey walls' }),
  }))
  expect(designs[0].renderUrl).toBeNull()
})

it('converts nested spec keys when saving a design', async () => {
  const fn = stubFetch(200, JSON.stringify({ designs: [{ id: 'd' }] }))
  await api.saveDesign('p1', {
    name: 'A',
    spec: { style: '', palette: [], keepUnchanged: ['window'], assignments: [{ target: 'type:wall', materialId: 'x', color: null, finish: '' }] },
  })
  const body = JSON.parse(fn.mock.calls[0][1].body)
  expect(body.spec.keep_unchanged).toEqual(['window'])
  expect(body.spec.assignments[0].material_id).toBe('x')
})

it('surfaces the backend error message and code', async () => {
  stubFetch(429, JSON.stringify({ error: { code: 'RENDER_LIMIT', message: 'Used all 8 previews.', status: 429, details: [] } }))
  await expect(api.render('d')).rejects.toMatchObject({ code: 'RENDER_LIMIT', status: 429, message: 'Used all 8 previews.' })
})

it('falls back to a friendly message for non-JSON errors', async () => {
  stubFetch(502, '<html>Bad gateway</html>')
  await expect(api.getProject('p')).rejects.toMatchObject({ status: 502, message: 'Something went wrong. Try again.' })
})

it('reports network failures plainly', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
  await expect(api.catalog()).rejects.toMatchObject({ code: 'NETWORK', status: 0 })
})

it('uploads photos as multipart without a JSON content type', async () => {
  const fn = stubFetch(200, JSON.stringify({ id: 'p', photos: [] }))
  await api.uploadPhoto('p', new File(['x'], 'h.jpg', { type: 'image/jpeg' }))
  const init = fn.mock.calls[0][1]
  expect(init.body).toBeInstanceOf(FormData)
  expect(init.headers).toBeUndefined()
})
