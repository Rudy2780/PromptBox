import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import ExportDropdown from '../components/ExportDropdown'
import * as exportApi from '../api/exportApi'

vi.mock('../api/exportApi', () => ({
  downloadExport: vi.fn(),
}))

describe('ExportDropdown', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('export dropdown renders .txt, .md, and .json options', () => {
    render(<ExportDropdown versionId={1} />)
    
    expect(screen.getByRole('combobox')).toBeInTheDocument()
    expect(screen.getByText('.txt (Plain Text)')).toBeInTheDocument()
    expect(screen.getByText('.md (Markdown)')).toBeInTheDocument()
    expect(screen.getByText('.json (JSON)')).toBeInTheDocument()
  })

  test('clicking export triggers a download request with the correct format parameter', async () => {
    exportApi.downloadExport.mockResolvedValue()
    
    render(<ExportDropdown versionId={1} />)
    
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'md' } })
    fireEvent.click(screen.getByRole('button', { name: /export/i }))
    
    expect(exportApi.downloadExport).toHaveBeenCalledWith(1, 'md')
  })

  test('export button is disabled when no version is selected or loaded', () => {
    render(<ExportDropdown versionId={null} />)
    
    const button = screen.getByRole('button', { name: /export/i })
    expect(button).toBeDisabled()
  })

  test('UI displays success feedback after export attempt', async () => {
    exportApi.downloadExport.mockResolvedValue()
    
    render(<ExportDropdown versionId={1} />)
    
    fireEvent.click(screen.getByRole('button', { name: /export/i }))
    
    await waitFor(() => {
      expect(screen.getByText('Export successful!')).toBeInTheDocument()
    })
  })

  test('UI displays error feedback after export attempt fails', async () => {
    exportApi.downloadExport.mockRejectedValue(new Error('Network error'))
    
    render(<ExportDropdown versionId={1} />)
    
    fireEvent.click(screen.getByRole('button', { name: /export/i }))
    
    await waitFor(() => {
      expect(screen.getByText('Failed to export: Network error')).toBeInTheDocument()
    })
  })
})
