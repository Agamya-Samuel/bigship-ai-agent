import { QueryClient } from '@tanstack/react-query'
import { createRootRouteWithContext, Outlet, useNavigate } from '@tanstack/react-router'
import { useEffect } from 'react'

export interface RouterContext {
  queryClient: QueryClient
}

function RootLayout() {
  const navigate = useNavigate()
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    const isLogin = window.location.pathname === '/login'
    const isIndex = window.location.pathname === '/'
    if (!token && !isLogin && !isIndex) {
      navigate({ to: '/login', replace: true })
    }
  }, [navigate])
  return <Outlet />
}

export const rootRoute = createRootRouteWithContext<RouterContext>()({
  component: RootLayout,
})
