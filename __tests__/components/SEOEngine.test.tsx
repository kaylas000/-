import { generateMetadata } from '@/components/SEOEngine'

describe('SEOEngine', () => {
  describe('generateMetadata', () => {
    it('generates basic metadata', () => {
      const metadata = generateMetadata({
        title: 'Test Title',
        description: 'Test Description',
      })

      expect(metadata.title).toBe('Test Title')
      expect(metadata.description).toBe('Test Description')
    })

    it('generates OpenGraph metadata', () => {
      const metadata = generateMetadata({
        title: 'Test Title',
        description: 'Test Description',
        path: '/test',
      })

      expect(metadata.openGraph).toBeDefined()
      expect(metadata.openGraph?.title).toBe('Test Title')
      expect(metadata.openGraph?.url).toContain('/test')
    })

    it('generates Twitter metadata', () => {
      const metadata = generateMetadata({
        title: 'Test Title',
        description: 'Test Description',
      })

      expect(metadata.twitter).toBeDefined()
      expect(metadata.twitter?.title).toBe('Test Title')
      expect(metadata.twitter?.card).toBe('summary_large_image')
    })

    it('includes edge-cache header', () => {
      const metadata = generateMetadata({
        title: 'Test',
        description: 'Test',
      })

      expect(metadata.other).toBeDefined()
      expect(metadata.other?.['edge-cache']).toBe('max-age=3600')
    })
  })
})
