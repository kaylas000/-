'use client'

import { motion } from 'framer-motion'
import ServiceAccordion from '@/components/ServiceAccordion'
import InteractiveFooter from '@/components/InteractiveFooter'
import { FAQSchema } from '@/components/SEOEngine'

const faqs = [
  {
    title: 'Сколько стоит разработка сайта?',
    content: 'Стоимость зависит от сложности проекта. Базовый сайт от 500,000₽, корпоративный портал от 2,000,000₽, сложные веб-приложения от 5,000,000₽. Точная оценка после брифа.',
  },
  {
    title: 'Какие сроки разработки?',
    content: 'Лендинг - 2-4 недели, корпоративный сайт - 2-3 месяца, веб-приложение - 4-6 месяцев. Сроки зависят от объема функционала и количества интеграций.',
  },
  {
    title: 'Предоставляете ли техподдержку?',
    content: 'Да, предоставляем техническую поддержку и сопровождение. Включает мониторинг, обновления, исправление ошибок. Стоимость от 50,000₽/месяц.',
  },
  {
    title: 'Работаете с международными клиентами?',
    content: 'Да, работаем с клиентами по всему миру. Поддерживаем удаленную работу, используем современные инструменты коммуникации.',
  },
  {
    title: 'Какие технологии используете?',
    content: 'Next.js 15, React, TypeScript, Node.js, Python, PostgreSQL, MongoDB, AWS, Docker, Kubernetes. Выбираем стек под задачи проекта.',
  },
  {
    title: 'Можно ли увидеть портфолио?',
    content: 'Да, на странице проектов представлены наши кейсы. Под NDA можем показать дополнительные работы при личной встрече.',
  },
  {
    title: 'Как происходит оплата?',
    content: 'Работаем по этапам: 30% предоплата, 40% после дизайна, 30% после запуска. Для крупных проектов возможна помесячная оплата.',
  },
  {
    title: 'Предоставляете ли гарантию?',
    content: 'Да, гарантия 12 месяцев на все разработанные решения. Бесплатное исправление ошибок в течение гарантийного периода.',
  },
]

const faqSchemaData = faqs.map(faq => ({
  question: faq.title,
  answer: faq.content,
}))

export default function FAQPage() {
  return (
    <>
      <FAQSchema faqs={faqSchemaData} />
      <main className="min-h-screen pt-32 px-6">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-16"
          >
            <h1 className="text-7xl md:text-8xl font-black tracking-tighter mb-6">
              Частые вопросы
            </h1>
            <p className="text-2xl text-accent">
              Ответы на популярные вопросы о наших услугах
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <ServiceAccordion items={faqs} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-16 text-center bg-accent/5 border border-accent/10 rounded-2xl p-12"
          >
            <h2 className="text-3xl font-black mb-4">Не нашли ответ?</h2>
            <p className="text-accent mb-6">
              Свяжитесь с нами, и мы ответим на все ваши вопросы
            </p>
            <a
              href="/contact"
              className="inline-block px-8 py-4 bg-light text-dark rounded-full font-bold hover:bg-accent transition-all"
            >
              Связаться с нами
            </a>
          </motion.div>
        </div>
      </main>
      <InteractiveFooter />
    </>
  )
}
