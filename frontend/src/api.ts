export class ApiError extends Error {
  status: number
  code: string
  retryable: boolean
  constructor(message: string, status = 0, code = 'NETWORK_ERROR', retryable = true) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.retryable = retryable
  }
}

interface ClientOptions {
  token: () => string | null
  expired: () => void
  fetcher?: typeof fetch
  timeout?: number
}

export function createClient({ token, expired, fetcher = fetch, timeout = 65000 }: ClientOptions) {
  async function request<T>(path: string, body?: unknown, key?: string): Promise<T> {
    if (!path.startsWith('/') || path.startsWith('//') || path.includes('://'))
      throw new Error('Invalid API path')
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeout)
    const headers: Record<string, string> = { Accept: 'application/json' }
    const accessToken = token()
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    if (key) headers['Idempotency-Key'] = key
    try {
      const response = await fetcher(`/api/v1${path}`, {
        method: body === undefined ? 'GET' : 'POST',
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
        cache: 'no-store',
        redirect: 'error',
      })
      const data = await response.json().catch(() => null)
      if (!response.ok) {
        if (response.status === 401 && path !== '/auth/login') expired()
        throw new ApiError(
          data?.error?.message ||
            (response.status === 503
              ? 'The service is temporarily unavailable. Please try again.'
              : 'We couldn’t complete that request.'),
          response.status,
          data?.error?.code || 'REQUEST_FAILED',
          data?.error?.retryable ?? response.status >= 500,
        )
      }
      if (data === null)
        throw new ApiError('The server returned an unreadable response. Please try again.')
      return data as T
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError(
        controller.signal.aborted
          ? 'The request took too long. Retry the original request to avoid sending it twice.'
          : 'We couldn’t confirm the request. Check your connection, then retry the original request.',
      )
    } finally {
      clearTimeout(timer)
    }
  }
  return {
    get: <T>(path: string) => request<T>(path),
    post: <T>(path: string, body: unknown, key?: string) => request<T>(path, body, key),
  }
}

export const api = createClient({
  token: () => sessionStorage.getItem('rampup.token'),
  expired: () => window.dispatchEvent(new Event('rampup:expired')),
})

export interface Operation {
  path: string
  body: Record<string, unknown>
  key: string
  label: string
}
export function makeOperation(
  path: string,
  body: Record<string, unknown>,
  label: string,
): Operation {
  return { path, body, label, key: crypto.randomUUID() }
}
export function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.'
}
export function safeSourceUrl(url: string): string | undefined {
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'https:' &&
      parsed.hostname === 'github.com' &&
      !parsed.username &&
      !parsed.password
      ? parsed.href
      : undefined
  } catch {
    return undefined
  }
}
