import { render, screen } from '@testing-library/react'
import ServiceAccordion from '@/components/ServiceAccordion'

const mockItems = [
  { title: 'Test Item 1', content: 'Test content 1' },
  { title: 'Test Item 2', content: 'Test content 2' },
]

describe('ServiceAccordion Component', () => {
  it('renders without crashing', () => {
    render(<ServiceAccordion items={mockItems} />)
  })

  it('renders all accordion items', () => {
    render(<ServiceAccordion items={mockItems} />)
    expect(screen.getByText('Test Item 1')).toBeInTheDocument()
    expect(screen.getByText('Test Item 2')).toBeInTheDocument()
  })

  it('shows first item content by default', () => {
    render(<ServiceAccordion items={mockItems} />)
    expect(screen.getByText('Test content 1')).toBeInTheDocument()
  })
})
