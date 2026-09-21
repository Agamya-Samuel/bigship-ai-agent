import { useState } from 'react'
import { login } from '../lib/api'
import { LogIn } from 'lucide-react'
import { ThemeToggle } from '../components/ThemeToggle'
import { BrandIcon } from '../components/ui/BrandIcon'

export default function Login() {
  const [userName, setUserName] = useState('')
  const [password, setPassword] = useState('')
  const [accessKey, setAccessKey] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
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
      } else if ((err as { response?: { status?: number } }).response?.status && (err as { response?: { status?: number } }).response!.status! >= 500) {
        setError('Internal server error. Please try again later.')
      } else {
        setError('Something went wrong. Please try again later.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-(--bg-primary) text-(--text-secondary) font-sans antialiased flex flex-col" style={{ paddingTop: 'env(safe-area-inset-top)' }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <BrandIcon size="sm" />
          <span className="text-sm font-semibold tracking-wide text-(--text-primary)">BIGSHIP</span>
        </div>
        <ThemeToggle />
      </div>
      <div className="flex-1 flex items-center justify-center px-4 py-8">
        <div className="border border-(--border-primary) bg-(--bg-secondary) w-full max-w-md" style={{ padding: 'calc(2rem + env(safe-area-inset-bottom))' }}>
          <div className="flex items-center justify-center mb-6">
            <LogIn className="w-6 h-6 text-(--accent) mr-2" />
            <h1 className="text-xl font-bold text-(--text-primary)">Bigship Login</h1>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">Username</label>
              <input
                type="text"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                className="mt-1 block w-full bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) placeholder-(--text-tertiary) px-3 py-2.5 sm:py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors"
                required
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) placeholder-(--text-tertiary) px-3 py-2.5 sm:py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors"
                required
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">Access Key</label>
              <input
                type="text"
                value={accessKey}
                onChange={(e) => setAccessKey(e.target.value)}
                className="mt-1 block w-full bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) placeholder-(--text-tertiary) px-3 py-2.5 sm:py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors"
                required
              />
            </div>
            {error && <p className="text-red-500 text-xs">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-(--accent) text-(--bg-primary) py-2.5 sm:py-2 text-sm font-semibold uppercase tracking-widest hover:bg-(--accent-hover) disabled:opacity-50 transition-colors"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
