'use client'

import { useEffect, useState } from 'react'
import { Circle, GitCommit } from 'lucide-react'

export default function InteractiveFooter() {
  const [time, setTime] = useState('')
  const [commitHash] = useState('a3f9c2e')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    const updateTime = () => {
      setTime(new Date().toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit',
        timeZone: 'UTC'
      }))
    }
    updateTime()
    const interval = setInterval(updateTime, 1000)
    return () => clearInterval(interval)
  }, [])

  if (!mounted) return null

  return (
    <footer className="border-t border-accent/10 px-6 py-16 bg-dark/50 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
          {/* AI Status */}
          <div className="flex items-center gap-3">
            <Circle className="w-3 h-3 fill-green-500 text-green-500 animate-pulse" />
            <div>
              <div className="text-sm font-bold text-light">ИИ Менеджер</div>
              <div className="text-xs text-accent">Системы активны</div>
            </div>
          </div>

          {/* Build Info */}
          <div className="flex items-center gap-3">
            <GitCommit className="w-4 h-4 text-accent" />
            <div>
              <div className="text-sm font-bold text-light">Последняя сборка</div>
              <div className="text-xs text-accent font-mono">{commitHash}</div>
            </div>
          </div>

          {/* Time */}
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-accent animate-pulse" />
            <div>
              <div className="text-sm font-bold text-light">Время UTC</div>
              <div className="text-xs text-accent font-mono">{time}</div>
            </div>
          </div>
        </div>

        <div className="border-t border-accent/10 pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="text-sm text-accent">
            © 2024 Premium Agency. Создано с точностью.
          </div>
          <div className="flex gap-6 text-sm text-accent">
            <a href="/privacy" className="hover:text-light transition-colors">Конфиденциальность</a>
            <a href="/terms" className="hover:text-light transition-colors">Условия</a>
            <a href="/contact" className="hover:text-light transition-colors">Контакты</a>
          </div>
        </div>
      </div>
    </footer>
  )
}
