import { useState, useEffect } from 'react'
import { getOrders, cancelOrder, trackOrder } from '../lib/api'
import { RotateCw, X } from 'lucide-react'
import { AccentButton } from '../components/ui/AccentButton'
import { IconButton } from '../components/ui/IconButton'

export default function Orders() {
  const [orders, setOrders] = useState<any[]>([])
  const [selected, setSelected] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadOrders()
  }, [])

  const loadOrders = async () => {
    setLoading(true)
    try {
      const data = await getOrders({ page: 1, per_page: 20 })
      setOrders(data.data?.orders || data.data || [])
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = async (orderId: string) => {
    if (!confirm('Cancel this order?')) return
    await cancelOrder(orderId)
    loadOrders()
    setSelected(null)
  }

  const getStatusColor = (status: string) => {
    const s = (status || '').toLowerCase()
    if (s.includes('deliver') || s.includes('complete')) return 'text-green-500'
    if (s.includes('cancel') || s.includes('fail')) return 'text-red-500'
    return 'text-(--accent)'
  }

  return (
    <div className="space-y-4" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
      {/* Header — stacked on mobile */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
        <h2 className="text-xl sm:text-2xl font-bold text-(--text-primary)">Orders</h2>
        <div className="flex gap-2 sm:gap-3">
          <IconButton onClick={loadOrders} ariaLabel="Refresh orders" variant="secondary">
            <RotateCw className="w-4 h-4" />
          </IconButton>
          <AccentButton size="sm" onClick={() => {}} className="flex-1 sm:flex-none">
            Refresh
          </AccentButton>
        </div>
      </div>

      {loading && <p className="text-(--text-tertiary)">Loading orders...</p>}
      {!loading && orders.length === 0 && <p className="text-(--text-tertiary)">No orders found.</p>}

      {/* Table — horizontal scroll on mobile */}
      <div className="border border-(--border-primary) bg-(--bg-secondary) overflow-x-auto">
        <table className="min-w-[600px] sm:min-w-full divide-y divide-(--border-primary)">
          <thead>
            <tr>
              <th className="px-4 py-2.5 sm:px-6 text-left text-[10px] sm:text-xs font-medium text-(--text-tertiary) uppercase">Order ID</th>
              <th className="px-4 py-2.5 sm:px-6 text-left text-[10px] sm:text-xs font-medium text-(--text-tertiary) uppercase">Date</th>
              <th className="px-4 py-2.5 sm:px-6 text-left text-[10px] sm:text-xs font-medium text-(--text-tertiary) uppercase">Status</th>
              <th className="px-4 py-2.5 sm:px-6 text-left text-[10px] sm:text-xs font-medium text-(--text-secondary) uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-(--border-primary)">
            {orders.map((order: any) => (
              <tr key={order.MasterCustomOrderId || order.CustomGlobalOrderId}>
                <td className="px-4 py-3 sm:px-6 whitespace-nowrap text-sm font-mono text-(--text-secondary)">
                  {order.MasterCustomOrderId || order.CustomGlobalOrderId}
                </td>
                <td className="px-4 py-3 sm:px-6 whitespace-nowrap text-sm text-(--text-secondary)">
                  {order.MasterOrderDate || '-'}
                </td>
                <td className="px-4 py-3 sm:px-6 whitespace-nowrap text-sm">
                  <span className={`font-medium ${getStatusColor(order.Status)}`}>
                    {order.Status || '-'}
                  </span>
                </td>
                <td className="px-4 py-3 sm:px-6 whitespace-nowrap flex gap-3">
                  <button
                    onClick={() => setSelected(order)}
                    className="text-(--accent) hover:text-(--accent-hover) text-xs uppercase tracking-widest transition-colors"
                  >
                    View
                  </button>
                  <button
                    onClick={() => trackOrder(order.CustomGlobalOrderId || order.MasterCustomOrderId)}
                    className="text-green-500 hover:text-green-400 text-xs uppercase tracking-widest transition-colors"
                  >
                    Track
                  </button>
                  <button
                    onClick={() => handleCancel(order.CustomGlobalOrderId || order.MasterCustomOrderId)}
                    className="text-red-500 hover:text-red-400 text-xs uppercase tracking-widest transition-colors"
                  >
                    Cancel
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal — border-led instead of shadow */}
      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="border border-(--border-primary) bg-(--bg-secondary) w-full max-w-2xl max-h-[80vh] overflow-auto">
            <div className="flex justify-between items-center p-4 border-b border-(--border-primary)">
              <h3 className="text-xs uppercase tracking-widest text-(--text-primary)">Order Details</h3>
              <IconButton
                onClick={() => setSelected(null)}
                ariaLabel="Close"
                variant="secondary"
              >
                <X className="w-4 h-4" />
              </IconButton>
            </div>
            <pre className="p-4 overflow-auto text-xs font-mono text-(--text-secondary)">
              {JSON.stringify(selected, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
