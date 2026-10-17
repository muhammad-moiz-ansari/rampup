import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ApiError, createClient, makeOperation, safeSourceUrl } from '../src/api.ts'

test('authenticated mutations retain the exact key and body on a retry', async () => {
  const calls = []
  const operation = makeOperation(
    '/sessions/one/messages',
    { content: 'Where should validation live?' },
    'question',
  )
  const client = createClient({
    token: () => 'test-token',
    expired: () => {},
    fetcher: async (url, options) => {
      calls.push({ url, ...options })
      return calls.length === 1
        ? Response.json(
            { error: { code: 'COACH_FAILED', message: 'Saved input', retryable: true } },
            { status: 503 },
          )
        : Response.json({ state: 'ACTIVE' })
    },
  })
  await assert.rejects(
    client.post(operation.path, operation.body, operation.key),
    (error) => error instanceof ApiError && error.code === 'COACH_FAILED' && error.retryable,
  )
  assert.deepEqual(await client.post(operation.path, operation.body, operation.key), {
    state: 'ACTIVE',
  })
  assert.equal(calls[0].headers['Idempotency-Key'], calls[1].headers['Idempotency-Key'])
  assert.equal(calls[0].body, calls[1].body)
  assert.equal(calls[0].headers.Authorization, 'Bearer test-token')
  assert.equal(calls[0].redirect, 'error')
  assert.equal(calls[0].url, '/api/v1/sessions/one/messages')
})

test('each new operation receives a new key', () => {
  const first = makeOperation('/sessions/one/messages', { content: 'Same text' }, 'question')
  const second = makeOperation(first.path, first.body, first.label)
  assert.notEqual(first.key, second.key)
})

test('expired sessions clear authentication; incorrect login does not trigger expiry', async () => {
  let expirations = 0
  const client = createClient({
    token: () => null,
    expired: () => expirations++,
    fetcher: async () =>
      Response.json(
        { error: { code: 'INVALID_CREDENTIALS', message: 'Incorrect credentials' } },
        { status: 401 },
      ),
  })
  await assert.rejects(client.post('/auth/login', {}), (error) => error.status === 401)
  assert.equal(expirations, 0)
  await assert.rejects(client.get('/auth/me'), (error) => error.status === 401)
  assert.equal(expirations, 1)
})

test('stale decisions remain a non-retryable conflict rather than being silently resubmitted', async () => {
  let requests = 0
  const client = createClient({
    token: () => null,
    expired: () => {},
    fetcher: async () => {
      requests++
      return Response.json(
        { error: { code: 'STALE_REVISION', message: 'Refresh this case', retryable: false } },
        { status: 409 },
      )
    },
  })
  await assert.rejects(
    client.post('/escalations/one/decision', { expected_revision: 2 }, 'key'),
    (error) => error.code === 'STALE_REVISION' && !error.retryable,
  )
  assert.equal(requests, 1)
})

test('network failures and invalid gateway responses remain recoverable', async () => {
  const offline = createClient({
    token: () => null,
    expired: () => {},
    fetcher: async () => {
      throw new TypeError('Network failure')
    },
  })
  await assert.rejects(
    offline.post('/sessions/one/messages', {}),
    (error) => error instanceof ApiError && error.retryable && error.status === 0,
  )
  const gateway = createClient({
    token: () => null,
    expired: () => {},
    fetcher: async () => new Response('<html>Unavailable</html>', { status: 503 }),
  })
  await assert.rejects(
    gateway.get('/tasks'),
    (error) => error.status === 503 && error.retryable && !error.message.includes('<html>'),
  )
})

test('bounded requests abort without silently creating a second operation', async () => {
  const client = createClient({
    token: () => null,
    expired: () => {},
    timeout: 5,
    fetcher: (_url, options) =>
      new Promise((_resolve, reject) =>
        options.signal.addEventListener('abort', () => reject(new Error('Aborted'))),
      ),
  })
  await assert.rejects(
    client.post('/sessions/one/messages', {}),
    (error) => error.retryable && error.message.includes('original request'),
  )
})

test('tokens never go to an external API path and source links reject executable or unrelated URLs', async () => {
  let calls = 0
  const client = createClient({
    token: () => 'test-token',
    expired: () => {},
    fetcher: async () => {
      calls++
      return Response.json({})
    },
  })
  await assert.rejects(client.get('https://example.com/tasks'))
  await assert.rejects(client.get('//example.com/tasks'))
  assert.equal(calls, 0)
  assert.equal(safeSourceUrl('javascript:alert(1)'), undefined)
  assert.equal(safeSourceUrl('https://github.com.attacker.test/repo'), undefined)
  assert.equal(safeSourceUrl('https://person:secret@github.com/repo'), undefined)
  assert.equal(
    safeSourceUrl('https://github.com/team/repo/blob/abc/file.py#L1'),
    'https://github.com/team/repo/blob/abc/file.py#L1',
  )
})
