import { beforeEach, expect } from 'vitest'
import { getHealth } from '../api/client'

beforeEach(() => {
    global.fetch = vi.fn(() =>
    Promise.resolve({ json: () => Promise.resolve({ status: 'ok '}) })
    )
})

test('getHealth calls the correct endpoint', async () => {
    const result = await getHealth()
    // Matched on path only: pinning the host made this assertion drift out of
    // sync with the source once already, and deriving it from API_BASE would
    // only be comparing the constant against itself.
    expect(fetch).toHaveBeenCalledWith(
        expect.stringMatching(/\/health$/),
        expect.objectContaining({ credentials: 'include' })
    )
    expect(result).toEqual({ status: 'ok '})
})

test('requests send credentials so the session cookie is included', async () => {
    await getHealth()
    const [, options] = fetch.mock.calls[0]
    expect(options.credentials).toBe('include')
})
