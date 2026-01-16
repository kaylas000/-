'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight, ArrowLeft, Check } from 'lucide-react'
import InteractiveFooter from '@/components/InteractiveFooter'

const steps = [
  { id: 1, title: 'Project Type', question: 'What do you need?' },
  { id: 2, title: 'Budget', question: 'What\'s your budget?' },
  { id: 3, title: 'Timeline', question: 'When do you need it?' },
  { id: 4, title: 'Contact', question: 'How can we reach you?' },
]

const projectTypes = ['Website', 'Mobile App', 'E-Commerce', 'Branding', 'AI Integration']
const budgets = ['$10k-$50k', '$50k-$100k', '$100k-$250k', '$250k+']
const timelines = ['ASAP', '1-3 months', '3-6 months', '6+ months']

export default function ContactPage() {
  const [currentStep, setCurrentStep] = useState(1)
  const [formData, setFormData] = useState({
    projectType: '',
    budget: '',
    timeline: '',
    name: '',
    email: '',
    company: '',
    message: '',
  })
  const [submitted, setSubmitted] = useState(false)

  const handleNext = () => {
    if (currentStep < 4) setCurrentStep(currentStep + 1)
  }

  const handleBack = () => {
    if (currentStep > 1) setCurrentStep(currentStep - 1)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitted(true)
    console.log('Form submitted:', formData)
  }

  if (submitted) {
    return (
      <>
        <main className="min-h-screen flex items-center justify-center px-6">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: 'spring' }}
              className="w-24 h-24 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-8"
            >
              <Check className="w-12 h-12 text-dark" />
            </motion.div>
            <h1 className="text-6xl font-black mb-4">Thank You!</h1>
            <p className="text-2xl text-accent mb-8">We'll get back to you within 24 hours.</p>
            <button
              onClick={() => window.location.href = '/'}
              className="px-8 py-4 bg-light text-dark rounded-full font-bold hover:bg-accent transition-colors"
            >
              Back to Home
            </button>
          </motion.div>
        </main>
        <InteractiveFooter />
      </>
    )
  }

  return (
    <>
      <main className="min-h-screen pt-32 px-6">
        <div className="max-w-4xl mx-auto">
          {/* Progress */}
          <div className="mb-16">
            <div className="flex justify-between mb-4">
              {steps.map((step) => (
                <div
                  key={step.id}
                  className={`flex-1 h-2 rounded-full mx-1 transition-all duration-500 ${
                    step.id <= currentStep ? 'bg-accent' : 'bg-accent/10'
                  }`}
                />
              ))}
            </div>
            <p className="text-accent text-sm">
              Step {currentStep} of {steps.length}
            </p>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
            >
              <h2 className="text-6xl font-black mb-12">
                {steps[currentStep - 1].question}
              </h2>

              {currentStep === 1 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {projectTypes.map((type) => (
                    <button
                      key={type}
                      onClick={() => {
                        setFormData({ ...formData, projectType: type })
                        handleNext()
                      }}
                      className={`p-8 rounded-2xl border-2 text-left text-2xl font-bold transition-all duration-300 ${
                        formData.projectType === type
                          ? 'border-accent bg-accent/10'
                          : 'border-accent/10 hover:border-accent/30'
                      }`}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              )}

              {currentStep === 2 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {budgets.map((budget) => (
                    <button
                      key={budget}
                      onClick={() => {
                        setFormData({ ...formData, budget })
                        handleNext()
                      }}
                      className={`p-8 rounded-2xl border-2 text-left text-2xl font-bold transition-all duration-300 ${
                        formData.budget === budget
                          ? 'border-accent bg-accent/10'
                          : 'border-accent/10 hover:border-accent/30'
                      }`}
                    >
                      {budget}
                    </button>
                  ))}
                </div>
              )}

              {currentStep === 3 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {timelines.map((timeline) => (
                    <button
                      key={timeline}
                      onClick={() => {
                        setFormData({ ...formData, timeline })
                        handleNext()
                      }}
                      className={`p-8 rounded-2xl border-2 text-left text-2xl font-bold transition-all duration-300 ${
                        formData.timeline === timeline
                          ? 'border-accent bg-accent/10'
                          : 'border-accent/10 hover:border-accent/30'
                      }`}
                    >
                      {timeline}
                    </button>
                  ))}
                </div>
              )}

              {currentStep === 4 && (
                <form onSubmit={handleSubmit} className="space-y-6">
                  <input
                    type="text"
                    placeholder="Your Name *"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full p-6 bg-accent/5 border border-accent/10 rounded-2xl text-xl focus:border-accent outline-none transition-all"
                  />
                  <input
                    type="email"
                    placeholder="Email Address *"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full p-6 bg-accent/5 border border-accent/10 rounded-2xl text-xl focus:border-accent outline-none transition-all"
                  />
                  <input
                    type="text"
                    placeholder="Company"
                    value={formData.company}
                    onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                    className="w-full p-6 bg-accent/5 border border-accent/10 rounded-2xl text-xl focus:border-accent outline-none transition-all"
                  />
                  <textarea
                    placeholder="Tell us about your project..."
                    rows={6}
                    value={formData.message}
                    onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                    className="w-full p-6 bg-accent/5 border border-accent/10 rounded-2xl text-xl focus:border-accent outline-none transition-all resize-none"
                  />
                  <button
                    type="submit"
                    className="w-full p-6 bg-light text-dark rounded-2xl text-xl font-bold hover:bg-accent transition-all duration-300 flex items-center justify-center gap-3"
                  >
                    Submit Project
                    <ArrowRight className="w-6 h-6" />
                  </button>
                </form>
              )}
            </motion.div>
          </AnimatePresence>

          {/* Navigation */}
          {currentStep < 4 && (
            <div className="flex justify-between mt-12">
              <button
                onClick={handleBack}
                disabled={currentStep === 1}
                className="px-8 py-4 border border-accent/20 rounded-full font-bold disabled:opacity-30 hover:border-accent transition-all flex items-center gap-2"
              >
                <ArrowLeft className="w-5 h-5" />
                Back
              </button>
            </div>
          )}
        </div>
      </main>
      <InteractiveFooter />
    </>
  )
}
