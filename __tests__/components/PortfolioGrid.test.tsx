import { render, screen } from '@testing-library/react'
import PortfolioGrid from '@/components/PortfolioGrid'

const mockProjects = [
  {
    slug: 'test-project',
    title: 'Test Project',
    description: 'Test description',
    date: '2024-01-01',
    metrics: [
      { label: 'Performance', value: '+100%' },
      { label: 'Score', value: '99/100' },
    ],
    content: 'Test content',
  },
]

describe('PortfolioGrid Component', () => {
  it('renders section heading', () => {
    render(<PortfolioGrid projects={mockProjects} />)
    expect(screen.getByText('Избранные проекты')).toBeInTheDocument()
  })

  it('renders project title', () => {
    render(<PortfolioGrid projects={mockProjects} />)
    expect(screen.getByText('Test Project')).toBeInTheDocument()
  })

  it('renders project description', () => {
    render(<PortfolioGrid projects={mockProjects} />)
    expect(screen.getByText('Test description')).toBeInTheDocument()
  })

  it('renders project metrics', () => {
    render(<PortfolioGrid projects={mockProjects} />)
    expect(screen.getByText('+100%')).toBeInTheDocument()
    expect(screen.getByText('99/100')).toBeInTheDocument()
  })

  it('renders empty state when no projects', () => {
    render(<PortfolioGrid projects={[]} />)
    expect(screen.getByText('Избранные проекты')).toBeInTheDocument()
  })
})
