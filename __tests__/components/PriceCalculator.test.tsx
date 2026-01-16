import { render, screen } from '@testing-library/react'
import PriceCalculator from '@/components/PriceCalculator'

describe('PriceCalculator Component', () => {
  it('renders calculator heading', () => {
    render(<PriceCalculator />)
    expect(screen.getByText('Калькулятор проекта')).toBeInTheDocument()
  })

  it('renders project type options', () => {
    render(<PriceCalculator />)
    expect(screen.getByText('Landing Page')).toBeInTheDocument()
    expect(screen.getByText('Corporate Website')).toBeInTheDocument()
    expect(screen.getByText('E-Commerce')).toBeInTheDocument()
  })

  it('renders feature options', () => {
    render(<PriceCalculator />)
    expect(screen.getByText('Custom Design')).toBeInTheDocument()
    expect(screen.getByText('AI Integration')).toBeInTheDocument()
  })

  it('renders Get Quote button', () => {
    render(<PriceCalculator />)
    expect(screen.getByText('Получить предложение')).toBeInTheDocument()
  })
})
