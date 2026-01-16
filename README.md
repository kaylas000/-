# Premium Digital Agency Website

High-end digital agency website built with Next.js 15, TypeScript, and Tailwind CSS. Features AI-managed content through Markdown files and GitOps workflow.

## Architecture

- **Framework**: Next.js 15 (App Router)
- **Styling**: Tailwind CSS with Silent Luxury theme
- **Animations**: Framer Motion + Lenis smooth scroll
- **Content**: Markdown-based (GitOps)
- **Icons**: Lucide React
- **Testing**: Jest + React Testing Library

## Design System

- Background: `#050505`
- Text: `#FAFAFA`
- Accent: `#8E8E93`
- Neural Aura background effects
- Procedural noise overlay

## Getting Started

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Run tests
npm test

# Build for production
npm run build
```

## Testing

### Run Tests

```bash
# Watch mode
npm test

# CI mode with coverage
npm run test:ci

# Generate test for new file
npm run test:generate components/MyComponent.tsx
```

### Coverage Requirements

- Minimum 70% coverage required
- Automated checks in CI/CD
- See [TESTING.md](./TESTING.md) for details

## Project Structure

```
/app                    # Next.js App Router
  /about                # About page
  /contact              # Contact form
  /projects/[slug]      # Dynamic project pages
  /services/[slug]      # Dynamic service pages
/components             # Shared UI components
  Hero.tsx              # Hero with reveal animation
  Navigation.tsx        # Premium navigation
  SEOEngine.tsx         # Metadata & Schema.org
  PortfolioGrid.tsx     # Masonry portfolio layout
  PriceCalculator.tsx   # Interactive calculator
  InteractiveFooter.tsx # Footer with AI status
  CustomCursor.tsx      # Custom cursor effect
/content                # Markdown content
  /projects             # Case studies
  /services             # Service pages
/lib                    # Utilities
  markdown.ts           # Content parser
/__tests__              # Test files
  /components           # Component tests
  /lib                  # Utility tests
/scripts                # Automation scripts
  generate-tests.js     # Auto-generate tests
```

## Content Management

Add new projects or services by creating Markdown files in `/content`:

```markdown
---
title: "Project Title"
description: "Brief description"
date: "2024-01-15"
metrics:
  - label: "Metric"
    value: "+340%"
---

## Content here
```

### AI Content Generation

Use GitHub Actions to auto-generate content:

1. Go to Actions tab
2. Run "AI Content Manager" workflow
3. Fill in title and description
4. Content is automatically created and committed

## Deployment

GitHub Actions workflow automatically:
1. Runs all tests (70% coverage required)
2. Type-checks TypeScript
3. Runs Lighthouse CI (99+ score required)
4. Deploys to Vercel on success

### Deployment Blockers

- ❌ Test failures
- ❌ Coverage < 70%
- ❌ TypeScript errors
- ❌ Lighthouse score < 99

## Performance

- Lighthouse score target: 99+
- Smooth 60fps animations
- Edge-optimized delivery
- Optimized bundle size (~102KB)
- Test coverage: 70%+

## Features

### UI/UX
- ✅ Premium animated navigation
- ✅ Custom magnetic cursor
- ✅ Smooth scroll (Lenis)
- ✅ Framer Motion animations
- ✅ Responsive design

### Pages
- ✅ Home with hero & portfolio
- ✅ About with timeline & team
- ✅ Multi-step contact form
- ✅ Dynamic project pages
- ✅ Dynamic service pages

### Tools
- ✅ Interactive price calculator
- ✅ AI content generation
- ✅ SEO optimization
- ✅ Schema.org markup

### Testing
- ✅ Automated test generation
- ✅ 70% coverage requirement
- ✅ CI/CD integration
- ✅ Pre-deployment checks

## Scripts

```bash
npm run dev          # Start dev server
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
npm run type-check   # TypeScript check
npm test             # Run tests (watch)
npm run test:ci      # Run tests (CI)
npm run test:generate <file> # Generate test
```

## Documentation

- [Testing Guide](./TESTING.md) - Complete testing documentation
- [GitHub Actions](./.github/workflows/) - CI/CD workflows

## License

Proprietary - Premium Digital Agency
