'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { ContentItem } from '@/lib/markdown'

export default function PortfolioGrid({ projects }: { projects: ContentItem[] }) {
  return (
    <section className="px-6 py-32" data-intent="portfolio-showcase">
      <div className="max-w-7xl mx-auto">
        <h2 className="text-6xl md:text-7xl font-black tracking-tighter mb-20">Избранные проекты</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {projects.map((project, index) => (
            <motion.div
              key={project.slug}
              initial={{ opacity: 0, y: 60 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-100px' }}
              transition={{ duration: 0.8, delay: index * 0.15, ease: [0.22, 1, 0.36, 1] }}
            >
              <Link href={`/projects/${project.slug}`}>
                <div className="group relative aspect-[4/3] bg-gradient-to-br from-accent/10 to-accent/5 rounded-2xl overflow-hidden cursor-pointer border border-accent/10 hover:border-accent/30 transition-all duration-500">
                  {/* Metric Glow Overlay */}
                  <div className="absolute inset-0 bg-gradient-to-t from-dark via-dark/90 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 ease-in-out backdrop-blur-sm" />
                  
                  <div className="absolute inset-0 p-10 flex flex-col justify-end translate-y-6 group-hover:translate-y-0 transition-transform duration-500 ease-in-out">
                    <h3 className="text-4xl font-black tracking-tighter mb-3">{project.title}</h3>
                    <p className="text-accent text-lg mb-6 opacity-0 group-hover:opacity-100 transition-opacity duration-500 ease-in-out delay-75">
                      {project.description}
                    </p>
                    
                    {project.metrics && (
                      <div className="flex gap-8 opacity-0 group-hover:opacity-100 transition-opacity duration-500 ease-in-out delay-150">
                        {project.metrics.map((metric, i) => (
                          <div key={i} className="glassmorphic p-4 rounded-lg bg-light/5 backdrop-blur-md border border-light/10">
                            <div className="text-3xl font-black text-light mb-1">{metric.value}</div>
                            <div className="text-sm text-accent uppercase tracking-wider">{metric.label}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
