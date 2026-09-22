import { Outlet, useNavigate } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { LogOut, Menu } from 'lucide-react'
import { logout } from '../lib/api'
import { ThemeToggle } from './ThemeToggle'
import { BrandIcon } from './ui/BrandIcon'

export default function DashboardLayout() {
  const navigate = useNavigate()
  const userName = localStorage.getItem('user_name') || 'User'
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSidebarOpen(false)
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [])

  const handleLogout = async () => {
    try {
      await logout()
    } finally {
      localStorage.clear()
      navigate({ to: '/login' })
    }
  }

  const SidebarNav = () => (
    <>
      <div className="p-4 border-b border-(--border-primary)">
        <div className="flex items-center gap-2.5">
          <BrandIcon size="sm" />
          <span className="text-sm font-semibold tracking-wide text-(--text-primary)">BIGSHIP</span>
        </div>
      </div>
      <div className="p-3 border-t border-(--border-primary)">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2.5 w-full text-xs uppercase tracking-widest text-(--text-tertiary) hover:text-red-500 hover:bg-(--bg-tertiary) transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>Logout</span>
        </button>
      </div>
    </>
  )

  return (
    <div className="flex h-screen bg-(--bg-primary) text-(--text-secondary) font-sans antialiased overflow-hidden">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      {/* Mobile overlay sidebar */}
      <aside
        className={
          'fixed inset-y-0 left-0 z-50 w-64 bg-(--bg-secondary) border-r border-(--border-primary) md:static md:translate-x-0 transition-transform duration-200 ease-out' +
          (sidebarOpen ? ' translate-x-0' : ' -translate-x-full md:translate-x-0')
        }
        style={{ paddingTop: 'env(safe-area-inset-top)', paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <SidebarNav />
      </aside>
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="h-12 border-b border-(--border-primary) bg-(--bg-secondary) flex items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="md:hidden min-w-10 min-h-10 p-2 border border-(--border-secondary) bg-(--bg-primary) text-(--text-secondary) hover:text-(--accent) hover:border-(--accent)/30 transition-colors"
              aria-label="Open navigation"
            >
              <Menu className="w-4 h-4" />
            </button>
            <span className="text-xs uppercase tracking-widest text-(--text-tertiary)">
              {userName}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
          </div>
        </div>
        <main className="flex-1 overflow-auto p-4 sm:p-6" style={{ paddingBottom: 'calc(1.5rem + env(safe-area-inset-bottom))' }}>
          <div className="max-w-4xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
