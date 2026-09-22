import type { LucideIcon } from 'lucide-react'
import { Package, Truck, Warehouse, BarChart3 } from 'lucide-react'

export type Suggestion = {
  icon: LucideIcon
  title: string
  prompt: string
}

export const suggestions: Suggestion[] = [
  {
    icon: BarChart3,
    title: 'Calculate rates',
    prompt: 'Calculate shipping rates for b2c order (no risk) for 15kg package, 20 x 10 x 20 cm,  from 400012 to 226018. Invoice is 1600. Customer will pay at delivery.',
  },
  {
    icon: Package,
    title: 'Create a shipment',
    prompt: 'Create a new b2c order for box 10 x 15 x 20 cm, from 400012 to 226018, 500g, give zone info if available.',
  },
  {
    icon: Truck,
    title: 'Track an order',
    prompt: 'Track shipment and tell me when it will arrive',
  },
  {
    icon: Warehouse,
    title: 'List my warehouses',
    prompt: 'Show me all my warehouses with their pickup addresses',
  }
]
