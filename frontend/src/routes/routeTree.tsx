import { createRoute } from '@tanstack/react-router'
import { rootRoute } from './rootRoute'
import LoginPage from '../pages/LoginPage'
import DashboardLayout from '../components/DashboardLayout'
import ChatPage from '../pages/ChatPage'
import OrdersPage from '../pages/OrdersPage'
import WarehousesPage from '../pages/WarehousesPage'
import RateCalculatorPage from '../pages/RateCalculatorPage'
import ProfilePage from '../pages/ProfilePage'
import LandingPage from '../pages/LandingPage'

export const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: LoginPage,
})

export const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: 'dashboard',
  component: DashboardLayout,
})

export const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: 'index',
  component: LandingPage,
})

export const chatRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/chat',
  component: ChatPage,
})

export const ordersRoute = createRoute({
  getParentRoute: () => dashboardRoute,
  path: 'orders',
  component: OrdersPage,
})

export const warehousesRoute = createRoute({
  getParentRoute: () => dashboardRoute,
  path: 'warehouses',
  component: WarehousesPage,
})

export const rateCalculatorRoute = createRoute({
  getParentRoute: () => dashboardRoute,
  path: 'rate-calculator',
  component: RateCalculatorPage,
})

export const profileRoute = createRoute({
  getParentRoute: () => dashboardRoute,
  path: 'profile',
  component: ProfilePage,
})
