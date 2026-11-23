import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { DEMO_ENABLED } from '../../services/api'
import { useAuth } from '../../hooks/useAuth'
import Button from '../ui/Button'

/** "Try the sample workspace": read-only, no account, no AI. Renders nothing unless the build enables it. */
export default function DemoButton({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const { loginAsDemo } = useAuth()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  if (!DEMO_ENABLED) return null

  async function handleClick() {
    setBusy(true)
    setError('')
    try {
      await loginAsDemo()
      navigate('/dashboard', { replace: true })
    } catch {
      setError('The sample workspace is not available right now.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <Button variant="secondary" size={size} isLoading={busy} onClick={handleClick}>
        Try the sample workspace
      </Button>
      <p className="text-xs text-slate-500">Read-only, no account needed, AI tools off.</p>
      {error && (
        <p role="alert" className="text-xs text-red-400">
          {error}
        </p>
      )}
    </div>
  )
}
