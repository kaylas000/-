import { notFound } from 'next/navigation'
import ReactMarkdown from 'react-markdown'
import { getContentBySlug, getContentByType } from '@/lib/markdown'
import { generateMetadata as genMeta, CaseStudySchema, BreadcrumbSchema } from '@/components/SEOEngine'
import InteractiveFooter from '@/components/InteractiveFooter'

export async function generateStaticParams() {
  const projects = getContentByType('projects')
  return projects.map((project) => ({ slug: project.slug }))
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const project = getContentBySlug('projects', slug)
  if (!project) return {}
  
  return genMeta({
    title: project.title,
    description: project.description,
    path: `/projects/${slug}`,
    type: 'article',
  })
}

export default async function ProjectPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const project = getContentBySlug('projects', slug)
  
  if (!project) notFound()

  return (
    <>
      <CaseStudySchema
        title={project.title}
        description={project.description}
        businessOutcome={project.business_outcome}
        techStack={project.tech_stack}
        intentScore={project.intent_score}
      />
      <BreadcrumbSchema
        items={[
          { name: 'Home', url: '/' },
          { name: 'Projects', url: '/projects' },
          { name: project.title, url: `/projects/${slug}` },
        ]}
      />
      <article className="min-h-screen px-6 py-32" data-intent={project.intent_score}>
        <div className="max-w-4xl mx-auto">
          <h1 className="text-7xl md:text-8xl font-black tracking-tighter mb-8">{project.title}</h1>
          <p className="text-2xl text-accent mb-4 leading-relaxed">{project.description}</p>
          
          {project.business_outcome && (
            <div className="text-lg text-light/80 mb-16 pb-8 border-b border-accent/10">
              <span className="text-accent font-bold">Outcome:</span> {project.business_outcome}
            </div>
          )}
          
          {project.metrics && (
            <div className="flex flex-wrap gap-6 mb-20 pb-20 border-b border-accent/10">
              {project.metrics.map((metric, i) => (
                <div key={i} className="bg-accent/5 backdrop-blur-sm border border-accent/10 rounded-xl p-6 min-w-[160px]">
                  <div className="text-5xl font-black mb-2">{metric.value}</div>
                  <div className="text-sm text-accent uppercase tracking-wider">{metric.label}</div>
                </div>
              ))}
            </div>
          )}

          <ReactMarkdown
            className="prose prose-invert prose-xl max-w-none
              prose-headings:font-black prose-headings:tracking-tighter prose-headings:text-light
              prose-p:text-accent prose-p:leading-relaxed prose-p:text-lg
              prose-a:text-light prose-a:no-underline hover:prose-a:text-accent
              prose-strong:text-light prose-strong:font-bold
              prose-ul:text-accent prose-li:text-accent
              prose-code:text-accent prose-code:bg-accent/10 prose-code:px-2 prose-code:py-1 prose-code:rounded"
          >
            {project.content}
          </ReactMarkdown>

          {project.tech_stack && (
            <div className="mt-20 pt-12 border-t border-accent/10">
              <h3 className="text-2xl font-black mb-6">Technology Stack</h3>
              <div className="flex flex-wrap gap-3">
                {project.tech_stack.map((tech, i) => (
                  <span key={i} className="px-4 py-2 bg-accent/10 text-light rounded-full text-sm font-medium">
                    {tech}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </article>
      <InteractiveFooter />
    </>
  )
}
