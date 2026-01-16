'use client'

import { motion } from 'framer-motion'
import { Award, Users, Zap, Target } from 'lucide-react'
import InteractiveFooter from '@/components/InteractiveFooter'

const timeline = [
  { year: '2020', event: 'Founded with vision to revolutionize digital' },
  { year: '2021', event: 'Reached $5M ARR, 50+ enterprise clients' },
  { year: '2022', event: 'Expanded to AI-native solutions' },
  { year: '2023', event: 'Awarded Best Digital Agency' },
  { year: '2024', event: 'Leading AI-powered transformations' },
]

const team = [
  { name: 'Alex Chen', role: 'CEO & Founder', expertise: 'Digital Strategy' },
  { name: 'Sarah Kim', role: 'CTO', expertise: 'AI Architecture' },
  { name: 'Marcus Johnson', role: 'Creative Director', expertise: 'Brand Design' },
  { name: 'Elena Rodriguez', role: 'Head of Growth', expertise: 'Performance Marketing' },
]

const values = [
  { icon: Target, title: 'Precision', desc: 'Every pixel, every line of code matters' },
  { icon: Zap, title: 'Speed', desc: 'Ship fast, iterate faster' },
  { icon: Users, title: 'Partnership', desc: 'Your success is our mission' },
  { icon: Award, title: 'Excellence', desc: 'World-class quality, always' },
]

export default function AboutPage() {
  return (
    <>
      <main className="min-h-screen pt-32 px-6">
        <div className="max-w-6xl mx-auto">
          {/* Hero */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="mb-32"
          >
            <h1 className="text-7xl md:text-9xl font-black tracking-tighter mb-8">
              Building the
              <span className="block text-accent">Future of Digital</span>
            </h1>
            <p className="text-2xl text-accent max-w-3xl leading-relaxed">
              We're a team of designers, engineers, and strategists obsessed with creating 
              digital experiences that drive real business outcomes.
            </p>
          </motion.div>

          {/* Values */}
          <section className="mb-32">
            <h2 className="text-5xl font-black mb-16">Our Values</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {values.map((value, i) => (
                <motion.div
                  key={value.title}
                  initial={{ opacity: 0, y: 40 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                  className="bg-accent/5 border border-accent/10 rounded-2xl p-8 hover:border-accent/30 transition-all duration-500"
                >
                  <value.icon className="w-12 h-12 mb-4 text-accent" />
                  <h3 className="text-3xl font-black mb-3">{value.title}</h3>
                  <p className="text-accent text-lg">{value.desc}</p>
                </motion.div>
              ))}
            </div>
          </section>

          {/* Timeline */}
          <section className="mb-32">
            <h2 className="text-5xl font-black mb-16">Our Journey</h2>
            <div className="space-y-8">
              {timeline.map((item, i) => (
                <motion.div
                  key={item.year}
                  initial={{ opacity: 0, x: -40 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                  className="flex gap-8 items-start border-l-2 border-accent/20 pl-8 pb-8"
                >
                  <div className="text-5xl font-black text-accent min-w-[120px]">{item.year}</div>
                  <div className="text-xl text-light pt-2">{item.event}</div>
                </motion.div>
              ))}
            </div>
          </section>

          {/* Team */}
          <section className="mb-32">
            <h2 className="text-5xl font-black mb-16">Leadership Team</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {team.map((member, i) => (
                <motion.div
                  key={member.name}
                  initial={{ opacity: 0, y: 40 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                  whileHover={{ y: -10 }}
                  className="bg-accent/5 border border-accent/10 rounded-2xl p-6 hover:border-accent/30 transition-all duration-500"
                >
                  <div className="w-full aspect-square bg-accent/10 rounded-xl mb-4" />
                  <h3 className="text-xl font-black mb-1">{member.name}</h3>
                  <p className="text-accent text-sm mb-2">{member.role}</p>
                  <p className="text-accent/60 text-xs">{member.expertise}</p>
                </motion.div>
              ))}
            </div>
          </section>
        </div>
      </main>
      <InteractiveFooter />
    </>
  )
}
