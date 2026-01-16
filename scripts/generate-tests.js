#!/usr/bin/env node

const fs = require('fs')
const path = require('path')

const args = process.argv.slice(2)
const filePath = args[0]

if (!filePath) {
  console.error('Usage: npm run test:generate <file-path>')
  console.error('Example: npm run test:generate components/MyComponent.tsx')
  process.exit(1)
}

const fullPath = path.join(process.cwd(), filePath)
if (!fs.existsSync(fullPath)) {
  console.error(`File not found: ${fullPath}`)
  process.exit(1)
}

const fileName = path.basename(filePath, path.extname(filePath))
const fileDir = path.dirname(filePath)
const isComponent = fileDir.includes('components')
const isLib = fileDir.includes('lib')
const isPage = fileDir.includes('app')

// Read file content
const fileContent = fs.readFileSync(fullPath, 'utf-8')
const isClientComponent = fileContent.includes("'use client'")
const hasExportDefault = fileContent.includes('export default')
const exportedFunctions = fileContent.match(/export (?:async )?function (\w+)/g) || []

// Determine test directory
let testDir = '__tests__'
if (isComponent) testDir = path.join(testDir, 'components')
else if (isLib) testDir = path.join(testDir, 'lib')
else if (isPage) testDir = path.join(testDir, 'app')

// Create test directory if it doesn't exist
if (!fs.existsSync(testDir)) {
  fs.mkdirSync(testDir, { recursive: true })
}

// Generate test file path
const testFilePath = path.join(testDir, `${fileName}.test.tsx`)

// Check if test already exists
if (fs.existsSync(testFilePath)) {
  console.log(`⚠️  Test already exists: ${testFilePath}`)
  console.log('Skipping generation.')
  process.exit(0)
}

// Generate test template
let testTemplate = ''

if (isComponent && isClientComponent) {
  testTemplate = `import { render, screen } from '@testing-library/react'
import ${fileName} from '@/${filePath.replace(/\\/g, '/').replace('.tsx', '').replace('.ts', '')}'

describe('${fileName} Component', () => {
  it('renders without crashing', () => {
    render(<${fileName} />)
  })

  it('renders expected content', () => {
    render(<${fileName} />)
    // Add your assertions here
    // expect(screen.getByText('...')).toBeInTheDocument()
  })

  it('handles user interactions', () => {
    render(<${fileName} />)
    // Add interaction tests here
    // const button = screen.getByRole('button')
    // fireEvent.click(button)
  })
})
`
} else if (isComponent && !isClientComponent) {
  testTemplate = `import { render, screen } from '@testing-library/react'
import ${fileName} from '@/${filePath.replace(/\\/g, '/').replace('.tsx', '').replace('.ts', '')}'

describe('${fileName} Component', () => {
  it('renders without crashing', () => {
    render(<${fileName} />)
  })

  it('renders expected content', () => {
    render(<${fileName} />)
    // Add your assertions here
  })
})
`
} else if (isLib) {
  const functions = exportedFunctions.map(f => f.match(/function (\w+)/)?.[1]).filter(Boolean)
  
  testTemplate = `import { ${functions.join(', ')} } from '@/${filePath.replace(/\\/g, '/').replace('.tsx', '').replace('.ts', '')}'

describe('${fileName} Utility', () => {
${functions.map(fn => `  describe('${fn}', () => {
    it('works correctly', () => {
      // Add your test here
      expect(${fn}).toBeDefined()
    })

    it('handles edge cases', () => {
      // Add edge case tests
    })
  })
`).join('\n')}
})
`
} else {
  testTemplate = `import { render, screen } from '@testing-library/react'

describe('${fileName}', () => {
  it('works correctly', () => {
    // Add your test here
    expect(true).toBe(true)
  })
})
`
}

// Write test file
fs.writeFileSync(testFilePath, testTemplate)

console.log(`✅ Test generated: ${testFilePath}`)
console.log(`\nNext steps:`)
console.log(`1. Open ${testFilePath}`)
console.log(`2. Add specific test cases`)
console.log(`3. Run: npm test`)
