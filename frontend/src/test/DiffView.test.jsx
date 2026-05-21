import { render, screen } from '@testing-library/react'
import DiffView from '../components/DiffView'

const mockVersionA = {
  id: 1,
  name: 'VersionA',
  prompt_text: 'explain quicksort in plain English',
  response_text: 'Quicksort is a sorting algorithm.',
}

const mockVersionB = {
  id: 2,
  name: 'VersionB',
  prompt_text: 'explain quicksort in simple clear English',
  response_text: null,
}

describe('DiffView', () => {

  test('selecting two versions renders a diff view', () => {
    render(<DiffView versionA={mockVersionA} versionB={mockVersionB} totalVersions={2} />)
    expect(screen.getByText('VersionA')).toBeInTheDocument()
    expect(screen.getByText('VersionB')).toBeInTheDocument()
  })

  test('removed text is highlighted red on the older version', () => {
    render(<DiffView versionA={mockVersionA} versionB={mockVersionB} totalVersions={2} />)
    const removed = document.querySelector('.diff-removed')
    expect(removed).toBeInTheDocument()
    expect(removed.textContent.trim()).toBe('plain')
  })

  test('added text is highlighted green on the newer version', () => {
    render(<DiffView versionA={mockVersionA} versionB={mockVersionB} totalVersions={2} />)
    const added = document.querySelectorAll('.diff-added')
    const addedWords = Array.from(added).map(el => el.textContent.trim())
    expect(addedWords).toContain('simple')
    expect(addedWords).toContain('clear')
  })

  test('diff view shows associated responses if available', () => {
    render(<DiffView versionA={mockVersionA} versionB={mockVersionB} totalVersions={2} />)
    expect(screen.getByText('Quicksort is a sorting algorithm.')).toBeInTheDocument()
  })

  test('diff is blocked when fewer than one saved version exists', () => {
    render(<DiffView versionA={mockVersionA} versionB={mockVersionB} totalVersions={0} />)
    expect(screen.getByText('You need at least one saved version to compare.')).toBeInTheDocument()
  })

})