import { RouterProvider } from '@tanstack/react-router'
import { useTheme } from './hooks/useTheme'
import { router } from './routes/routeTree.gen'

export default function App() {
  useTheme()

  return <RouterProvider router={router} />
}
