import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError, errorMessage, makeOperation } from './api'
import type { Operation } from './api'
import type { Session } from './types'

export function useResource<T>(
  load: (() => Promise<T>) | null,
  poll = 0,
  reconcile?: (previous: T | null, next: T) => T,
) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(Boolean(load))
  const refreshRef = useRef<() => Promise<void>>(async () => {})
  useEffect(() => {
    let active = true,
      inFlight = false
    let timer: ReturnType<typeof setTimeout> | undefined
    setData(null)
    setError('')
    setLoading(Boolean(load))
    async function run() {
      if (!load || !active || inFlight) return
      inFlight = true
      try {
        const result = await load()
        if (active) {
          setData((previous) => (reconcile ? reconcile(previous, result) : result))
          setError('')
        }
      } catch (failure) {
        if (active) setError(errorMessage(failure))
      } finally {
        inFlight = false
        if (active) setLoading(false)
      }
    }
    refreshRef.current = run
    async function tick() {
      if (document.visibilityState !== 'hidden') await run()
      if (active && poll) timer = setTimeout(tick, poll)
    }
    void run().finally(() => {
      if (active && poll) timer = setTimeout(tick, poll)
    })
    const visible = () => {
      if (document.visibilityState === 'visible') void run()
    }
    document.addEventListener('visibilitychange', visible)
    return () => {
      active = false
      clearTimeout(timer)
      document.removeEventListener('visibilitychange', visible)
    }
  }, [load, poll, reconcile])
  return { data, setData, error, loading, refresh: useCallback(() => refreshRef.current(), []) }
}

export function newestSession(previous: Session | null, next: Session) {
  return previous?.id === next.id && previous.version > next.version ? previous : next
}

export function useDraft(key: string) {
  const [draft, setDraft] = useState(() => sessionStorage.getItem(`rampup.draft.${key}`) || '')
  useEffect(() => {
    if (draft) sessionStorage.setItem(`rampup.draft.${key}`, draft)
    else sessionStorage.removeItem(`rampup.draft.${key}`)
  }, [key, draft])
  return [draft, setDraft] as const
}

function readOperation(key: string): Operation | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(key) || 'null')
    return value &&
      typeof value.path === 'string' &&
      /^\/(sessions|escalations)\//.test(value.path) &&
      typeof value.key === 'string' &&
      /^[\da-f-]{36}$/i.test(value.key) &&
      typeof value.body === 'object' &&
      value.body !== null &&
      typeof value.label === 'string'
      ? value
      : null
  } catch {
    return null
  }
}

export function useOperation(
  scope: string,
  changed: (session: Session) => void,
  refresh: () => Promise<void>,
) {
  const storageKey = `rampup.operation.${scope}`
  const [pending, setPending] = useState<Operation | null>(() => readOperation(storageKey))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const lock = useRef(false)
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  async function execute(operation: Operation): Promise<'done' | 'saved' | 'failed'> {
    if (lock.current) return 'failed'
    lock.current = true
    setBusy(true)
    setError('')
    setSaved(false)
    setPending(operation)
    sessionStorage.setItem(storageKey, JSON.stringify(operation))
    try {
      const result = await api.post<Session>(operation.path, operation.body, operation.key)
      sessionStorage.removeItem(storageKey)
      if (mounted.current) {
        setPending(null)
        changed(result)
      }
      await refresh() // A replay may be older than the live session.
      return 'done'
    } catch (failure) {
      const isSaved = failure instanceof ApiError && failure.code === 'COACH_FAILED'
      const canRetry =
        !(failure instanceof ApiError) || failure.retryable || failure.code === 'RUN_IN_PROGRESS'
      if (!canRetry) {
        sessionStorage.removeItem(storageKey)
        if (mounted.current) setPending(null)
      }
      if (mounted.current) {
        setError(errorMessage(failure))
        setSaved(isSaved)
      }
      await refresh()
      return isSaved ? 'saved' : 'failed'
    } finally {
      lock.current = false
      if (mounted.current) setBusy(false)
    }
  }
  return {
    pending,
    busy,
    error,
    saved,
    run: (path: string, body: Record<string, unknown>, label: string) =>
      execute(makeOperation(path, body, label)),
    retry: () => (pending ? execute(pending) : Promise.resolve('failed' as const)),
    clearError: () => setError(''),
  }
}
