import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { AxiosError } from 'axios'
import type { AICategorizeResponse, Task, ApiError } from '../../types'
import * as api from '../../services/api'
import Button from '../ui/Button'
import Textarea from '../ui/Textarea'

interface AIPanelProps {
  taskId: number
  taskTitle: string
}

export default function AIPanel({ taskId, taskTitle }: AIPanelProps) {
  const [catResult, setCatResult] = useState<AICategorizeResponse | null>(null)
  const [catLoading, setCatLoading] = useState(false)
  const [catError, setCatError] = useState('')

  const [notes, setNotes] = useState('')
  const [extractResult, setExtractResult] = useState<Task | null>(null)
  const [extractLoading, setExtractLoading] = useState(false)
  const [extractError, setExtractError] = useState('')

  async function handleCategorize() {
    setCatLoading(true)
    setCatError('')
    setCatResult(null)
    try {
      const result = await api.categorizeTask(taskId)
      setCatResult(result)
    } catch (err) {
      const e = err as AxiosError<ApiError>
      setCatError(e.response?.data?.detail ?? 'Failed to categorize task')
    } finally {
      setCatLoading(false)
    }
  }

  async function handleExtract() {
    if (!notes.trim()) return
    setExtractLoading(true)
    setExtractError('')
    setExtractResult(null)
    try {
      const task = await api.extractTaskFromNotes(notes)
      setExtractResult(task)
    } catch (err) {
      const e = err as AxiosError<ApiError>
      setExtractError(e.response?.data?.detail ?? 'Failed to extract task from notes')
    } finally {
      setExtractLoading(false)
    }
  }

  return (
    <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 space-y-6">
      <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">AI Tools</h2>

      {/* Categorize */}
      <div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Categorize task</h3>
            <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
              AI will categorize &ldquo;{taskTitle}&rdquo; and explain it in one line.
            </p>
          </div>
          <Button size="sm" variant="secondary" onClick={handleCategorize} isLoading={catLoading}>
            Categorize
          </Button>
        </div>
        {catResult && (
          <div className="mt-3 p-3 bg-brand-600/10 border border-brand-600/20 rounded-lg">
            <p className="text-sm text-slate-200">{catResult.ai_suggestion}</p>
          </div>
        )}
        {catError && <p className="mt-2 text-xs text-red-400">{catError}</p>}
      </div>

      <div className="border-t border-slate-800" />

      {/* Extract from notes */}
      <div>
        <h3 className="text-sm font-semibold text-slate-100 mb-1">Extract task from notes</h3>
        <p className="text-xs text-slate-400 mb-3 leading-relaxed">
          Paste messy notes and AI will extract a structured task and save it.
        </p>
        <Textarea
          placeholder="e.g. 'need to call the shelter about food donations next tuesday, also check if the van is available'"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
        />
        <Button
          size="sm"
          variant="secondary"
          onClick={handleExtract}
          isLoading={extractLoading}
          disabled={!notes.trim()}
          className="mt-3"
        >
          Extract task
        </Button>
        {extractResult && (
          <div className="mt-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
            <p className="text-xs text-emerald-400 font-medium mb-1">Task created</p>
            <p className="text-sm font-semibold text-slate-100">{extractResult.title}</p>
            {extractResult.description && (
              <p className="text-sm text-slate-300 mt-1">{extractResult.description}</p>
            )}
            <Link
              to={`/tasks/${extractResult.id}`}
              className="text-xs text-brand-500 hover:text-brand-400 mt-2 inline-block"
            >
              View task →
            </Link>
          </div>
        )}
        {extractError && <p className="mt-2 text-xs text-red-400">{extractError}</p>}
      </div>
    </div>
  )
}
