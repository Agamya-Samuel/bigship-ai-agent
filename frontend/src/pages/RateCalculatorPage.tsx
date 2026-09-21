import { useState } from 'react'
import { calculateRate } from '../lib/api'
import { AccentButton } from '../components/ui/AccentButton'

export default function RateCalculator() {
  const [segmentType, setSegmentType] = useState('domestic_b2b')
  const [sourcePincode, setSourcePincode] = useState('')
  const [destPincode, setDestPincode] = useState('')
  const [invoiceValue, setInvoiceValue] = useState('')
  const [paymentModeId, setPaymentModeId] = useState('')
  const [riskTypeId, setRiskTypeId] = useState('')
  const [boxes, setBoxes] = useState([{ box_length: 10, box_width: 10, box_height: 10, box_dead_weight: 1, no_of_box: 1 }])
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const data = await calculateRate({
        segment_type: segmentType,
        sourcePincode,
        destPincode,
        invoiceValue: parseFloat(invoiceValue),
        paymentModeId: parseInt(paymentModeId),
        riskTypeId: parseInt(riskTypeId),
        boxes,
      })
      setResult(data)
    } catch {
      setResult({ status: false, message: 'Failed to calculate rate' })
    } finally {
      setLoading(false)
    }
  }

  const updateBox = (idx: number, field: string, value: any) => {
    const b = [...boxes]
    b[idx] = { ...b[idx], [field]: value }
    setBoxes(b)
  }

  return (
    <div className="space-y-6" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
      <h2 className="text-xl sm:text-2xl font-bold text-(--text-primary)">Rate Calculator</h2>
      <form onSubmit={handleCalculate} className="border border-(--border-primary) bg-(--bg-secondary) p-6 space-y-4">
        <div>
          <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">Segment Type</label>
          <select
            value={segmentType}
            onChange={(e) => setSegmentType(e.target.value)}
            className="mt-1 block w-full bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) px-3 py-2.5 sm:py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors"
          >
            <option value="domestic_b2b">Domestic B2B</option>
            <option value="domestic_b2c">Domestic B2C</option>
          </select>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
          <div>
            <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">Source Pincode</label>
            <input
              type="text"
              value={sourcePincode}
              onChange={(e) => setSourcePincode(e.target.value)}
              className="mt-1 block w-full bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) placeholder-(--text-tertiary) px-3 py-2.5 sm:py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors"
              required
            />
          </div>
          <div>
            <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">Destination Pincode</label>
            <input
              type="text"
              value={destPincode}
              onChange={(e) => setDestPincode(e.target.value)}
              className="mt-1 block w-full bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) placeholder-(--text-tertiary) px-3 py-2.5 sm:py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors"
              required
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
          <div>
            <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">Invoice Value</label>
            <input
              type="number"
              value={invoiceValue}
              onChange={(e) => setInvoiceValue(e.target.value)}
              className="mt-1 block w-full bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) px-3 py-2.5 sm:py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors"
              required
            />
          </div>
          <div>
            <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">Payment Mode ID</label>
            <input
              type="number"
              value={paymentModeId}
              onChange={(e) => setPaymentModeId(e.target.value)}
              className="mt-1 block w-full bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) px-3 py-2.5 sm:py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">Risk Type ID</label>
          <input
            type="number"
            value={riskTypeId}
            onChange={(e) => setRiskTypeId(e.target.value)}
            className="mt-1 block w-full bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) px-3 py-2.5 sm:py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors"
            required
          />
        </div>

        <div>
          <label className="block text-xs uppercase tracking-widest text-(--text-tertiary) mb-1">Boxes</label>
          {boxes.map((box, idx) => (
            <div key={idx} className="grid grid-cols-5 gap-1 mt-2">
              <input type="number" placeholder="L" value={box.box_length} onChange={(e) => updateBox(idx, 'box_length', parseInt(e.target.value))} className="bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) px-2 py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent)/30" />
              <input type="number" placeholder="W" value={box.box_width} onChange={(e) => updateBox(idx, 'box_width', parseInt(e.target.value))} className="bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) px-2 py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent)/30" />
              <input type="number" placeholder="H" value={box.box_height} onChange={(e) => updateBox(idx, 'box_height', parseInt(e.target.value))} className="bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) px-2 py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent)/30" />
              <input type="number" placeholder="Wt" value={box.box_dead_weight} onChange={(e) => updateBox(idx, 'box_dead_weight', parseInt(e.target.value))} className="bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) px-2 py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent)/30" />
              <input type="number" placeholder="Qty" value={box.no_of_box} onChange={(e) => updateBox(idx, 'no_of_box', parseInt(e.target.value))} className="bg-(--bg-primary) border border-(--border-secondary) text-(--text-primary) px-2 py-2 text-base sm:text-sm focus:outline-none focus:border-(--accent)/30" />
            </div>
          ))}
        </div>

        <div className="flex justify-end pt-2 border-t border-(--border-primary)">
          <AccentButton size="md" type="submit" loading={loading}>
            {loading ? 'Calculating...' : 'Calculate Rate'}
          </AccentButton>
        </div>
      </form>

      {result && (
        <div className="border border-(--border-primary) bg-(--bg-secondary) p-6">
          <h3 className="text-xs uppercase tracking-widest text-(--text-primary) mb-3">Result</h3>
          <pre className="p-4 overflow-auto text-xs font-mono text-(--text-secondary)">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
