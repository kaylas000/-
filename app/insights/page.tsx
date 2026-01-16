'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { ArrowRight, Clock } from 'lucide-react'
import InteractiveFooter from '@/components/InteractiveFooter'

const insights = [
  {
    slug: 'ai-native-design',
    title: 'AI-Native Design: The Future of Digital Experiences',
    excerpt: 'How artificial intelligence is reshaping the way we approach design systems and user experiences.',
    date: '2024-03-15',
    readTime: '8 min',
    category: 'Design',
  },
  {
    slug: 'performance-obsession',
    title: 'Performance Obsession: Why Speed Matters More Than Ever',
    excerpt: 'Deep dive into web performance optimization and its impact on business metrics.',
    date: '2024-03-10',
    readTime: '12 min',
    category: 'Engineering',
  },
  {
    slug: 'aeo-revolution',
    title: 'AEO Revolution: Optimizing for AI Search Engines',
    excerpt: 'Answer Engine Optimization strategies for the age of ChatGPT and Perplexity.',
    date: '2024-03-05',
    readTime: '10 min',
    category: 'SEO',
  },
]

export default function InsightsPage() {
  return (
    <>
      <main className="min-h-screen pt-32 px-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="mb-20"
          >
            <h1 className="text-7xl md:text-9xl font-black tracking-tighter mb-6">
              Insights
            </h1>
            <p className="text-2xl text-accent max-w-3xl">
              Thought leadership on design, technology, and digital transformation.
            </p>
          </motion.div>

          {/* Featured Article */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mb-20"
          >
            <Link href={`/insights/${insights[0].slug}`}>
              <div className="group relative aspect-[21/9] bg-accent/5 rounded-3xl overflow-hidden border border-accent/10 hover:border-accent/30 transition-all duration-500">
                <div className="absolute inset-0 bg-gradient-to-t from-dark via-dark/50 to-transparent" />
                <div className="absolute inset-0 p-12 flex flex-col justify-end">
                  <div className="text-sm text-accent mb-4 flex items-center gap-4">
                    <span className="px-3 py-1 bg-accent/20 rounded-full">{insights[0].category}</span>
                    <span className="flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      {insights[0].readTime}
                    </span>
                  </div>
                  <h2 className="text-5xl font-black mb-4 group-hover:text-accent transition-colors">
                    {insights[0].title}
                  </h2>
                  <p className="text-xl text-accent mb-6 max-w-3xl">
                    {insights[0].excerpt}
                  </p>
                  <div className="flex items-center gap-2 text-light">
                    Read Article
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-2 transition-transform" />
                  </div>
                </div>
              </div>
            </Link>
          </motion.div>

          {/* Articles Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-20">
            {insights.slice(1).map((article, i) => (
              <motion.div
                key={article.slug}
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <Link href={`/insights/${article.slug}`}>
                  <div className="group h-full bg-accent/5 rounded-2xl p-8 border border-accent/10 hover:border-accent/30 transition-all duration-500">
                    <div className="text-sm text-accent mb-4 flex items-center gap-4">
                      <span className="px-3 py-1 bg-accent/20 rounded-full">{article.category}</span>
                      <span className="flex items-center gap-2">
                        <Clock className="w-4 h-4" />
                        {article.readTime}
                      </span>
                    </div>
                    <h3 className="text-3xl font-black mb-4 group-hover:text-accent transition-colors">
                      {article.title}
                    </h3>
                    <p className="text-accent mb-6">
                      {article.excerpt}
                    </p>
                    <div className="flex items-center gap-2 text-light">
                      Read More
                      <ArrowRight className="w-4 h-4 group-hover:translate-x-2 transition-transform" />
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </main>
      <InteractiveFooter />
    </>
  )
}
