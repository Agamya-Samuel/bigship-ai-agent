import { createRouter } from '@tanstack/react-router'
import { rootRoute } from './rootRoute'
import { loginRoute } from './routeTree'
import { dashboardRoute } from './routeTree'
import { indexRoute } from './routeTree'
import { chatRoute } from './routeTree'

const routeTree = rootRoute.addChildren([
  loginRoute,
  indexRoute,
  chatRoute,
  dashboardRoute,
])

export const router = createRouter({ 
  routeTree,
  context: {
    queryClient: {} as any,
  },
})
