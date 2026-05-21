import { beforeEach, expect } from 'vitest'
import { getHealth } from '../api/client'

beforeEach(() => {
    global.fetch = vi.fn(() =>
    Promise.resolve({ json: () => Promise.resolve({ status: 'ok '}) })
    )
})

test('getHealth calls the correct endpoint', async () => {
    const result = await getHealth()
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/health')
    expect(result).toEqual({ status: 'ok '})
})
