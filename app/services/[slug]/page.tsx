import { notFound } from 'next/navigation'
import ReactMarkdown from 'react-markdown'
import { getContentBySlug, getContentByType } from '@/lib/markdown'
import { generateMetadata as genMeta, ProfessionalServiceSchema, BreadcrumbSchema } from '@/components/SEOEngine'
import InteractiveFooter from '@/components/InteractiveFooter'

export async function generateStaticParams() {
  const services = getContentByType('services')
  return services.map((service) => ({ slug: service.slug }))
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const service = getContentBySlug('services', slug)
  if (!service) return {}
  
  return genMeta({
    title: service.title,
    description: service.description,
    path: `/services/${slug}`,
    type: 'service',
  })
}

export default async function ServicePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const service = getContentBySlug('services', slug)
  
  if (!service) notFound()

  return (
    <>
      <ProfessionalServiceSchema name={service.title} description={service.description} />
      <BreadcrumbSchema
        items={[
          { name: 'Home', url: '/' },
          { name: 'Services', url: '/services' },
          { name: service.title, url: `/services/${slug}` },
        ]}
      />
      <article className="min-h-screen px-6 py-32" data-intent="service-offering">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-7xl md:text-8xl font-black tracking-tighter mb-8">{service.title}</h1>
          <p className="text-2xl text-accent mb-20 leading-relaxed">{service.description}</p>

          <ReactMarkdown
            className="prose prose-invert prose-xl max-w-none
              prose-headings:font-black prose-headings:tracking-tighter prose-headings:text-light
              prose-p:text-accent prose-p:leading-relaxed prose-p:text-lg
              prose-a:text-light prose-a:no-underline hover:prose-a:text-accent
              prose-strong:text-light prose-strong:font-bold
              prose-ul:text-accent prose-li:text-accent
              prose-code:text-accent prose-code:bg-accent/10 prose-code:px-2 prose-code:py-1 prose-code:rounded"
          >
            {service.content}
          </ReactMarkdown>
        </div>
      </article>
      <InteractiveFooter />
    </>
  )
}
