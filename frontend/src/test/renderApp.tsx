import { render } from '@testing-library/react'
import App from '../App'
import { AuthProvider } from '../context/AuthContext'
import { fakeToken } from './server'

/** Render the whole app at `path`, optionally already signed in. */
export function renderApp(path: string, { signedIn = true }: { signedIn?: boolean } = {}) {
  if (signedIn) localStorage.setItem('access_token', fakeToken())
  window.history.pushState({}, '', path)
  return render(
    <AuthProvider>
      <App />
    </AuthProvider>
  )
}
