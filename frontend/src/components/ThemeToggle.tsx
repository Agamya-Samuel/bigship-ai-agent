import { Moon, SunDim } from 'lucide-react'
import { useTheme } from '../hooks/useTheme'
import { IconButton } from './ui/IconButton'

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()

  return (
    <IconButton
      onClick={toggleTheme}
      ariaLabel={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {theme === 'dark' ? (
        <SunDim className="w-4 h-4" />
      ) : (
        <Moon className="w-4 h-4" />
      )}
    </IconButton>
  )
}
