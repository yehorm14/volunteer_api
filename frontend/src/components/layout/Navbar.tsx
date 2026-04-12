import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import Button from '../ui/Button'

export default function Navbar() {
  const { user, logout } = useAuth()

  return (
    <header className="bg-slate-900 border-b border-slate-800">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        <Link
          to="/dashboard"
          className="text-slate-100 font-semibold text-base hover:text-white transition-colors"
        >
          Volunteer
        </Link>
        <div className="flex items-center gap-4">
          {user && (
            <span className="text-slate-400 text-sm hidden sm:block">{user.email}</span>
          )}
          <Button variant="ghost" size="sm" onClick={logout}>
            Sign out
          </Button>
        </div>
      </div>
    </header>
  )
}
