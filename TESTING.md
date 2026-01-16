# 🧪 Testing Guide

## Обзор

Проект использует **Jest** и **React Testing Library** для автоматического тестирования.

## Структура тестов

```
__tests__/
├── components/     # Тесты компонентов
├── lib/           # Тесты утилит
└── app/           # Тесты страниц
```

## Команды

### Запуск тестов

```bash
# Режим watch (для разработки)
npm test

# Одноразовый запуск (для CI)
npm run test:ci

# Генерация теста для нового файла
npm run test:generate components/MyComponent.tsx
```

## Автоматическая генерация тестов

### Для нового компонента

```bash
npm run test:generate components/NewComponent.tsx
```

Скрипт автоматически:
- Определяет тип файла (компонент/утилита/страница)
- Создает базовый шаблон теста
- Размещает тест в правильной директории

### Пример сгенерированного теста

```typescript
import { render, screen } from '@testing-library/react'
import NewComponent from '@/components/NewComponent'

describe('NewComponent Component', () => {
  it('renders without crashing', () => {
    render(<NewComponent />)
  })

  it('renders expected content', () => {
    render(<NewComponent />)
    // Добавьте ваши проверки
  })
})
```

## Покрытие кода

### Минимальные требования

- **Branches**: 70%
- **Functions**: 70%
- **Lines**: 70%
- **Statements**: 70%

### Просмотр покрытия

```bash
npm run test:ci
# Откройте coverage/lcov-report/index.html
```

## CI/CD Integration

### Автоматические проверки

При каждом push/PR:
1. ✅ Запускаются все тесты
2. ✅ Проверяется покрытие кода (>70%)
3. ✅ Type-checking
4. ✅ Lighthouse CI (>99)
5. ✅ Автогенерация тестов для новых файлов

### Блокировка деплоя

Деплой **блокируется** если:
- Тесты не проходят
- Покрытие < 70%
- TypeScript ошибки
- Lighthouse < 99

## Best Practices

### 1. Тестируйте поведение, а не реализацию

```typescript
// ❌ Плохо
expect(component.state.count).toBe(5)

// ✅ Хорошо
expect(screen.getByText('Count: 5')).toBeInTheDocument()
```

### 2. Используйте data-testid для сложных селекторов

```typescript
<div data-testid="user-profile">...</div>

// В тесте
screen.getByTestId('user-profile')
```

### 3. Мокайте внешние зависимости

```typescript
jest.mock('@/lib/api', () => ({
  fetchData: jest.fn(() => Promise.resolve({ data: 'test' }))
}))
```

### 4. Тестируйте edge cases

```typescript
it('handles empty state', () => {
  render(<List items={[]} />)
  expect(screen.getByText('No items')).toBeInTheDocument()
})

it('handles loading state', () => {
  render(<List loading={true} />)
  expect(screen.getByText('Loading...')).toBeInTheDocument()
})
```

## Примеры тестов

### Компонент с взаимодействием

```typescript
import { render, screen, fireEvent } from '@testing-library/react'
import Button from '@/components/Button'

describe('Button', () => {
  it('calls onClick when clicked', () => {
    const handleClick = jest.fn()
    render(<Button onClick={handleClick}>Click me</Button>)
    
    fireEvent.click(screen.getByText('Click me'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })
})
```

### Асинхронный компонент

```typescript
import { render, screen, waitFor } from '@testing-library/react'
import UserProfile from '@/components/UserProfile'

describe('UserProfile', () => {
  it('loads and displays user data', async () => {
    render(<UserProfile userId="123" />)
    
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument()
    })
  })
})
```

### Утилита

```typescript
import { formatPrice } from '@/lib/utils'

describe('formatPrice', () => {
  it('formats price correctly', () => {
    expect(formatPrice(1000)).toBe('$1,000')
    expect(formatPrice(1500.50)).toBe('$1,500.50')
  })

  it('handles zero', () => {
    expect(formatPrice(0)).toBe('$0')
  })
})
```

## Troubleshooting

### Тесты не находят компонент

```bash
# Проверьте пути в jest.config.js
moduleNameMapper: {
  '^@/(.*)$': '<rootDir>/$1',
}
```

### Ошибки с framer-motion

Уже замокано в `jest.setup.js`

### Ошибки с Next.js navigation

Уже замокано в `jest.setup.js`

## Мониторинг

### GitHub Actions

Все тесты автоматически запускаются в CI:
- `.github/workflows/testing.yml` - основные тесты
- `.github/workflows/deploy.yml` - перед деплоем

### Coverage Reports

Отчеты о покрытии автоматически:
- Загружаются в Codecov
- Комментируются в PR
- Проверяются на соответствие порогу

## Поддержка

При проблемах с тестами:
1. Проверьте `jest.setup.js`
2. Убедитесь что моки настроены
3. Запустите `npm test -- --verbose`
