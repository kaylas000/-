import { Metadata } from 'next'

interface SEOEngineProps {
  title: string
  description: string
  path?: string
  type?: 'website' | 'article' | 'service'
  image?: string
  intentScore?: number
  businessOutcome?: string
  techStack?: string[]
}

export function generateMetadata({
  title,
  description,
  path = '',
  image = '/og-image.jpg',
}: SEOEngineProps): Metadata {
  const url = `https://youragency.com${path}`
  
  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url,
      siteName: 'Premium Digital Agency',
      images: [{ url: image }],
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
      images: [image],
    },
    other: {
      'edge-cache': 'max-age=3600',
    },
  }
}

export function OrganizationSchema() {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'Premium Digital Agency',
    url: 'https://youragency.com',
    logo: 'https://youragency.com/logo.png',
    description: 'AI-native digital agency delivering measurable business outcomes',
    contactPoint: {
      '@type': 'ContactPoint',
      contactType: 'Customer Service',
      email: 'hello@youragency.com',
    },
    sameAs: [
      'https://twitter.com/youragency',
      'https://linkedin.com/company/youragency',
    ],
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

export function ProfessionalServiceSchema({ name, description }: { name: string; description: string }) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'ProfessionalService',
    name,
    description,
    provider: {
      '@type': 'Organization',
      name: 'Premium Digital Agency',
    },
    areaServed: 'Worldwide',
    serviceType: 'Digital Transformation',
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

export function CaseStudySchema({
  title,
  description,
  businessOutcome,
  techStack,
  intentScore,
}: SEOEngineProps) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: title,
    description,
    author: {
      '@type': 'Organization',
      name: 'Premium Digital Agency',
    },
    publisher: {
      '@type': 'Organization',
      name: 'Premium Digital Agency',
      logo: {
        '@type': 'ImageObject',
        url: 'https://youragency.com/logo.png',
      },
    },
    about: {
      '@type': 'Thing',
      name: 'Digital Transformation',
      description: businessOutcome,
    },
    keywords: techStack?.join(', '),
    'data-intent': intentScore,
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

export function BreadcrumbSchema({ items }: { items: { name: string; url: string }[] }) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: `https://youragency.com${item.url}`,
    })),
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

export function FAQSchema({ faqs }: { faqs: { question: string; answer: string }[] }) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqs.map((faq) => ({
      '@type': 'Question',
      name: faq.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faq.answer,
      },
    })),
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}
