import { useState, type FormEvent } from 'react'
import { useNavigate, useLocation } from '@tanstack/react-router'
import { login } from '../lib/api'
import { ArrowLeft, Eye, EyeOff, Loader2, ShieldCheck, Sparkles } from 'lucide-react'
import { ThemeToggle } from '../components/ThemeToggle'
import { BrandLogo } from '../components/ui/BrandIcon'

function getQueryPrompt(search?: string): string {
  if (!search) return ''
  const params = new URLSearchParams(search)
  return params.get('q') ?? ''
}

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const prompt = getQueryPrompt(location.search)

  const [userName, setUserName] = useState('')
  const [password, setPassword] = useState('')
  const [accessKey, setAccessKey] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await login({ user_name: userName, password, access_key: accessKey })
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('account_id', data.account_id)
      window.location.href = '/'
    } catch (err: unknown) {
      if (!err || typeof err !== 'object' || !('response' in err)) {
        setError('Server unavailable. Please try again later.')
      } else if ((err as { response?: { status?: number } }).response?.status === 401) {
        setError('Invalid credentials. Please try again.')
      } else if (
        (err as { response?: { status?: number } }).response?.status &&
        (err as { response?: { status?: number } }).response!.status! >= 500
      ) {
        setError('Internal server error. Please try again later.')
      } else {
        setError('Something went wrong. Please try again later.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg-base)] text-[var(--text-primary)] flex flex-col">
      <header
        className="border-b border-[var(--border-subtle)]"
        style={{ paddingTop: 'env(safe-area-inset-top)' }}
      >
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate({ to: '/' })}
              className="inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
            <span className="text-[var(--border-default)]" aria-hidden>/</span>
            <BrandLogo size="sm" />
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="flex-1 flex">
        {/* Form side */}
        <div className="flex-1 flex items-center justify-center px-4 sm:px-8 py-10">
          <div className="w-full max-w-sm slide-up">
            <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)] mb-1.5">
              Welcome back
            </h1>
            <p className="text-sm text-[var(--text-secondary)] mb-7">
              Sign in with your Bigship merchant credentials to start chatting with the agent.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <Field
                label="Username"
                value={userName}
                onChange={setUserName}
                placeholder="your-merchant-id"
                autoComplete="username"
                required
              />
              <Field
                label="Password"
                value={password}
                onChange={setPassword}
                placeholder="••••••••"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                required
                trailing={
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors p-0.5 -mr-1"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                }
              />
              <Field
                label="Access key"
                value={accessKey}
                onChange={setAccessKey}
                placeholder="Paste your Bigship access key"
                autoComplete="off"
                required
              />

              {error && (
                <p
                  role="alert"
                  className="text-sm text-[var(--danger)] bg-[var(--accent-soft)]/40 border border-[var(--danger)]/20 rounded-lg px-3 py-2"
                >
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[var(--accent)] text-white font-medium hover:bg-[var(--accent-hover)] disabled:opacity-60 disabled:cursor-not-allowed transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-base)]"
              >
                {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                {loading ? 'Signing in…' : 'Sign in'}
              </button>
            </form>

            <p className="mt-5 text-xs text-[var(--text-tertiary)] text-center">
              Credentials are encrypted at rest with Fernet and never sent to the LLM.
            </p>
          </div>
        </div>

        {/* Preview side — hidden on mobile */}
        <aside className="hidden lg:flex flex-1 items-center justify-center bg-[var(--bg-subtle)] border-l border-[var(--border-subtle)] p-10">
          <div className="w-full max-w-md">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[var(--bg-elevated)] border border-[var(--border-subtle)] text-xs text-[var(--text-secondary)] mb-4">
              <Sparkles className="h-3 w-3 text-[var(--accent)]" />
              Preview
            </div>
            <h2 className="text-xl font-semibold tracking-tight text-[var(--text-primary)] mb-2">
              {prompt ? 'Ready when you are.' : 'See what you can do.'}
            </h2>
            <p className="text-sm text-[var(--text-secondary)] mb-5 leading-relaxed">
              After signing in you&apos;ll be taken straight to a chat surface where the agent can act on your account.
            </p>

            <div className="space-y-3">
              {prompt ? (
                <PreviewUserBubble message={prompt} />
              ) : (
                <>
                  <PreviewUserBubble message="Track shipment BS-4821" />
                  <PreviewAssistantBubble
                    message="Pulled the latest event for BS-4821 — currently **In Transit** on the Mumbai → Chennai lane, ETA **tomorrow 11:30 AM**. Want me to alert you if it slips past 12 PM?"
                  />
                </>
              )}
            </div>

            <div className="mt-6 flex items-center gap-2 text-xs text-[var(--text-tertiary)]">
              <ShieldCheck className="h-3.5 w-3.5" />
              Encrypted at rest · per-session memory
            </div>
          </div>
        </aside>
      </main>
    </div>
  )
}

function Field({
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
  autoComplete,
  required,
  trailing,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
  placeholder?: string
  autoComplete?: string
  required?: boolean
  trailing?: React.ReactNode
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">{label}</label>
      <div className="relative">
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          required={required}
          className="w-full px-3.5 py-2.5 bg-[var(--bg-base)] border border-[var(--border-default)] rounded-lg text-base sm:text-sm text-[var(--text-primary)] placeholder:text-[var(--text-quaternary)] focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)] transition-colors disabled:opacity-60"
        />
        {trailing && <div className="absolute right-2 top-1/2 -translate-y-1/2">{trailing}</div>}
      </div>
    </div>
  )
}

function PreviewUserBubble({ message }: { message: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] px-3.5 py-2 rounded-2xl bg-[var(--accent)] text-white text-sm leading-relaxed">
        {message}
      </div>
    </div>
  )
}

function PreviewAssistantBubble({ message }: { message: string }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] px-3.5 py-2.5 rounded-2xl bg-[var(--bg-elevated)] border border-[var(--border-subtle)] text-sm text-[var(--text-primary)] leading-relaxed">
        {message}
      </div>
    </div>
  )
}