import { getContentByType, getContentBySlug } from '@/lib/markdown'

describe('Markdown Utility', () => {
  describe('getContentByType', () => {
    it('returns array of projects', () => {
      const projects = getContentByType('projects')
      expect(Array.isArray(projects)).toBe(true)
      expect(projects.length).toBeGreaterThan(0)
    })

    it('returns array of services', () => {
      const services = getContentByType('services')
      expect(Array.isArray(services)).toBe(true)
      expect(services.length).toBeGreaterThan(0)
    })

    it('projects have required fields', () => {
      const projects = getContentByType('projects')
      const project = projects[0]
      expect(project).toHaveProperty('slug')
      expect(project).toHaveProperty('title')
      expect(project).toHaveProperty('description')
      expect(project).toHaveProperty('content')
    })
  })

  describe('getContentBySlug', () => {
    it('returns project by slug', () => {
      const project = getContentBySlug('projects', 'case-alpha')
      expect(project).not.toBeNull()
      expect(project?.title).toBeDefined()
    })

    it('returns null for non-existent slug', () => {
      const project = getContentBySlug('projects', 'non-existent')
      expect(project).toBeNull()
    })

    it('returns service by slug', () => {
      const service = getContentBySlug('services', 'digital-strategy')
      expect(service).not.toBeNull()
      expect(service?.title).toBeDefined()
    })
  })
})
