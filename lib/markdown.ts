import fs from 'fs'
import path from 'path'
import matter from 'gray-matter'

const contentDirectory = path.join(process.cwd(), 'content')

export interface ContentItem {
  slug: string
  title: string
  description: string
  date?: string
  intent_score?: number
  business_outcome?: string
  tech_stack?: string[]
  metrics?: {
    label: string
    value: string
  }[]
  content: string
}

export function getContentByType(type: 'projects' | 'services' | 'insights'): ContentItem[] {
  const dir = path.join(contentDirectory, type)
  const files = fs.readdirSync(dir)

  return files
    .filter((file) => file.endsWith('.md'))
    .map((file) => {
      const slug = file.replace(/\.md$/, '')
      const fullPath = path.join(dir, file)
      const fileContents = fs.readFileSync(fullPath, 'utf8')
      const { data, content } = matter(fileContents)

      return {
        slug,
        title: data.title,
        description: data.description,
        date: data.date,
        intent_score: data.intent_score,
        business_outcome: data.business_outcome,
        tech_stack: data.tech_stack,
        metrics: data.metrics,
        content,
      }
    })
    .sort((a, b) => (a.date && b.date ? new Date(b.date).getTime() - new Date(a.date).getTime() : 0))
}

export function getContentBySlug(type: 'projects' | 'services' | 'insights', slug: string): ContentItem | null {
  try {
    const fullPath = path.join(contentDirectory, type, `${slug}.md`)
    const fileContents = fs.readFileSync(fullPath, 'utf8')
    const { data, content } = matter(fileContents)

    return {
      slug,
      title: data.title,
      description: data.description,
      date: data.date,
      intent_score: data.intent_score,
      business_outcome: data.business_outcome,
      tech_stack: data.tech_stack,
      metrics: data.metrics,
      content,
    }
  } catch {
    return null
  }
}
