import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { expect, vi } from 'vitest'
import VersionSelector from '../components/VersionSelector'
import * as versionsApi from '../api/versionsApi'
import { version } from 'react'

vi.mock('../api/versionsApi', () => ({
  getVersions: vi.fn(),
  updateVersion: vi.fn(),
  deleteVersion: vi.fn(),
}))

const mockVersions = [
  {
    id: 1,
    name: 'Version 1',
    prompt_text: 'Test prompt 1',
    response_text: 'Response 1',
    response_model: 'gpt-4',
    response_latency: 1.2
  },
  {
    id: 2,
    name: 'Version 2',
    prompt_text: 'Test prompt 2',
    response_text: null,
    response_model: null,
    response_latency: null
  }
]

describe('VersionSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('version list displays all saved versions', async () => {
    versionsApi.getVersions.mockResolvedValue(mockVersions)
    render(<VersionSelector token="fake-token" onSelectVersion={() => {}} />)

    await waitFor(() => {
      expect(screen.getByText('Version 1')).toBeInTheDocument()
      expect(screen.getByText('Version 2')).toBeInTheDocument()
    })
  })

  test('version list is empty when no versions are saved', async () => {
    versionsApi.getVersions.mockResolvedValue([])
    render(<VersionSelector token="fake-token" onSelectVersion={() => {}} />)

    await waitFor(() => {
      expect(screen.getByText('No saved versions yet.')).toBeInTheDocument()
    })
  })

  test('selecting a version calls onSelectVersion with correct data', async () => {
    versionsApi.getVersions.mockResolvedValue(mockVersions)
    const onSelectMock = vi.fn()
    render(<VersionSelector token="fake-token" onSelectVersion={onSelectMock} />)

    await waitFor(() => {
      expect(screen.getByText('Version 1')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Version 1'))
    
    expect(onSelectMock).toHaveBeenCalledWith(mockVersions[0])
  })

  test('clicking refresh button calls getVersions again', async () => {
    versionsApi.getVersions.mockResolvedValue(mockVersions)
    render(<VersionSelector token="fake-token" onSelectVersion={() => {}} />)

    await waitFor(() => {
      expect(screen.getByText('Version 1')).toBeInTheDocument()
    })

    versionsApi.getVersions.mockClear()
    
    fireEvent.click(screen.getByText('Refresh'))
    
    expect(versionsApi.getVersions).toHaveBeenCalledWith('fake-token', '')
  })

  test('renders search input above version list', async () => {
    versionsApi.getVersions.mockResolvedValue(mockVersions)
    render(<VersionSelector token="fake-token" onSelectVersion={() => {}} />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument()
    })
  })

  test('typing in search input triggers getVersions with search param after debounce', async () => {
    vi.useFakeTimers()
    versionsApi.getVersions.mockResolvedValue(mockVersions)
    render(<VersionSelector token="fake-token" onSelectVersion={() => {}} />)

    await vi.waitFor(() => {
      expect(versionsApi.getVersions).toHaveBeenCalledWith('fake-token', '')
    })

    versionsApi.getVersions.mockClear()

    const input = screen.getByPlaceholderText(/search/i)
    fireEvent.change(input, { target: { value: 'quicksort' } })

    expect(versionsApi.getVersions).not.toHaveBeenCalled()

    vi.advanceTimersByTime(300)

    await vi.waitFor(() => {
      expect(versionsApi.getVersions).toHaveBeenCalledWith('fake-token', 'quicksort')
    })

    vi.useRealTimers()
  })

  test('shows "No results found" when search returns empty list', async () => {
    versionsApi.getVersions.mockResolvedValueOnce(mockVersions)
    render(<VersionSelector token="fake-token" onSelectVersion={() => {}} />)

    await waitFor(() => {
      expect(screen.getByText('Version 1')).toBeInTheDocument()
    })

    versionsApi.getVersions.mockResolvedValueOnce([])

    const input = screen.getByPlaceholderText(/search/i)
    fireEvent.change(input, { target: { value: 'nonexistent' } })

    await waitFor(() => {
      expect(screen.getByText(/no results found/i)).toBeInTheDocument()
    })
  })

  test('editing a version updates its name and tag', async () => {
    versionsApi.getVersions.mockResolvedValue(mockVersions)
    versionsApi.updateVersion.mockResolvedValue({
      ...mockVersions[0],
      name: 'Version 1 Updated',
      tag: 'final',
    })
    const onSelectMock = vi.fn()
    render(<VersionSelector token="fake-token" onSelectVersion={onSelectMock} />)

    await waitFor(() => {
      expect(screen.getByText('Version 1')).toBeInTheDocument()
    })

    fireEvent.click(screen.getAllByText('Edit')[0])
    fireEvent.change(screen.getByPlaceholderText('Version name'), { target: { value: 'Version 1 Updated' } })
    fireEvent.change(screen.getByPlaceholderText('Tag (optional)'), { target: { value: 'final' } })
    fireEvent.click(screen.getByText('Save'))

    await waitFor(() => {
      expect(versionsApi.updateVersion).toHaveBeenCalledWith('fake-token', 1, {
        name: 'Version 1 Updated',
        tag: 'final',
      })
    })
  })

  test('deleting a version calls API and removes item from list', async () => {
    versionsApi.getVersions.mockResolvedValue(mockVersions)
    versionsApi.deleteVersion.mockResolvedValue(undefined)
    render(<VersionSelector token="fake-token" onSelectVersion={() => {}} />)

    await waitFor(() => {
      expect(screen.getByText('Version 1')).toBeInTheDocument()
      expect(screen.getByText('Version 2')).toBeInTheDocument()
    })

    fireEvent.click(screen.getAllByText('Delete')[0])

    await waitFor(() => {
      expect(versionsApi.deleteVersion).toHaveBeenCalledWith('fake-token', 1)
    })

    await waitFor(() => {
      expect(screen.queryByText('Version 1')).not.toBeInTheDocument()
      expect(screen.getByText('Version 2')).toBeInTheDocument()
    })
  })
})
