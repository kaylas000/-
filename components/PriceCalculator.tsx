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
    <div className="bg-accent/5 border border-accent/10 rounded-2xl sm:rounded-3xl p-4 sm:p-6 md:p-8 lg:p-12">
      <div className="flex items-center gap-3 sm:gap-4 mb-6 sm:mb-8">
        <Calculator className="w-6 sm:w-8 h-6 sm:h-8 text-accent flex-shrink-0" />
        <h3 className="text-2xl sm:text-3xl md:text-4xl font-black">Калькулятор проекта</h3>
      </div>

      {/* Project Type */}
      <div className="mb-6 sm:mb-8">
        <label className="text-base sm:text-lg md:text-xl font-bold mb-3 sm:mb-4 block">Тип проекта</label>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 gap-2 sm:gap-3">
          {options.type.map((type) => (
            <button
              key={type.name}
              onClick={() => setSelected({ ...selected, type: type.name })}
              className={`p-3 sm:p-4 rounded-lg sm:rounded-xl border-2 text-left transition-all text-xs sm:text-sm ${
                selected.type === type.name
                  ? 'border-accent bg-accent/10'
                  : 'border-accent/10 hover:border-accent/30'
              }`}
            >
              <div className="font-bold">{type.name}</div>
              <div className="text-xs sm:text-sm text-accent">
                from ${(type.price / 1000).toFixed(0)}k
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Features */}
      <div className="mb-6 sm:mb-8">
        <label className="text-base sm:text-lg md:text-xl font-bold mb-3 sm:mb-4 block">Дополнительные функции</label>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 gap-2 sm:gap-3">
          {options.features.map((feature) => (
            <button
              key={feature.name}
              onClick={() => toggleFeature(feature.name)}
              className={`p-3 sm:p-4 rounded-lg sm:rounded-xl border-2 text-left transition-all flex items-center gap-2 sm:gap-3 text-xs sm:text-sm ${
                selected.features.includes(feature.name)
                  ? 'border-accent bg-accent/10'
                  : 'border-accent/10 hover:border-accent/30'
              }`}
            >
              <div
                className={`w-5 sm:w-6 h-5 sm:h-6 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                  selected.features.includes(feature.name)
                    ? 'border-accent bg-accent'
                    : 'border-accent/30'
                }`}
              >
                {selected.features.includes(feature.name) && (
                  <Check className="w-3 sm:w-4 h-3 sm:h-4 text-dark" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-bold truncate">{feature.name}</div>
                <div className="text-xs sm:text-sm text-accent">
                  +${(feature.price / 1000).toFixed(0)}k
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Timeline */}
      <div className="mb-6 sm:mb-8">
        <label className="text-base sm:text-lg md:text-xl font-bold mb-3 sm:mb-4 block">Сроки</label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3">
          {options.timeline.map((timeline) => (
            <button
              key={timeline.name}
              onClick={() => setSelected({ ...selected, timeline: timeline.name })}
              className={`p-3 sm:p-4 rounded-lg sm:rounded-xl border-2 text-center transition-all text-xs sm:text-sm ${
                selected.timeline === timeline.name
                  ? 'border-accent bg-accent/10'
                  : 'border-accent/10 hover:border-accent/30'
              }`}
            >
              <div className="font-bold truncate">{timeline.name}</div>
              <div className="text-xs sm:text-sm text-accent">
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
        className="bg-dark border-2 border-accent rounded-xl sm:rounded-2xl p-4 sm:p-6 md:p-8 text-center mt-6 sm:mt-8"
      >
        <div className="text-accent text-xs sm:text-sm mb-1 sm:mb-2">Ориентировочная стоимость</div>
        <div className="text-4xl sm:text-5xl md:text-6xl font-black mb-3 sm:mb-4">
          ${(calculatePrice() / 1000).toFixed(0)}k
        </div>
        <button className="px-4 sm:px-6 md:px-8 py-2.5 sm:py-3 md:py-4 bg-light text-dark rounded-full font-bold hover:bg-accent transition-all text-xs sm:text-sm md:text-base">
          Получить предложение
        </button>
      </motion.div>
    </div>
  )
}
