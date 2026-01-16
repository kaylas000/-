import { Metadata } from 'next'

interface SEOProps {
  title: string
  description: string
  path?: string
  type?: 'website' | 'article' | 'service'
  image?: string
}

export function generateMetadata({
  title,
  description,
  path = '',
  image = '/og-image.jpg',
}: SEOProps): Metadata {
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
  }
}

export function OrganizationSchema() {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'Premium Digital Agency',
    url: 'https://youragency.com',
    logo: 'https://youragency.com/logo.png',
    contactPoint: {
      '@type': 'ContactPoint',
      contactType: 'Customer Service',
      email: 'hello@youragency.com',
    },
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

export function ServiceSchema({ name, description }: { name: string; description: string }) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Service',
    name,
    description,
    provider: {
      '@type': 'Organization',
      name: 'Premium Digital Agency',
    },
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}
