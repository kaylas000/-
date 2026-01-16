import { render, screen } from '@testing-library/react'
import InteractiveFooter from '@/components/InteractiveFooter'

describe('InteractiveFooter Component', () => {
  it('renders AI status', () => {
    render(<InteractiveFooter />)
    expect(screen.getByText('ИИ Менеджер')).toBeInTheDocument()
    expect(screen.getByText('Системы активны')).toBeInTheDocument()
  })

  it('renders build info', () => {
    render(<InteractiveFooter />)
    expect(screen.getByText('Последняя сборка')).toBeInTheDocument()
  })

  it('renders UTC time label', () => {
    render(<InteractiveFooter />)
    expect(screen.getByText('Время UTC')).toBeInTheDocument()
  })

  it('renders copyright', () => {
    render(<InteractiveFooter />)
    expect(screen.getByText(/© 2024 Premium Agency/i)).toBeInTheDocument()
  })

  it('renders footer links', () => {
    render(<InteractiveFooter />)
    expect(screen.getByText('Конфиденциальность')).toBeInTheDocument()
    expect(screen.getByText('Условия')).toBeInTheDocument()
    expect(screen.getByText('Контакты')).toBeInTheDocument()
  })
})
