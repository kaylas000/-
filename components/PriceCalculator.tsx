'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Calculator, Check } from 'lucide-react'

const options = {
  type: [
    { name: 'Landing Page', price: 15000 },
    { name: 'Corporate Website', price: 50000 },
    { name: 'E-Commerce', price: 100000 },
    { name: 'Web App', price: 200000 },
    { name: 'Mobile App', price: 250000 },
  ],
  features: [
    { name: 'Custom Design', price: 30000 },
    { name: 'AI Integration', price: 80000 },
    { name: 'CMS', price: 20000 },
    { name: 'Analytics', price: 15000 },
    { name: 'SEO Optimization', price: 25000 },
  ],
  timeline: [
    { name: 'Standard (3-6 months)', multiplier: 1 },
    { name: 'Fast (1-3 months)', multiplier: 1.5 },
    { name: 'Express (< 1 month)', multiplier: 2 },
  ],
}

export default function PriceCalculator() {
  const [selected, setSelected] = useState({
    type: '',
    features: [] as string[],
    timeline: '',
  })

  const calculatePrice = () => {
    let base = options.type.find((t) => t.name === selected.type)?.price || 0
    let featuresTotal = selected.features.reduce((sum, f) => {
      return sum + (options.features.find((opt) => opt.name === f)?.price || 0)
    }, 0)
    let multiplier = options.timeline.find((t) => t.name === selected.timeline)?.multiplier || 1
    return Math.round((base + featuresTotal) * multiplier)
  }

  const toggleFeature = (feature: string) => {
    setSelected({
      ...selected,
      features: selected.features.includes(feature)
        ? selected.features.filter((f) => f !== feature)
        : [...selected.features, feature],
    })
  }

  return (
    <div className="bg-accent/5 border border-accent/10 rounded-3xl p-8 md:p-12">
      <div className="flex items-center gap-4 mb-8">
        <Calculator className="w-8 h-8 text-accent" />
        <h3 className="text-4xl font-black">Калькулятор проекта</h3>
      </div>

      {/* Project Type */}
      <div className="mb-8">
        <label className="text-xl font-bold mb-4 block">Тип проекта</label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {options.type.map((type) => (
            <button
              key={type.name}
              onClick={() => setSelected({ ...selected, type: type.name })}
              className={`p-4 rounded-xl border-2 text-left transition-all ${
                selected.type === type.name
                  ? 'border-accent bg-accent/10'
                  : 'border-accent/10 hover:border-accent/30'
              }`}
            >
              <div className="font-bold">{type.name}</div>
              <div className="text-sm text-accent">
                from ${(type.price / 1000).toFixed(0)}k
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Features */}
      <div className="mb-8">
        <label className="text-xl font-bold mb-4 block">Дополнительные функции</label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {options.features.map((feature) => (
            <button
              key={feature.name}
              onClick={() => toggleFeature(feature.name)}
              className={`p-4 rounded-xl border-2 text-left transition-all flex items-center gap-3 ${
                selected.features.includes(feature.name)
                  ? 'border-accent bg-accent/10'
                  : 'border-accent/10 hover:border-accent/30'
              }`}
            >
              <div
                className={`w-6 h-6 rounded border-2 flex items-center justify-center ${
                  selected.features.includes(feature.name)
                    ? 'border-accent bg-accent'
                    : 'border-accent/30'
                }`}
              >
                {selected.features.includes(feature.name) && (
                  <Check className="w-4 h-4 text-dark" />
                )}
              </div>
              <div className="flex-1">
                <div className="font-bold">{feature.name}</div>
                <div className="text-sm text-accent">
                  +${(feature.price / 1000).toFixed(0)}k
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Timeline */}
      <div className="mb-8">
        <label className="text-xl font-bold mb-4 block">Сроки</label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {options.timeline.map((timeline) => (
            <button
              key={timeline.name}
              onClick={() => setSelected({ ...selected, timeline: timeline.name })}
              className={`p-4 rounded-xl border-2 text-center transition-all ${
                selected.timeline === timeline.name
                  ? 'border-accent bg-accent/10'
                  : 'border-accent/10 hover:border-accent/30'
              }`}
            >
              <div className="font-bold">{timeline.name}</div>
              <div className="text-sm text-accent">
                {timeline.multiplier > 1 ? `×${timeline.multiplier}` : 'Standard'}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Result */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-dark border-2 border-accent rounded-2xl p-8 text-center"
      >
        <div className="text-accent text-sm mb-2">Ориентировочная стоимость</div>
        <div className="text-6xl font-black mb-4">
          ${(calculatePrice() / 1000).toFixed(0)}k
        </div>
        <button className="px-8 py-4 bg-light text-dark rounded-full font-bold hover:bg-accent transition-all">
          Получить предложение
        </button>
      </motion.div>
    </div>
  )
}
