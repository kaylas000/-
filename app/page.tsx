import Hero from '@/components/Hero'
import PortfolioGrid from '@/components/PortfolioGrid'
import InteractiveFooter from '@/components/InteractiveFooter'
import PriceCalculator from '@/components/PriceCalculator'
import SocialProof from '@/components/SocialProof'
import { OrganizationSchema } from '@/components/SEOEngine'
import { getContentByType } from '@/lib/markdown'

export default function Home() {
  const projects = getContentByType('projects')

  return (
    <>
      <OrganizationSchema />
      <Hero />
      <SocialProof />
      <div id="work">
        <PortfolioGrid projects={projects} />
      </div>
      <section className="px-6 py-32">
        <div className="max-w-4xl mx-auto">
          <PriceCalculator />
        </div>
      </section>
      <InteractiveFooter />
    </>
  )
}
