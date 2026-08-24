import { beforeEach, expect } from 'vitest'
import { getHealth } from '../api/client'
import { API_BASE } from '../api/http'

beforeEach(() => {
    global.fetch = vi.fn(() =>
    Promise.resolve({ json: () => Promise.resolve({ status: 'ok '}) })
    )
})

test('getHealth calls the correct endpoint', async () => {
    const result = await getHealth()
    // URL is derived from API_BASE rather than hardcoded, so the assertion
    // cannot drift out of sync with the source the way it previously had.
    expect(fetch).toHaveBeenCalledWith(
        `${API_BASE}/health`,
        expect.objectContaining({ credentials: 'include' })
    )
    expect(result).toEqual({ status: 'ok '})
})

test('requests send credentials so the session cookie is included', async () => {
    await getHealth()
    const [, options] = fetch.mock.calls[0]
    expect(options.credentials).toBe('include')
})
