'use client'

import { motion, useMotionValue, useSpring } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import { useRef, MouseEvent } from 'react'

export default function Hero() {
  const buttonRef = useRef<HTMLButtonElement>(null)
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  
  const springX = useSpring(x, { stiffness: 150, damping: 15 })
  const springY = useSpring(y, { stiffness: 150, damping: 15 })

  const handleMouseMove = (e: MouseEvent<HTMLButtonElement>) => {
    if (!buttonRef.current) return
    const rect = buttonRef.current.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2
    const distance = Math.sqrt(
      Math.pow(e.clientX - centerX, 2) + Math.pow(e.clientY - centerY, 2)
    )
    
    if (distance < 60) {
      x.set((e.clientX - centerX) * 0.5)
      y.set((e.clientY - centerY) * 0.5)
    }
  }

  const handleMouseLeave = () => {
    x.set(0)
    y.set(0)
  }

  return (
    <section className="min-h-screen flex items-center justify-center px-4 md:px-6 pt-32 relative overflow-hidden">
      {/* WebGL-inspired gradient background */}
      <div className="absolute inset-0 opacity-30">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-accent/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-light/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
      </div>

      <div className="max-w-6xl w-full relative z-10">
        <motion.h1
          className="text-3xl sm:text-5xl md:text-7xl lg:text-8xl xl:text-9xl font-black tracking-tighter mb-6 md:mb-8 leading-[0.9]"
          initial={{ opacity: 0, y: 60 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
        >
          <motion.span 
            className="block"
            initial={{ opacity: 0, x: -40 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
            translate="no"
          >
            Цифровое совершенство
          </motion.span>
          <motion.span 
            className="block text-accent"
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1, delay: 0.4, ease: [0.22, 1, 0.36, 1] }}
            translate="no"
          >
            Созданное с точностью
          </motion.span>
        </motion.h1>

        <motion.p
          className="text-sm sm:text-base md:text-xl lg:text-2xl text-accent max-w-2xl mb-8 md:mb-12 leading-relaxed"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.6, ease: [0.22, 1, 0.36, 1] }}
          translate="no"
        >
          Мы создаём премиум цифровые продукты для брендов, которые требуют совершенства.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.8, ease: [0.22, 1, 0.36, 1] }}
        >
          <motion.button
            ref={buttonRef}
            style={{ x: springX, y: springY }}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            className="group relative px-6 sm:px-8 md:px-10 py-4 md:py-5 bg-light text-dark font-bold rounded-full overflow-hidden transition-all duration-500 ease-in-out hover:scale-105 hover:shadow-2xl"
            translate="no"
          >
            <span className="relative z-10 flex items-center gap-2 md:gap-3 text-base md:text-lg">
              Начать проект
              <ArrowRight className="w-5 h-5 md:w-6 md:h-6 transition-transform duration-500 ease-in-out group-hover:translate-x-2" />
            </span>
            <motion.div
              className="absolute inset-0 bg-accent"
              initial={{ scale: 0, opacity: 0 }}
              whileHover={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            />
          </motion.button>
        </motion.div>
      </div>
    </section>
  )
}
