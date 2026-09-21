import { RouterProvider } from '@tanstack/react-router'
import { useEffect } from 'react'
import { router } from './routes/routeTree.gen'

export default function App() {
  useEffect(() => {
    const theme = localStorage.getItem('theme') as 'dark' | 'light' | null
    document.documentElement.setAttribute('data-theme', theme ?? 'dark')
  }, [])

  return <RouterProvider router={router} />
}
