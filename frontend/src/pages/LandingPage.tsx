import { useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import {
  ArrowRight,
  CheckCircle2,
  Sparkles,
  Truck,
  Warehouse,
  Package,
  BarChart3,
} from 'lucide-react'
import { getMe } from '../lib/api'
import { ThemeToggle } from '../components/ThemeToggle'
import { BrandLogo } from '../components/ui/BrandIcon'
import { suggestions, type Suggestion } from '../lib/suggestions'

const capabilities = [
  {
    icon: Truck,
    title: 'Smart routing',
    body: 'Multi-modal path optimization with real-time carrier selection across couriers.',
  },
  {
    icon: Warehouse,
    title: 'Warehouse control',
    body: 'One inventory view across every pickup location you operate.',
  },
  {
    icon: Package,
    title: 'Order intelligence',
    body: 'End-to-end order tracking, status forecasting, and exception alerts.',
  },
  {
    icon: BarChart3,
    title: 'Rate engine',
    body: 'Instant rate calculation with dimensional pricing across all segments.',
  },
]

function StepBadge({ index }: { index: number }) {
  return (
    <span className="inline-flex items-center justify-center w-6 h-6 rounded-full border border-[var(--border-subtle)] text-[10px] font-mono text-[var(--text-tertiary)]">
      0{index}
    </span>
  )
}

function HeaderNav({ cta }: { cta: { label: string; onClick: () => void } }) {
  return (
    <header className="sticky top-0 z-30 bg-[var(--bg-overlay)] backdrop-blur-md border-b border-[var(--border-subtle)]">
      <div
        className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between"
        style={{ paddingTop: 'env(safe-area-inset-top)' }}
      >
        <BrandLogo size="md" />
        <nav className="flex items-center gap-1 sm:gap-2">
          <a
            href="#capabilities"
            className="hidden sm:block px-3 py-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            Capabilities
          </a>
          <a
            href="#workflow"
            className="hidden sm:block px-3 py-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            Workflow
          </a>
          <ThemeToggle />
          <button
            onClick={cta.onClick}
            className="ml-1 px-3.5 py-1.5 text-sm font-medium rounded-lg bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-base)] whitespace-nowrap shrink-0"
          >
            {cta.label}
          </button>
        </nav>
      </div>
    </header>
  )
}

function SuggestionCard({ suggestion, onPick }: { suggestion: Suggestion; onPick: (p: string) => void }) {
  const Icon = suggestion.icon
  return (
    <button
      onClick={() => onPick(suggestion.prompt)}
      className="group text-left p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] hover:border-[var(--border-default)] hover:bg-[var(--bg-subtle)] transition-all hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-base)]"
    >
      <div className="flex items-center gap-2.5 mb-2">
        <Icon className="h-4 w-4 text-[var(--text-secondary)] group-hover:text-[var(--accent)] transition-colors" strokeWidth={2} />
        <span className="text-sm font-medium text-[var(--text-primary)]">{suggestion.title}</span>
      </div>
      <p className="text-xs text-[var(--text-tertiary)] leading-relaxed line-clamp-2">{suggestion.prompt}</p>
    </button>
  )
}

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

  const handleStart = (prompt?: string) => {
    if (authed) {
      navigate({ to: '/chat', search: prompt ? { threadId: 'new', q: prompt } : { threadId: 'new' } })
    } else {
      navigate({ to: '/login', search: prompt ? { q: prompt } : {} })
    }
  }

  if (authed === null) {
    return (
      <div className="min-h-screen bg-[var(--bg-base)] flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-[var(--border-default)] border-t-[var(--accent)] rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[var(--bg-base)] text-[var(--text-primary)]">
      <HeaderNav cta={{ label: authed ? 'Open chat' : 'Sign in', onClick: () => handleStart() }} />

      {/* Hero — Claude-style */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-[var(--accent-soft)]/40 via-transparent to-transparent" />
        <div className="max-w-3xl mx-auto px-4 sm:px-6 pt-16 sm:pt-24 pb-10 text-center fade-in">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-xs text-[var(--text-secondary)] mb-6">
            <Sparkles className="h-3 w-3 text-[var(--accent)]" />
            <span>Logistics, operated by conversation</span>
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight text-[var(--text-primary)] leading-[1.05]">
            Ship smarter.
            <br />
            <span className="text-[var(--text-secondary)]">Just ask.</span>
          </h1>
          <p className="mt-5 text-base sm:text-lg text-[var(--text-secondary)] max-w-xl mx-auto leading-relaxed px-2 sm:px-0">
            Bigship&apos;s AI agent handles routing, warehouse lookups, rate calculations, and order tracking — so your team stops switching tabs.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3 flex-wrap">
            <button
              onClick={() => handleStart()}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-[var(--accent)] text-white font-medium hover:bg-[var(--accent-hover)] transition-colors shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-base)] min-h-11"
            >
              Start chatting
              <ArrowRight className="h-4 w-4" />
            </button>
            <a
              href="#capabilities"
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-secondary)] font-medium hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)] transition-colors min-h-11"
            >
              See capabilities
            </a>
          </div>
        </div>
      </section>

      {/* Suggestion cards — ChatGPT-style starter grid */}
      <section className="max-w-3xl mx-auto px-4 sm:px-6 pb-16">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {suggestions.map((s) => (
            <SuggestionCard key={s.title} suggestion={s} onPick={handleStart} />
          ))}
        </div>
      </section>

      {/* Capabilities */}
      <section id="capabilities" className="border-t border-[var(--border-subtle)] bg-[var(--bg-subtle)]/50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
          <div className="text-center mb-12">
            <p className="text-xs uppercase tracking-wider text-[var(--text-tertiary)] mb-2">Platform</p>
            <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[var(--text-primary)]">
              Four surfaces. One chat layer.
            </h2>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            {capabilities.map((c) => {
              const Icon = c.icon
              return (
                <div
                  key={c.title}
                  className="p-6 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] hover:shadow-[var(--shadow-sm)] transition-shadow"
                >
                  <div className="w-9 h-9 rounded-lg bg-[var(--accent-soft)] flex items-center justify-center mb-4">
                    <Icon className="h-4 w-4 text-[var(--accent)]" strokeWidth={2} />
                  </div>
                  <h3 className="text-base font-medium text-[var(--text-primary)] mb-1.5">{c.title}</h3>
                  <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{c.body}</p>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Workflow */}
      <section id="workflow" className="border-t border-[var(--border-subtle)]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
          <div className="text-center mb-12">
            <p className="text-xs uppercase tracking-wider text-[var(--text-tertiary)] mb-2">Workflow</p>
            <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[var(--text-primary)]">
              From prompt to confirmation.
            </h2>
          </div>
          <div className="space-y-4">
            {[
              { step: 1, title: 'Ask in plain English', body: 'Type what you need — track an order, calculate a rate, create a shipment.' },
              { step: 2, title: 'Agent reasons + acts', body: 'Picks the right tools from your Bigship account, queries them, and assembles the answer.' },
              { step: 3, title: 'You review the trace', body: 'Every tool call is visible. Open the reasoning and inputs to see exactly what happened.' },
              { step: 4, title: 'Confirmation lands in chat', body: 'Order IDs, rates, and tracking events appear as a structured response — ready to act on.' },
            ].map((item) => (
              <div
                key={item.step}
                className="flex items-start gap-4 p-5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)]"
              >
                <StepBadge index={item.step} />
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-[var(--text-primary)] mb-1">{item.title}</h3>
                  <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{item.body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust strip */}
      <section className="border-t border-[var(--border-subtle)]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
          <div className="flex flex-col sm:flex-row items-center justify-center gap-x-8 gap-y-3 text-sm text-[var(--text-tertiary)]">
            <span className="inline-flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-[var(--success)]" />
              Encrypted credential storage
            </span>
            <span className="inline-flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-[var(--success)]" />
              Per-session memory
            </span>
            <span className="inline-flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-[var(--success)]" />
              Service-key guarded
            </span>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-[var(--border-subtle)] bg-[var(--bg-subtle)]/50">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16 text-center">
          <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[var(--text-primary)] mb-3">
            Ready to operate by chat?
          </h2>
          <p className="text-[var(--text-secondary)] mb-7 max-w-md mx-auto">
            Sign in with your Bigship merchant credentials and the agent picks up where your dashboard left off.
          </p>
          <button
            onClick={() => handleStart()}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[var(--accent)] text-white font-medium hover:bg-[var(--accent-hover)] transition-colors shadow-[var(--shadow-sm)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-base)]"
          >
            {authed ? 'Open chat' : 'Sign in to start'}
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </section>

      <Footer />
    </div>
  )
}

function Footer() {
  const year = new Date().getFullYear()
  return (
    <footer className="border-t border-[var(--border-subtle)]">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-[var(--text-tertiary)]">
        <BrandLogo size="sm" />
        <span>© {year} Bigship · Freight intelligence, in chat.</span>
      </div>
    </footer>
  )
}