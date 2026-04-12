import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import Button from '../components/ui/Button'

const features = [
  {
    title: 'Task Management',
    description: 'Create, update, and track volunteer tasks with a clean and fast interface.',
  },
  {
    title: 'AI Categorization',
    description: 'Let AI automatically categorize and organize your tasks by type and urgency.',
  },
  {
    title: 'Notes to Tasks',
    description: 'Paste messy notes and AI extracts structured, actionable tasks instantly.',
  },
]

export default function Landing() {
  const { token, isLoading } = useAuth()

  if (!isLoading && token) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      {/* Nav */}
      <nav className="border-b border-slate-900 px-4 sm:px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <span className="text-slate-100 font-semibold text-lg">Volunteer</span>
          <div className="flex items-center gap-3">
            <Link to="/login">
              <Button variant="ghost" size="sm">
                Sign in
              </Button>
            </Link>
            <Link to="/register">
              <Button size="sm">Get started</Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 text-center py-16">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-4xl sm:text-5xl font-bold text-slate-100 leading-tight">
            Organize your volunteer work.{' '}
            <span className="text-brand-500">Powered by AI.</span>
          </h1>
          <p className="mt-4 text-lg text-slate-400 max-w-md mx-auto">
            Track tasks, categorize work, and extract to-dos from your notes — all in one place.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
            <Link to="/register">
              <Button size="lg">Get started free</Button>
            </Link>
            <Link to="/login">
              <Button variant="secondary" size="lg">
                Sign in
              </Button>
            </Link>
          </div>
        </div>

        {/* Features */}
        <div className="mt-24 grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-4xl mx-auto w-full">
          {features.map((f) => (
            <div
              key={f.title}
              className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-left"
            >
              <h3 className="font-semibold text-slate-100 mb-2">{f.title}</h3>
              <p className="text-sm text-slate-400">{f.description}</p>
            </div>
          ))}
        </div>
      </main>

      <footer className="py-8 text-center text-xs text-slate-600 border-t border-slate-900">
        Volunteer Task Manager
      </footer>
    </div>
  )
}
