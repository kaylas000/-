'use client'

import { motion } from 'framer-motion'
import { Users, Award, TrendingUp, Zap } from 'lucide-react'

const stats = [
  { icon: Users, value: '200+', label: 'Довольных клиентов' },
  { icon: Award, value: '15+', label: 'Наград и сертификатов' },
  { icon: TrendingUp, value: '98%', label: 'Успешных проектов' },
  { icon: Zap, value: '24/7', label: 'Техподдержка' },
]

export default function SocialProof() {
  return (
    <section className="px-6 py-20 border-y border-accent/10">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="text-center"
            >
              <stat.icon className="w-12 h-12 mx-auto mb-4 text-accent" />
              <div className="text-5xl font-black mb-2">{stat.value}</div>
              <div className="text-accent">{stat.label}</div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
