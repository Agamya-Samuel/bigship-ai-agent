import { createRouter } from '@tanstack/react-router'
import { rootRoute } from './rootRoute'
import { loginRoute } from './routeTree'
import { dashboardRoute } from './routeTree'
import { indexRoute } from './routeTree'
import { chatRoute } from './routeTree'
import { ordersRoute } from './routeTree'
import { warehousesRoute } from './routeTree'
import { rateCalculatorRoute } from './routeTree'
import { profileRoute } from './routeTree'

const routeTree = rootRoute.addChildren([
  loginRoute,
  indexRoute,
  chatRoute,
  dashboardRoute.addChildren([
    ordersRoute,
    warehousesRoute,
    rateCalculatorRoute,
    profileRoute,
  ]),
])

export const router = createRouter({ 
  routeTree,
  context: {
    queryClient: {} as any,
  },
})
