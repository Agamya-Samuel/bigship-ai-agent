import { Link, useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { ArrowRight, Package, GitBranch, Route, Warehouse, BarChart3, Zap, MapPin, CheckCircle } from 'lucide-react'
import { getMe } from '../lib/api'
import { ThemeToggle } from '../components/ThemeToggle'
import { AccentButton } from '../components/ui/AccentButton'
import { BrandIcon } from '../components/ui/BrandIcon'

const features = [
  { icon: Route, title: 'Smart Routing', desc: 'Multi-modal path optimization with real-time carrier selection and dynamic rerouting.' },
  { icon: Warehouse, title: 'Warehouse Control', desc: 'Unified inventory visibility across segments — local, regional, and national.' },
  { icon: Package, title: 'Order Intelligence', desc: 'End-to-end order tracking with status forecasting and exception alerts.' },
  { icon: BarChart3, title: 'Rate Engine', desc: 'Instant rate calculation across segments with box-level dimensional pricing.' },
]

const proof = [
  { label: 'Active Shipments', value: '12,847', delta: '+8.3% vs last week' },
  { label: 'On-Time Rate', value: '97.2%', delta: 'Above 95% target' },
  { label: 'Avg Transit Days', value: '2.4', delta: '-0.6 days improved' },
  { label: 'Cost per Mile', value: '$1.83', delta: '-4.1% optimization' },
]

export default function Landing() {
  const navigate = useNavigate()
  const [authed, setAuthed] = useState<boolean | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      getMe().then(() => setAuthed(true)).catch(() => setAuthed(false))
    } else {
      setAuthed(false)
    }
  }, [])

  const handleGetStarted = () => {
    if (authed) {
      navigate({ to: '/chat', search: { threadId: 'new' } })
    } else {
      navigate({ to: '/login' })
    }
  }

  if (authed === null) {
    return (
      <div className="min-h-screen bg-(--bg-primary) flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-(--border-secondary) border-t-(--accent) animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-(--bg-primary) text-(--text-secondary) font-sans antialiased">
      {/* Header */}
      <header className="border-b border-(--border-primary) bg-(--bg-primary)/80 backdrop-blur-sm sticky top-0 z-50" style={{ height: 'calc(3.5rem + env(safe-area-inset-top))' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between" style={{ paddingTop: 'env(safe-area-inset-top)' }}>
          <div className="flex items-center gap-2.5">
            <BrandIcon size="md" />
            <span className="text-sm font-semibold tracking-wide text-(--text-primary)">BIGSHIP</span>
          </div>
          <nav className="flex items-center gap-2 sm:gap-6">
            <a href="#features" className="px-2.5 py-1 text-[10px] sm:text-xs uppercase tracking-widest text-(--text-tertiary) hover:text-(--text-secondary) transition-colors">Platform</a>
            <a href="#proof" className="px-2.5 py-1 text-[10px] sm:text-xs uppercase tracking-widest text-(--text-tertiary) hover:text-(--text-secondary) transition-colors">Metrics</a>
            <a href="#workflow" className="px-2.5 py-1 text-[10px] sm:text-xs uppercase tracking-widest text-(--text-tertiary) hover:text-(--text-secondary) transition-colors">Workflow</a>
            <ThemeToggle />
            <AccentButton size="md" onClick={handleGetStarted}>
              {authed ? 'Open Dashboard' : 'Sign In'}
            </AccentButton>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="border-b border-(--border-primary)">
        <div className="max-w-7xl mx-auto px-6 py-20 lg:py-28 grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <div className="flex items-center gap-2 mb-6">
              <div className="h-px w-8 bg-(--accent)" />
              <span className="text-[10px] uppercase tracking-[0.2em] text-(--accent) font-medium">Logistics Intelligence Platform</span>
            </div>
            <h1 className="text-4xl lg:text-5xl font-bold tracking-tight text-(--text-primary) leading-[1.05] mb-6">
              Ship smarter.
              <br />
              <span className="text-(--accent)">Route faster.</span>
            </h1>
            <p className="text-(--text-tertiary) text-lg leading-relaxed max-w-md mb-8">
              End-to-end freight intelligence — real-time routing, warehouse control, order tracking, and rate calculation in one operational surface.
            </p>
            <div className="flex items-center gap-4">
              <AccentButton size="lg" onClick={handleGetStarted} className="px-5 py-2.5">
                Start Operating
                <ArrowRight className="w-4 h-4" />
              </AccentButton>
              <a href="#features" className="text-xs uppercase tracking-widest text-(--text-tertiary) hover:text-(--text-secondary) transition-colors">Explore Platform →</a>
            </div>
          </div>
          <div className="relative">
            {/* Proof object: live operations board */}
            <div className="border border-(--border-primary) bg-(--bg-secondary) p-5">
              <div className="flex items-center justify-between mb-4">
                <span className="text-[10px] uppercase tracking-[0.15em] text-(--text-tertiary)">Live Operations</span>
                <span className="flex items-center gap-1.5 text-[10px] text-(--accent)">
                  <span className="w-1.5 h-1.5 bg-(--accent) animate-pulse" />
                  LIVE
                </span>
              </div>
              <div className="space-y-2">
                {[
                  { id: 'BS-4821', route: 'Mumbai → Chennai', status: 'In Transit', eta: '14h' },
                  { id: 'BS-3902', route: 'Delhi → Bangalore', status: 'Dispatch', eta: '6h' },
                  { id: 'BS-7103', route: 'Kolkata → Hyderabad', status: 'In Transit', eta: '22h' },
                  { id: 'BS-2256', route: 'Pune → Mumbai', status: 'Delivered', eta: 'Arrived' },
                ].map((shipment) => (
                  <div key={shipment.id} className="flex items-center justify-between py-2 border-b border-(--border-primary) last:border-0">
                    <div className="flex items-center gap-3">
                      <span className="text-[10px] text-(--text-tertiary) font-mono">{shipment.id}</span>
                      <span className="text-xs text-(--text-secondary)">{shipment.route}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-[10px] uppercase tracking-wider ${shipment.status === 'Delivered' ? 'text-green-500' : 'text-(--accent)'}`}>{shipment.status}</span>
                      <span className="text-[10px] text-(--text-tertiary) font-mono">{shipment.eta}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            {/* Accent edge */}
            <div className="absolute -top-2 -right-2 w-16 h-16 border-t border-r border-(--accent)/20 pointer-events-none" />
            <div className="absolute -bottom-2 -left-2 w-16 h-16 border-b border-l border-(--accent)/20 pointer-events-none" />
          </div>
        </div>
      </section>

      {/* Proof Metrics */}
      <section id="proof" className="border-b border-(--border-primary) bg-(--bg-secondary)">
        <div className="max-w-7xl mx-auto px-6 py-12 grid grid-cols-2 lg:grid-cols-4 gap-8">
          {proof.map((item) => (
            <div key={item.label} className="space-y-1.5">
              <span className="text-[10px] uppercase tracking-[0.15em] text-(--text-tertiary)">{item.label}</span>
              <div className="text-2xl lg:text-3xl font-bold text-(--text-primary) tracking-tight">{item.value}</div>
              <span className="text-[10px] text-(--accent)">{item.delta}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="border-b border-(--border-primary)">
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="flex items-end justify-between mb-12">
            <div>
              <span className="text-[10px] uppercase tracking-[0.2em] text-(--accent) mb-3 block">Platform Capabilities</span>
              <h2 className="text-2xl lg:text-3xl font-bold text-(--text-primary) tracking-tight">Four surfaces. One control layer.</h2>
            </div>
            <Link to="/login" className="hidden lg:flex items-center gap-2 px-2.5 py-1 text-xs uppercase tracking-widest text-(--text-tertiary) hover:text-(--text-secondary) transition-colors">
              Full platform access <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="grid md:grid-cols-2 gap-px bg-(--border-primary)">
            {features.map((f, i) => (
              <div key={f.title} className="bg-(--bg-secondary) p-6 lg:p-8 group hover:bg-(--bg-tertiary) transition-colors">
                <div className="flex items-start justify-between">
                  <div className="w-9 h-9 border border-(--border-secondary) bg-(--bg-primary) flex items-center justify-center mb-4 group-hover:border-(--accent)/30 transition-colors">
                    <f.icon className="w-4 h-4 text-(--accent)" />
                  </div>
                  <span className="text-[10px] text-(--border-secondary) font-mono">0{i + 1}</span>
                </div>
                <h3 className="text-base font-semibold text-(--text-secondary) mb-2">{f.title}</h3>
                <p className="text-sm text-(--text-tertiary) leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Workflow */}
      <section id="workflow" className="border-b border-(--border-primary)">
        <div className="max-w-7xl mx-auto px-6 py-16">
          <span className="text-[10px] uppercase tracking-[0.2em] text-(--accent) mb-3 block">How It Operates</span>
          <h2 className="text-2xl lg:text-3xl font-bold text-(--text-primary) tracking-tight mb-12">From dispatch to confirmation.</h2>
          <div className="grid md:grid-cols-4 gap-px bg-(--border-primary)">
            {[
              { step: '01', title: 'Ingest', desc: 'Orders, routes, and warehouse data flow into the platform via API or manual entry.', icon: Zap },
              { step: '02', title: 'Analyze', desc: 'The engine evaluates capacity, cost, and timeline across all active carriers.', icon: GitBranch },
              { step: '03', title: 'Route', desc: 'Optimal paths are assigned with real-time carrier selection and exception handling.', icon: MapPin },
              { step: '04', title: 'Confirm', desc: 'Status updates, rate calc, and delivery confirmation in a single operational view.', icon: CheckCircle },
            ].map((s) => (
              <div key={s.step} className="bg-(--bg-secondary) p-6 lg:p-8 group hover:bg-(--bg-tertiary) transition-colors">
                <span className="text-[10px] text-(--accent) font-mono mb-3 block">{s.step}</span>
                <div className="w-8 h-8 border border-(--border-secondary) bg-(--bg-primary) flex items-center justify-center mb-4 group-hover:border-(--accent)/30 transition-colors">
                  <s.icon className="w-4 h-4 text-(--accent)" />
                </div>
                <h3 className="text-sm font-semibold text-(--text-secondary) mb-2">{s.title}</h3>
                <p className="text-xs text-(--text-tertiary) leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-6 text-center">
          <h2 className="text-2xl lg:text-4xl font-bold text-(--text-primary) tracking-tight mb-4">Ready to operate?</h2>
          <p className="text-(--text-tertiary) max-w-md mx-auto mb-8">Sign in to access the full dashboard — routing, warehouses, orders, and rate calculation.</p>
          <AccentButton size="lg" onClick={handleGetStarted}>
            Sign In to Platform
            <ArrowRight className="w-4 h-4" />
          </AccentButton>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-(--border-primary) bg-(--bg-secondary)">
        <div className="max-w-7xl mx-auto px-6 py-8 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BrandIcon size="sm" />
            <span className="text-xs text-(--text-tertiary) font-semibold tracking-wide">BIGSHIP</span>
          </div>
          <span className="text-[10px] text-(--text-tertiary) uppercase tracking-widest">Freight Intelligence Platform</span>
        </div>
      </footer>
    </div>
  )
}
