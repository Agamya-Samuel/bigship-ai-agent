import { createRoute } from '@tanstack/react-router'
import { rootRoute } from './rootRoute'
import LoginPage from '../pages/LoginPage'
import DashboardLayout from '../components/DashboardLayout'
import ChatPage from '../pages/ChatPage'
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
