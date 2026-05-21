import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ModelSelector from '../components/ModelSelector'
import { validateKey } from '../api/client'
import { expect, expectTypeOf, vi } from 'vitest'
import { useState } from 'react'

vi.mock('../api/client', () => ({
    validateKey: vi.fn()
}))

function ModelSelectorWrapper(props){
    const [apiKey, setApiKey] = useState('')
    return <ModelSelector {...props} apiKey={apiKey} setApiKey={setApiKey}/>
}

const defaultProps = {
    provider: 'openai',
    setProvider: vi.fn(),
    apiKey: '',
    setApiKey: vi.fn(),
    model: 'gpt-4o',
    setModel: vi.fn(),
    onValidated: vi.fn()
}

test('renders provider dropdown and API key input', () => {
    render(<ModelSelectorWrapper {...defaultProps} />)
    expect(screen.getByLabelText(/provider/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/model/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Enter API Key')).toBeInTheDocument()
    expect(screen.getByText('Validate Key')).toBeInTheDocument()
})

test('shows success message when key is valid', async() => {
    validateKey.mockResolvedValue({ status: 200, data: { status: 'valid', provider: 'openai'}})
    
    render(<ModelSelectorWrapper {...defaultProps} />)
    fireEvent.change(screen.getByPlaceholderText('Enter API Key'), { target: {value: 'sk-test-key'} })
    fireEvent.click(screen.getByText('Validate Key'))

    await waitFor(() => {
        expect(screen.getByText(/valid/i)).toBeInTheDocument()
    })
})

test('shows error message when key is invalid', async () => {
    validateKey.mockResolvedValue({ status: 401, data: { detail: 'Invalid API Key' } })

    render(<ModelSelectorWrapper {...defaultProps}/>)
    fireEvent.change(screen.getByPlaceholderText('Enter API Key'), { target: { value: 'sk-bad-key' } })
    fireEvent.click(screen.getByText('Validate Key'))

    await waitFor(() => {
        expect(screen.getByText(/invalid/i)).toBeInTheDocument()
    })
})
