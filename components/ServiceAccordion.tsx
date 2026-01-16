'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown } from 'lucide-react'

interface AccordionItem {
  title: string
  content: string
}

interface AccordionProps {
  items: AccordionItem[]
}

export default function ServiceAccordion({ items }: AccordionProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  return (
    <div className="space-y-2 sm:space-y-4">
      {items.map((item, index) => (
        <div
          key={index}
          className="border border-accent/10 rounded-lg sm:rounded-2xl overflow-hidden bg-accent/5 hover:border-accent/30 transition-all duration-300"
        >
          <button
            onClick={() => setOpenIndex(openIndex === index ? null : index)}
            className="w-full p-4 sm:p-8 flex justify-between items-center text-left gap-3"
          >
            <h3 className="text-lg sm:text-2xl font-black flex-1">{item.title}</h3>
            <motion.div
              animate={{ rotate: openIndex === index ? 180 : 0 }}
              transition={{ duration: 0.3 }}
              className="flex-shrink-0"
            >
              <ChevronDown className="w-5 sm:w-6 h-5 sm:h-6 text-accent" />
            </motion.div>
          </button>
          
          <AnimatePresence>
            {openIndex === index && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
              >
                <div className="px-4 sm:px-8 pb-4 sm:pb-8 text-accent text-sm sm:text-lg leading-relaxed">
                  {item.content}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ))}
    </div>
  )
}
