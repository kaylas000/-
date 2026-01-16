import { render, screen } from '@testing-library/react'
import Hero from '@/components/Hero'

describe('Hero Component', () => {
  it('renders hero heading', () => {
    render(<Hero />)
    expect(screen.getByText('Цифровое совершенство')).toBeInTheDocument()
    expect(screen.getByText('Созданное с точностью')).toBeInTheDocument()
  })

  it('renders CTA button', () => {
    render(<Hero />)
    expect(screen.getByText('Начать проект')).toBeInTheDocument()
  })

  it('renders description text', () => {
    render(<Hero />)
    expect(screen.getByText(/Мы создаём премиум цифровые продукты/i)).toBeInTheDocument()
  })
})
