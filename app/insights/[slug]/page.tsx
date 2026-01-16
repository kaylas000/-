import { notFound } from 'next/navigation'
import ReactMarkdown from 'react-markdown'
import { getContentBySlug, getContentByType } from '@/lib/markdown'
import { generateMetadata as genMeta, BreadcrumbSchema } from '@/components/SEOEngine'
import InteractiveFooter from '@/components/InteractiveFooter'
import { Clock } from 'lucide-react'

export async function generateStaticParams() {
  const insights = getContentByType('insights')
  return insights.map((insight) => ({ slug: insight.slug }))
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const insight = getContentBySlug('insights', slug)
  if (!insight) return {}
  
  return genMeta({
    title: insight.title,
    description: insight.description,
    path: `/insights/${slug}`,
    type: 'article',
  })
}

export default async function InsightPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const insight = getContentBySlug('insights', slug)
  
  if (!insight) notFound()

  return (
    <>
      <BreadcrumbSchema
        items={[
          { name: 'Home', url: '/' },
          { name: 'Insights', url: '/insights' },
          { name: insight.title, url: `/insights/${slug}` },
        ]}
      />
      <article className="min-h-screen pt-32 px-6" data-intent="thought-leadership">
        <div className="max-w-4xl mx-auto">
          <div className="mb-12">
            <div className="flex items-center gap-4 text-accent mb-6">
              {insight.date && (
                <time className="text-sm">{new Date(insight.date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</time>
              )}
              <span className="flex items-center gap-2 text-sm">
                <Clock className="w-4 h-4" />
                8 min read
              </span>
            </div>
            <h1 className="text-6xl md:text-7xl font-black tracking-tighter mb-6">{insight.title}</h1>
            <p className="text-2xl text-accent leading-relaxed">{insight.description}</p>
          </div>

          <div className="w-full h-px bg-accent/10 mb-12" />

          <ReactMarkdown
            className="prose prose-invert prose-xl max-w-none
              prose-headings:font-black prose-headings:tracking-tighter prose-headings:text-light
              prose-p:text-accent prose-p:leading-relaxed prose-p:text-lg prose-p:mb-6
              prose-a:text-light prose-a:no-underline hover:prose-a:text-accent
              prose-strong:text-light prose-strong:font-bold
              prose-ul:text-accent prose-li:text-accent prose-li:mb-2
              prose-blockquote:border-l-4 prose-blockquote:border-accent prose-blockquote:pl-6 prose-blockquote:italic
              prose-code:text-accent prose-code:bg-accent/10 prose-code:px-2 prose-code:py-1 prose-code:rounded"
          >
            {insight.content}
          </ReactMarkdown>
        </div>
      </article>
      <InteractiveFooter />
    </>
  )
}
