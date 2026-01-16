'use client'

import { motion } from 'framer-motion'
import ServiceAccordion from '@/components/ServiceAccordion'
import InteractiveFooter from '@/components/InteractiveFooter'
import { Zap, Target, Sparkles, TrendingUp } from 'lucide-react'

const services = [
  {
    icon: Zap,
    title: 'Digital Strategy',
    description: 'Transform your business with data-driven digital strategies',
  },
  {
    icon: Target,
    title: 'Brand Design',
    description: 'Create memorable brand identities that resonate',
  },
  {
    icon: Sparkles,
    title: 'Web Development',
    description: 'Build high-performance web applications',
  },
  {
    icon: TrendingUp,
    title: 'Growth Marketing',
    description: 'Scale your business with proven marketing strategies',
  },
]

const methodology = [
  {
    title: '01. Discovery & Research',
    content: 'We begin with deep research into your business, competitors, and target audience. This phase includes stakeholder interviews, market analysis, and user research to establish a solid foundation.',
  },
  {
    title: '02. Strategy & Planning',
    content: 'Based on insights from discovery, we develop a comprehensive strategy with clear objectives, KPIs, and roadmap. Every decision is backed by data and aligned with your business goals.',
  },
  {
    title: '03. Design & Development',
    content: 'Our team creates pixel-perfect designs and develops high-performance solutions using cutting-edge technologies. We follow agile methodology with regular check-ins and iterations.',
  },
  {
    title: '04. Testing & Optimization',
    content: 'Rigorous testing across devices and browsers ensures flawless performance. We use A/B testing and analytics to continuously optimize for better results.',
  },
  {
    title: '05. Launch & Support',
    content: 'Smooth deployment with zero downtime, followed by ongoing monitoring and support. We provide training and documentation to ensure your team can manage the solution effectively.',
  },
]

export default function ServicesPage() {
  return (
    <>
      <main className="min-h-screen pt-32 px-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="mb-32"
          >
            <h1 className="text-7xl md:text-9xl font-black tracking-tighter mb-8">
              Services
            </h1>
            <p className="text-2xl text-accent max-w-3xl leading-relaxed">
              End-to-end digital solutions that drive measurable business outcomes.
            </p>
          </motion.div>

          {/* Services Grid */}
          <section className="mb-32">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {services.map((service, i) => (
                <motion.div
                  key={service.title}
                  initial={{ opacity: 0, y: 40 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                  className="group bg-accent/5 border border-accent/10 rounded-2xl p-8 hover:border-accent/30 transition-all duration-500"
                >
                  <service.icon className="w-12 h-12 mb-6 text-accent group-hover:scale-110 transition-transform" />
                  <h3 className="text-3xl font-black mb-4">{service.title}</h3>
                  <p className="text-accent text-lg">{service.description}</p>
                </motion.div>
              ))}
            </div>
          </section>

          {/* Methodology */}
          <section className="mb-32">
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="mb-12"
            >
              <h2 className="text-5xl md:text-6xl font-black mb-6">Our Methodology</h2>
              <p className="text-xl text-accent max-w-3xl">
                A proven process that delivers exceptional results, every time.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
            >
              <ServiceAccordion items={methodology} />
            </motion.div>
          </section>

          {/* CTA */}
          <motion.section
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mb-32 text-center"
          >
            <div className="bg-accent/5 border border-accent/10 rounded-3xl p-16">
              <h2 className="text-5xl font-black mb-6">Ready to Start?</h2>
              <p className="text-xl text-accent mb-8 max-w-2xl mx-auto">
                Let's discuss how we can help transform your digital presence.
              </p>
              <a
                href="/contact"
                className="inline-block px-10 py-5 bg-light text-dark rounded-full font-bold text-lg hover:bg-accent transition-all duration-300 hover:scale-105"
              >
                Get in Touch
              </a>
            </div>
          </motion.section>
        </div>
      </main>
      <InteractiveFooter />
    </>
  )
}
