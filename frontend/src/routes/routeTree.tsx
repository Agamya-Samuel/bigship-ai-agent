import { createRoute } from '@tanstack/react-router'
import { rootRoute } from './rootRoute'
import LoginPage from '../pages/LoginPage'
import ChatPage from '../pages/ChatPage'
import LandingPage from '../pages/LandingPage'

export const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: LandingPage,
})

export const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: LoginPage,
})

export const chatRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/chat',
  component: ChatPage,
})
