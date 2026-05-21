import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import TemplateLibrary from '../components/TemplateLibrary'
import * as templatesApi from '../api/templatesApi'

const mockTemplates = [
  { id: 1, name: 'Zero-Shot', category: 'structure', content: '[TASK INSTRUCTION]\n\nInput: [INPUT]\n\nOutput:' },
  { id: 2, name: 'Steelman + Counter', category: 'reasoning', content: 'Steelman the following [POSITION]' },
  { id: 3, name: 'Critique Mode', category: 'task', content: 'Critique the following [ARTIFACT TYPE]' },
]

vi.mock('../api/templatesApi', () => ({
  getTemplates: vi.fn(),
}))

beforeEach(() => {
  templatesApi.getTemplates.mockResolvedValue(mockTemplates)
})

describe('TemplateLibrary', () => {

  test('renders list of templates', async () => {
    render(<TemplateLibrary onSelectTemplate={vi.fn()} currentPrompt="" />)
    await waitFor(() => {
      expect(screen.getByText('Zero-Shot')).toBeInTheDocument()
      expect(screen.getByText('Steelman + Counter')).toBeInTheDocument()
      expect(screen.getByText('Critique Mode')).toBeInTheDocument()
    })
  })

  test('clicking a template with empty editor loads it directly', async () => {
    const onSelectTemplate = vi.fn()
    render(<TemplateLibrary onSelectTemplate={onSelectTemplate} currentPrompt="" />)
    await waitFor(() => screen.getByText('Zero-Shot'))
    fireEvent.click(screen.getByText('Zero-Shot').closest('button'))
    expect(onSelectTemplate).toHaveBeenCalledWith('[TASK INSTRUCTION]\n\nInput: [INPUT]\n\nOutput:')
  })

  test('clicking a template with existing editor content shows confirmation', async () => {
    window.confirm = vi.fn(() => true)
    const onSelectTemplate = vi.fn()
    render(<TemplateLibrary onSelectTemplate={onSelectTemplate} currentPrompt="some existing text" />)
    await waitFor(() => screen.getByText('Zero-Shot'))
    fireEvent.click(screen.getByText('Zero-Shot').closest('button'))
    expect(window.confirm).toHaveBeenCalled()
    expect(onSelectTemplate).toHaveBeenCalledWith('[TASK INSTRUCTION]\n\nInput: [INPUT]\n\nOutput:')
  })

  test('cancelling confirmation keeps existing editor content', async () => {
    window.confirm = vi.fn(() => false)
    const onSelectTemplate = vi.fn()
    render(<TemplateLibrary onSelectTemplate={onSelectTemplate} currentPrompt="some existing text" />)
    await waitFor(() => screen.getByText('Zero-Shot'))
    fireEvent.click(screen.getByText('Zero-Shot').closest('button'))
    expect(window.confirm).toHaveBeenCalled()
    expect(onSelectTemplate).not.toHaveBeenCalled()
  })

  test('filter buttons are rendered', async () => {
    render(<TemplateLibrary onSelectTemplate={vi.fn()} currentPrompt="" />)
    expect(screen.getByText('All')).toBeInTheDocument()
    expect(screen.getByText('Reasoning')).toBeInTheDocument()
    expect(screen.getByText('Structure')).toBeInTheDocument()
    expect(screen.getByText('Task')).toBeInTheDocument()
  })

})