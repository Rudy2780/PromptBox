import { render, waitFor } from '@testing-library/react'
import { describe, test, expect, vi } from 'vitest'
import DiffVersionPicker from '../components/DiffVerisonPicker'
import * as versionsApi from '../api/versionsApi'

vi.mock('../api/versionsApi', () => ({
  getVersions: vi.fn(),
}))

describe('DiffVersionPicker', () => {
  test('reloads versions when refreshSignal changes', async () => {
    versionsApi.getVersions.mockResolvedValue([])

    const { rerender } = render(
      <DiffVersionPicker onCompare={() => {}} refreshSignal={0} />
    )

    await waitFor(() => {
      expect(versionsApi.getVersions).toHaveBeenCalledTimes(1)
      expect(versionsApi.getVersions).toHaveBeenCalledWith()
    })

    rerender(
      <DiffVersionPicker onCompare={() => {}} refreshSignal={1} />
    )

    await waitFor(() => {
      expect(versionsApi.getVersions).toHaveBeenCalledTimes(2)
    })
  })
})
