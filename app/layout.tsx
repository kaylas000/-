import type { Metadata } from 'next'
import { GeistSans } from 'geist/font/sans'
import { Inter_Tight } from 'next/font/google'
import './globals.css'
import SmoothScroll from '@/components/SmoothScroll'
import Navigation from '@/components/Navigation'
import CustomCursor from '@/components/CustomCursor'
import WhatsAppButton from '@/components/WhatsAppButton'
import Analytics from '@/components/Analytics'

const interTight = Inter_Tight({ 
  subsets: ['latin'],
  variable: '--font-inter-tight',
})

export const metadata: Metadata = {
  title: 'Премиум Digital Агентство',
  description: 'Высококлассные цифровые решения',
  metadataBase: new URL('https://youragency.com'),
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ru" className={`${GeistSans.variable} ${interTight.variable}`} translate="no">
      <head>
        <meta name="google" content="notranslate" />
      </head>
      <body className="font-sans cursor-none">
        <Analytics />
        <div className="neural-aura" />
        <div className="noise-overlay" />
        <CustomCursor />
        <Navigation />
        <WhatsAppButton />
        <SmoothScroll>{children}</SmoothScroll>
      </body>
    </html>
  )
}
