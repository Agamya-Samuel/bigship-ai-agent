import { useState, useEffect } from 'react'
import { getWarehouses, saveWarehouse, updateWarehouse } from '../lib/api'
import { Plus, X } from 'lucide-react'
import { AccentButton } from '../components/ui/AccentButton'
import { IconButton } from '../components/ui/IconButton'

export default function Warehouses() {
  const [warehouses, setWarehouses] = useState<any[]>([])
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [form, setForm] = useState({
    segment_type: 'local',
    warehouseContactPerson: '',
    warehouseAddressPhone: '',
    warehouseState: '',
    warehouseCity: '',
    warehousePinCode: '',
    warehouseAddressLine1: '',
    warehouseAddressLandMark: '',
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadWarehouses()
  }, [])

  const loadWarehouses = async () => {
    setLoading(true)
    try {
      const data = await getWarehouses({ page: 1, per_page: 20, segment_type: 'local' })
      setWarehouses(data.data?.warehouse || [])
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editing) {
        await updateWarehouse(editing.warehouseId, form)
      } else {
        await saveWarehouse(form)
      }
      setShowForm(false)
      setEditing(null)
      setForm({
        segment_type: 'local',
        warehouseContactPerson: '',
        warehouseAddressPhone: '',
        warehouseState: '',
        warehouseCity: '',
        warehousePinCode: '',
        warehouseAddressLine1: '',
        warehouseAddressLandMark: '',
      })
      loadWarehouses()
    } catch {
      alert('Failed to save warehouse')
    }
  }

  const handleEdit = (wh: any) => {
    setEditing(wh)
    setForm({
      segment_type: wh.segment_type || 'local',
      warehouseContactPerson: wh.warehouseContactPerson || '',
      warehouseAddressPhone: wh.warehouseAddressPhone || '',
      warehouseState: wh.warehouseState || '',
      warehouseCity: wh.warehouseCity || '',
      warehousePinCode: wh.warehousePinCode || '',
      warehouseAddressLine1: wh.warehouseAddressLine1 || '',
      warehouseAddressLandMark: wh.warehouseAddressLandMark || '',
    })
    setShowForm(true)
  }

  return (
    <div className="space-y-4" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
        <h2 className="text-xl sm:text-2xl font-bold text-(--text-primary)">Warehouses</h2>
        <AccentButton size="sm" onClick={() => { setShowForm(true); setEditing(null) }} className="w-full sm:w-auto">
          <Plus className="w-4 h-4" />
          Add Warehouse
        </AccentButton>
      </div>

      {loading && <p className="text-(--text-tertiary)">Loading warehouses...</p>}

      <div className="border border-(--border-primary) bg-(--bg-secondary) overflow-x-auto">
        <table className="min-w-[500px] sm:min-w-full divide-y divide-(--border-primary)">
          <thead>
            <tr>
              <th className="px-4 py-2.5 sm:px-6 text-left text-[10px] sm:text-xs font-medium text-(--text-tertiary) uppercase">Name</th>
              <th className="px-4 py-2.5 sm:px-6 text-left text-[10px] sm:text-xs font-medium text-(--text-tertiary) uppercase">City</th>
              <th className="px-4 py-2.5 sm:px-6 text-left text-[10px] sm:text-xs font-medium text-(--text-tertiary) uppercase">State</th>
              <th className="px-4 py-2.5 sm:px-6 text-left text-[10px] sm:text-xs font-medium text-(--text-tertiary) uppercase">Phone</th>
              <th className="px-4 py-2.5 sm:px-6 text-left text-[10px] sm:text-xs font-medium text-(--text-secondary) uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-(--border-primary)">
            {warehouses.map((wh: any) => (
              <tr key={wh.warehouseId}>
                <td className="px-4 py-3 sm:px-6 whitespace-nowrap text-sm font-mono text-(--text-secondary)">{wh.warehouseName || '-'}</td>
                <td className="px-4 py-3 sm:px-6 whitespace-nowrap text-sm text-(--text-secondary)">{wh.warehouseCity}</td>
                <td className="px-4 py-3 sm:px-6 whitespace-nowrap text-sm text-(--text-secondary)">{wh.warehouseState}</td>
                <td className="px-4 py-3 sm:px-6 whitespace-nowrap text-sm text-(--text-secondary)">{wh.warehouseAddressPhone}</td>
                <td className="px-4 py-3 sm:px-6 whitespace-nowrap">
                  <button
                    onClick={() => handleEdit(wh)}
                    className="text-(--accent) hover:text-(--accent-hover) text-xs uppercase tracking-widest transition-colors"
                  >
                    Edit
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Form modal — border-led */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="border border-(--border-primary) bg-(--bg-secondary) w-full max-w-2xl max-h-[80vh] overflow-auto">
            <div className="flex justify-between items-center p-4 border-b border-(--border-primary)">
              <h3 className="text-xs uppercase tracking-widest text-(--text-primary)">
                {editing ? 'Edit Warehouse' : 'Add Warehouse'}
              </h3>
              <IconButton
                onClick={() => { setShowForm(false); setEditing(null) }}
                ariaLabel="Close"
                variant="secondary"
              >
                <X className="w-4 h-4" />
              </IconButton>
            </div>
            <form onSubmit={handleSubmit} className="p-4 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                <div>
                  <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">Contact Person</label>
                  <input
                    type="text"
                    value={form.warehouseContactPerson}
                    onChange={(e) => setForm({ ...form, warehouseContactPerson: e.target.value })}
                    className="mt-1 block w-full bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) placeholder-(--text-tertiary) px-3 py-2.5 sm:py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">Phone</label>
                  <input
                    type="text"
                    value={form.warehouseAddressPhone}
                    onChange={(e) => setForm({ ...form, warehouseAddressPhone: e.target.value })}
                    className="mt-1 block w-full bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) placeholder-(--text-tertiary) px-3 py-2.5 sm:py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">State</label>
                  <input
                    type="text"
                    value={form.warehouseState}
                    onChange={(e) => setForm({ ...form, warehouseState: e.target.value })}
                    className="mt-1 block w-full bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) placeholder-(--text-tertiary) px-3 py-2.5 sm:py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">City</label>
                  <input
                    type="text"
                    value={form.warehouseCity}
                    onChange={(e) => setForm({ ...form, warehouseCity: e.target.value })}
                    className="mt-1 block w-full bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) placeholder-(--text-tertiary) px-3 py-2.5 sm:py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">Pincode</label>
                  <input
                    type="text"
                    value={form.warehousePinCode}
                    onChange={(e) => setForm({ ...form, warehousePinCode: e.target.value })}
                    className="mt-1 block w-full bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) placeholder-(--text-tertiary) px-3 py-2.5 sm:py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">Address Line 1</label>
                  <input
                    type="text"
                    value={form.warehouseAddressLine1}
                    onChange={(e) => setForm({ ...form, warehouseAddressLine1: e.target.value })}
                    className="mt-1 block w-full bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) placeholder-(--text-tertiary) px-3 py-2.5 sm:py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors"
                    required
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">Landmark</label>
                  <input
                    type="text"
                    value={form.warehouseAddressLandMark}
                    onChange={(e) => setForm({ ...form, warehouseAddressLandMark: e.target.value })}
                    className="mt-1 block w-full bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) placeholder-(--text-tertiary) px-3 py-2.5 sm:py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors"
                    required
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2 border-t border-(--border-primary)">
                <IconButton
                  onClick={() => { setShowForm(false); setEditing(null) }}
                  ariaLabel="Cancel"
                  variant="secondary"
                >
                  Cancel
                </IconButton>
                <AccentButton size="sm" type="submit">
                  Save
                </AccentButton>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
