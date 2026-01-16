import '@testing-library/jest-dom'
import React from 'react'

// Mock next/link globally
jest.mock('next/link', () => {
  return function Link({ children, href }) {
    return React.createElement('a', { href }, children)
  }
})

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: function MockDiv(props) { return React.createElement('div', props) },
    h1: function MockH1(props) { return React.createElement('h1', props) },
    p: function MockP(props) { return React.createElement('p', props) },
    span: function MockSpan(props) { return React.createElement('span', props) },
    button: function MockButton(props) { return React.createElement('button', props) },
    nav: function MockNav(props) { return React.createElement('nav', props) },
  },
  AnimatePresence: function MockAnimatePresence({ children }) { return children },
  useMotionValue: () => ({ set: jest.fn(), get: jest.fn() }),
  useSpring: () => ({ set: jest.fn(), get: jest.fn() }),
  useTransform: () => ({ set: jest.fn(), get: jest.fn() }),
}))

// Mock Lenis
jest.mock('@studio-freight/lenis', () => ({
  __esModule: true,
  default: jest.fn().mockImplementation(() => ({
    raf: jest.fn(),
    destroy: jest.fn(),
  })),
}))

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
  }),
  usePathname: () => '/',
  notFound: jest.fn(),
}))
