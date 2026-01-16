import { render, screen } from '@testing-library/react'
import Navigation from '@/components/Navigation'

describe('Navigation Component', () => {
  it('renders logo', () => {
    render(<Navigation />)
    expect(screen.getByText('AGENCY')).toBeInTheDocument()
  })

  it('renders all navigation items', () => {
    render(<Navigation />)
    expect(screen.getByText('Проекты')).toBeInTheDocument()
    expect(screen.getByText('Услуги')).toBeInTheDocument()
    expect(screen.getByText('О нас')).toBeInTheDocument()
  })

  it('renders Get Started button', () => {
    render(<Navigation />)
    expect(screen.getByText('Начать проект')).toBeInTheDocument()
  })
})
