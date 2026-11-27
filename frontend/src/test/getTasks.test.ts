import { describe, expect, it } from 'vitest'
import { getTasks, TASK_PAGE_SIZE } from '../services/api'
import { seed } from './server'

describe('getTasks', () => {
  it('fetches every page so all tasks are returned', async () => {
    const total = TASK_PAGE_SIZE * 2 + 5
    seed(Array.from({ length: total }, (_, i) => ({ title: `Task ${i}` })))
    const tasks = await getTasks()
    expect(tasks).toHaveLength(total)
    expect(new Set(tasks.map((t) => t.id)).size).toBe(total)
  })
})
