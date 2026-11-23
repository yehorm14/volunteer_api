import type { AxiosError } from 'axios'

/** A short, user-facing reason for a failed request. */
export function describeError(err: unknown): string {
  const axiosErr = err as AxiosError<{ detail?: unknown }>
  const detail = axiosErr?.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail) && detail.length > 0) {
    // FastAPI validation errors: [{ loc, msg }]
    const first = detail[0] as { msg?: string }
    if (first?.msg) return first.msg
  }
  if (axiosErr?.response) return `The server returned an error (${axiosErr.response.status}).`
  return 'The server could not be reached.'
}
