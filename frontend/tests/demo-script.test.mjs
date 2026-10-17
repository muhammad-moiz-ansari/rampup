import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ApiError, localRequest } from '../src/api.ts'
import { demoRequest, TASK_ONE_SAMPLE_ATTEMPT, TASK_ONE_SCRIPT } from '../src/demo-api.ts'

const values = new Map()
globalThis.localStorage = {
  getItem: (key) => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, value),
  removeItem: (key) => values.delete(key),
  clear: () => values.clear(),
}

test('question validation reports a correctable error instead of an ambiguous delivery failure', async () => {
  values.clear()
  const session = await localRequest('POST', '/sessions', { task_id: 'demo-task-1' })
  await assert.rejects(
    localRequest('POST', `/sessions/${session.id}/messages`, { content: 'Where should I start?' }),
    (error) =>
      error instanceof ApiError &&
      error.status === 400 &&
      !error.retryable &&
      /next question/.test(error.message),
  )
  const updated = await localRequest('POST', `/sessions/${session.id}/messages`, {
    content: TASK_ONE_SCRIPT[0].question,
  })
  assert.equal(updated.messages.at(-1).content, TASK_ONE_SCRIPT[0].response)
})

test('Task 1 follows the scripted questions and criteria-gates completion', async () => {
  values.clear()
  const tasks = await demoRequest('GET', '/tasks')
  const task = tasks.items.find((item) => item.id === 'demo-task-1')
  assert.ok(task)
  const session = await demoRequest('POST', '/sessions', { task_id: task.id })
  const attemptPath = `/sessions/${session.id}/attempts`
  const messagePath = `/sessions/${session.id}/messages`
  const baseAttempt = {
    milestone_id: session.current_milestone_id,
    explanation: 'I tried a basic change.',
    code: '',
    file_paths: [],
    test_output: null,
  }

  await assert.rejects(
    demoRequest('POST', attemptPath, baseAttempt),
    /Answer both questions before sharing your work/,
  )
  await assert.rejects(
    demoRequest('POST', messagePath, { content: TASK_ONE_SCRIPT[1].question }),
    /Choose the next question shown in the workspace/,
  )

  let updated = await demoRequest('POST', messagePath, {
    content: TASK_ONE_SCRIPT[0].question,
  })
  assert.equal(updated.messages.at(-1).content, TASK_ONE_SCRIPT[0].response)
  updated = await demoRequest('POST', messagePath, {
    content: TASK_ONE_SCRIPT[1].question,
  })
  assert.equal(updated.messages.at(-1).content, TASK_ONE_SCRIPT[1].response)

  updated = await demoRequest('POST', attemptPath, baseAttempt)
  assert.equal(updated.state, 'ACTIVE')
  assert.equal(updated.attempts.at(-1).assessment, 'UNRESOLVED')

  updated = await demoRequest('POST', attemptPath, {
    milestone_id: session.current_milestone_id,
    ...TASK_ONE_SAMPLE_ATTEMPT,
    test_output: null,
  })
  assert.equal(updated.state, 'COMPLETED')
  assert.equal(updated.attempts.at(-1).assessment, 'PROGRESS')
})

test('previously saved task feedback no longer exposes internal wording', async () => {
  values.set(
    'rampup.scripted-demo',
    JSON.stringify({
      sessions: {
        legacy: {
          messages: [
            {
              content: 'Scripted check: your submission meets the task criteria. Task complete.',
            },
          ],
          attempts: [{ assessment_note: 'Scripted check: all criteria met.' }],
        },
      },
      cases: {},
    }),
  )
  const session = await demoRequest('GET', '/sessions/legacy')
  assert.equal(
    session.messages[0].content,
    'Review: your submission meets the task criteria. Task complete.',
  )
  assert.equal(session.attempts[0].assessment_note, 'Review: all criteria met.')
  assert.equal(localStorage.getItem('rampup.scripted-demo').includes('Scripted check'), false)
})
