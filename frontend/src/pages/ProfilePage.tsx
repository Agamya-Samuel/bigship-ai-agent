import { useState, useEffect } from 'react'
import { getProfile } from '../lib/api'

export default function Profile() {
  const [profile, setProfile] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadProfile()
  }, [])

  const loadProfile = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getProfile()
      setProfile(data.data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load profile')
    } finally {
      setLoading(false)
    }
  }

  if (loading)
    return <p className="text-(--text-tertiary)" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>Loading profile...</p>
  if (error)
    return <p className="text-red-500" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>{error}</p>
  if (!profile)
    return <p className="text-(--text-tertiary)" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>No profile data.</p>

  return (
    <div className="space-y-6" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
      <h2 className="text-xl sm:text-2xl font-bold text-(--text-primary)">Profile</h2>
      <div className="border border-(--border-primary) bg-(--bg-secondary) p-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-(--text-tertiary)">Name</p>
            <p className="text-sm text-(--text-primary)">{profile.firstName} {profile.lastName}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-(--text-tertiary)">Email</p>
            <p className="text-sm text-(--text-primary)">{profile.EmailID}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-(--text-tertiary)">Mobile</p>
            <p className="text-sm text-(--text-primary)">{profile.mobileNumber}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-(--text-tertiary)">Country</p>
            <p className="text-sm text-(--text-primary)">{profile.countryname}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-(--text-tertiary)">Wallet Balance</p>
            <p className="text-sm font-mono text-(--accent)">{profile.userWallet?.kycCurrency || '₹'} {profile.userWallet?.Balance || 0}.00</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-(--text-tertiary)">KYC Currency</p>
            <p className="text-sm text-(--text-primary)">{profile.userWallet?.kycCurrency || '-'}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
