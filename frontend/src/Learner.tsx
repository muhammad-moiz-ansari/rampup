import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { api } from './api'
import { TASK_ONE_SAMPLE_ATTEMPT, TASK_ONE_SCRIPT, taskOneQuestionCount } from './demo-api'
import { newestSession, useDraft, useOperation, useResource } from './hooks'
import type { Session, User } from './types'
import {
  AttemptCard,
  CodeExcerpt,
  Conversation,
  Dialog,
  Empty,
  Icon,
  LoadError,
  LoadingPage,
  Notice,
  OperationNotice,
  reasons,
  Spinner,
  Status,
  TaskBrief,
} from './ui'

export function LearnerWorkspace({ id, user }: { id: string; user: User }) {
  const load = useCallback(() => api.get<Session>(`/sessions/${id}`), [id])
  const resource = useResource(load, 4500, newestSession)
  const changed = useCallback(
    (session: Session) => resource.setData((previous) => newestSession(previous, session)),
    [resource.setData],
  )
  const coach = useOperation(`${user.id}.${id}.coach`, changed, resource.refresh)
  const clarification = useOperation(`${user.id}.${id}.clarification`, changed, resource.refresh)
  const mentor = useOperation(`${user.id}.${id}.mentor`, changed, resource.refresh)
  const completion = useOperation(`${user.id}.${id}.completion`, changed, resource.refresh)
  const [question, setQuestion] = useDraft(`${user.id}.${id}.question`)
  const [mentorQuestion, setMentorQuestion] = useDraft(`${user.id}.${id}.mentor-question`)
  const [modal, setModal] = useState<'attempt' | 'mentor' | 'completion' | null>(null)
  const [view, setView] = useState<'conversation' | 'attempts' | 'sources'>('conversation')
  const [requestFeedback, setRequestFeedback] = useState<{
    tone: 'info' | 'success' | 'error'
    text: string
  } | null>(null)
  const chat = useRef<HTMLDivElement>(null)
  const nearBottom = useRef(true)
  const input = useRef<HTMLTextAreaElement>(null)
  const session = resource.data
  const entryCount = (session?.messages.length || 0) + (session?.attempts.length || 0)
  useEffect(() => {
    if (nearBottom.current && view === 'conversation') {
      const box = chat.current
      if (box) box.scrollTo({ top: box.scrollHeight, behavior: 'auto' })
    } else if (view !== 'conversation') {
      chat.current?.scrollTo({ top: 0, behavior: 'auto' })
    }
  }, [entryCount, view])
  if (!session)
    return resource.error ? (
      <LoadError error={resource.error} retry={resource.refresh} />
    ) : (
      <LoadingPage />
    )

  const active = session.state === 'ACTIVE'
  const finished = session.state === 'COMPLETED'
  const scriptedTaskOne = session.task.id === 'demo-task-1'
  const scriptedQuestionsAnswered = scriptedTaskOne ? taskOneQuestionCount(session.messages) : 0
  const suggestedQuestions = scriptedTaskOne
    ? TASK_ONE_SCRIPT.slice(scriptedQuestionsAnswered, scriptedQuestionsAnswered + 1).map(
        (item) => item.question,
      )
    : session.task.suggested_questions || []
  const running = coach.busy || session.latest_run?.status === 'RUNNING'
  const coachBlocked = running || Boolean(coach.pending)
  const messageOperation = active ? coach : clarification
  const messageBlocked =
    messageOperation.busy || Boolean(messageOperation.pending) || (active && running)
  const sources = [
    ...session.messages.flatMap((message) => message.citations),
    ...(session.open_escalation?.evidence || []),
  ].filter(
    (source, index, all) =>
      all.findIndex(
        (item) =>
          item.source_id === source.source_id &&
          item.start_line === source.start_line &&
          item.end_line === source.end_line,
      ) === index,
  )
  const starterQuestions = scriptedTaskOne ? [] : ['Where should quantity validation live?']
  async function deliverQuestion(content: string) {
    if (!content.trim() || messageBlocked || finished) return
    setRequestFeedback({ tone: 'info', text: 'Sending your question to RampUp…' })
    setView('conversation')
    const outcome = await messageOperation.run(
      `/sessions/${id}/messages`,
      { content: content.trim() },
      active ? 'question' : 'clarification',
    )
    if (outcome !== 'failed') {
      setQuestion('')
      setRequestFeedback(
        outcome === 'saved'
          ? {
              tone: 'info',
              text: 'Your question was saved, but RampUp could not prepare a reply. See the error above to retry or ask your mentor.',
            }
          : {
              tone: 'success',
              text: active
                ? 'Question sent. Your message and the resulting guidance or mentor handoff are in Conversation.'
                : 'Clarification sent to your mentor and saved in Conversation.',
            },
      )
    } else {
      setRequestFeedback(null) // OperationNotice shows the actual error and recovery action.
    }
    nearBottom.current = true
  }
  async function sendQuestion(event: FormEvent) {
    event.preventDefault()
    await deliverQuestion(question)
  }
  async function askMentor(event: FormEvent) {
    event.preventDefault()
    const outcome = await mentor.run(
      `/sessions/${id}/escalations`,
      { reason: 'MANUAL', question: mentorQuestion.trim() },
      'mentor request',
    )
    if (outcome === 'done') {
      setModal(null)
      setMentorQuestion('')
    }
  }
  async function retryQuestion(operation: ReturnType<typeof useOperation>) {
    const outcome = await operation.retry()
    setView('conversation')
    if (outcome !== 'failed') setQuestion('')
    setRequestFeedback(
      outcome === 'done'
        ? {
            tone: 'success',
            text: 'Retry succeeded. The saved question and resulting guidance or mentor handoff are in Conversation.',
          }
        : outcome === 'saved'
          ? {
              tone: 'info',
              text: 'The question is saved, but RampUp still could not prepare a reply. See the updated error above or ask your mentor.',
            }
          : {
              tone: 'error',
              text: 'Retry did not complete. See the error above for the request status and next step.',
            },
    )
  }

  return (
    <div className="workspace-page">
      <header className="page-heading">
        <div>
          <a className="back-link" href="#/tasks">
            <Icon name="arrow" />
            Your tasks
          </a>
          <h1>{session.task.title}</h1>
          <div className="repository">
            <Icon name="branch" size={15} />
            <span>
              {session.task.repository.owner} / <strong>{session.task.repository.name}</strong>
            </span>
          </div>
        </div>
        <div className="heading-actions">
          {!scriptedTaskOne && (
            <button
              className="button secondary"
              onClick={() => setModal('mentor')}
              disabled={
                finished ||
                session.state === 'COMPLETION_REVIEW' ||
                Boolean(session.open_escalation) ||
                mentor.busy
              }
            >
              <Icon name="chat" />
              {session.open_escalation ? 'Mentor requested' : 'Ask my mentor'}
            </button>
          )}
          <button className="icon-button" aria-label="Refresh workspace" onClick={resource.refresh}>
            <Icon name="refresh" />
          </button>
        </div>
      </header>
      <div className="workspace-status">
        <Status state={session.state} />
        <span>Your submitted work stays here</span>
      </div>
      {resource.error && (
        <Notice
          action={
            <button className="text-button" onClick={resource.refresh}>
              Reconnect
            </button>
          }
        >
          Couldn’t refresh the workspace. {resource.error}
        </Notice>
      )}
      <OperationNotice operation={mentor} />
      <OperationNotice operation={completion} />
      <OperationNotice
        operation={coach}
        onRetry={() => {
          void retryQuestion(coach)
        }}
      />
      <OperationNotice
        operation={clarification}
        onRetry={() => {
          void retryQuestion(clarification)
        }}
      />
      <div className="learner-grid">
        <details className="task-description-disclosure learner-task-disclosure">
          <summary>
            <span>
              <strong>Task brief</strong>
              <small>Problem, goal, milestones, and code structure</small>
            </span>
            <Icon name="down" />
          </summary>
          <TaskBrief task={session.task} session={session} />
        </details>
        <section className="learning-panel" aria-label="Learning workspace">
          <div className="panel-tabs" aria-label="Workspace views">
            {(['conversation', 'attempts', 'sources'] as const).map((item) => (
              <button
                key={item}
                aria-pressed={view === item}
                className={view === item ? 'selected' : ''}
                onClick={() => setView(item)}
              >
                {item === 'conversation'
                  ? 'Conversation'
                  : item === 'attempts'
                    ? `Attempts${session.attempts.length ? ` · ${session.attempts.length}` : ''}`
                    : 'Sources'}
              </button>
            ))}
          </div>
          {(!session.task.exercise || view === 'sources') && (
            <p className="workspace-view-description" aria-live="polite">
              {view === 'conversation'
                ? 'Questions, RampUp replies, mentor guidance, and submitted attempts appear here in time order.'
                : view === 'attempts'
                  ? 'Explicit submissions with your explanation, code, test output, and coach assessment. RampUp does not run code or tests.'
                  : 'Repository excerpts cited in guidance or attached to a mentor review, pinned to the task snapshot.'}
            </p>
          )}
          {session.open_escalation && (
            <div className="handoff-banner">
              <span className="handoff-symbol">
                <Icon name="chat" />
              </span>
              <div>
                <strong>
                  {session.state === 'MENTOR_ACTIVE'
                    ? 'Your mentor is working with you.'
                    : 'Your mentor has the context.'}
                </strong>
                <p>
                  {reasons[session.open_escalation.reason]}. Add any clarification below; coaching
                  resumes after your mentor sends guidance.
                </p>
              </div>
            </div>
          )}
          {session.state === 'COMPLETION_REVIEW' && (
            <div className="handoff-banner">
              <span className="handoff-symbol">
                <Icon name="check" />
              </span>
              <div>
                <strong>Completion review requested</strong>
                <p>
                  Your mentor will confirm completion or suggest what to revisit. You can add a note
                  below.
                </p>
              </div>
            </div>
          )}
          {finished && (
            <div className="completed-banner">
              <Icon name="check" />
              <div>
                <strong>Task completed</strong>
                <p>
                  Your work meets the task criteria. Your conversation and sources are here whenever
                  you need them.
                </p>
              </div>
            </div>
          )}
          <div
            className="conversation-scroll"
            ref={chat}
            onScroll={() => {
              const box = chat.current
              if (box)
                nearBottom.current = box.scrollHeight - box.scrollTop - box.clientHeight < 120
            }}
          >
            {view === 'conversation' &&
              (entryCount ? (
                <Conversation messages={session.messages} attempts={session.attempts} />
              ) : (
                <div className="conversation-start">
                  <h2>Ask about the code</h2>
                  <p>Ask a question or share your approach.</p>
                  <div className="starter-questions">
                    {(scriptedTaskOne
                      ? TASK_ONE_SCRIPT.slice(
                          scriptedQuestionsAnswered,
                          scriptedQuestionsAnswered + 1,
                        ).map((item) => item.question)
                      : session.task.suggested_questions?.length
                        ? session.task.suggested_questions
                        : ['Where should I start?', 'Which file should I read first?']
                    ).map((prompt) => (
                      <button
                        key={prompt}
                        onClick={() => {
                          setQuestion(prompt)
                          input.current?.focus()
                        }}
                        disabled={coachBlocked}
                      >
                        <Icon name="plus" size={14} />
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            {view === 'attempts' && session.task.exercise && (
              <section className="exercise-brief">
                <h2>{session.task.exercise.answer_label}</h2>
                <p>{session.task.exercise.prompt}</p>
                <pre tabIndex={0}>
                  <code>{session.task.exercise.starter}</code>
                </pre>
                <button
                  className="button primary"
                  disabled={!active || coachBlocked || finished}
                  onClick={() => setModal('attempt')}
                >
                  <Icon name="code" />
                  Write answer
                </button>
              </section>
            )}
            {view === 'attempts' &&
              (session.attempts.length ? (
                <div className="attempt-history">
                  {session.attempts.map((attempt, index) => (
                    <AttemptCard key={attempt.id} attempt={attempt} number={index + 1} />
                  ))}
                </div>
              ) : (
                !session.task.exercise && (
                  <Empty title="No attempts yet" icon="code">
                    Share an approach or a small change when you’re ready. It can be a work in
                    progress.
                  </Empty>
                )
              ))}
            {view === 'sources' &&
              (sources.length ? (
                <div className="source-history">
                  <h2>The code behind the guidance</h2>
                  <p className="muted">Repository excerpts referenced in the conversation.</p>
                  {sources.map((source) => (
                    <CodeExcerpt
                      key={`${source.source_id}-${source.start_line}-${source.end_line}`}
                      source={source}
                    />
                  ))}
                </div>
              ) : (
                <Empty title="Sources will appear here." icon="file">
                  Repository excerpts are collected as you receive guidance.
                </Empty>
              ))}
          </div>
          {!finished && (
            <div className="composer-area">
              {requestFeedback && (
                <Notice tone={requestFeedback.tone}>{requestFeedback.text}</Notice>
              )}
              {running && active && (
                <div className="typing-indicator" role="status" aria-label="RampUp is typing">
                  <span>RampUp</span>
                  <span>is typing</span>
                  <i aria-hidden="true">
                    <b />
                    <b />
                    <b />
                  </i>
                </div>
              )}
              {active &&
                entryCount > 0 &&
                suggestedQuestions.filter(
                  (prompt) =>
                    !session.messages.some(
                      (message) =>
                        message.author === 'LEARNER' && message.content.trim() === prompt,
                    ),
                ).length > 0 && (
                  <div className="next-questions">
                    {suggestedQuestions
                      .filter(
                        (prompt) =>
                          !session.messages.some(
                            (message) =>
                              message.author === 'LEARNER' && message.content.trim() === prompt,
                          ),
                      )
                      .map((prompt) => (
                        <button
                          className="text-button"
                          key={prompt}
                          onClick={() => {
                            setQuestion(prompt)
                            setView('conversation')
                            input.current?.focus()
                          }}
                          disabled={coachBlocked}
                        >
                          <Icon name="plus" size={14} />
                          {prompt}
                        </button>
                      ))}
                  </div>
                )}
              {!(session.task.exercise && view === 'attempts') && (
                <form className="composer" onSubmit={sendQuestion}>
                  <label className="sr-only" htmlFor="question">
                    {active ? 'Your question' : 'Add a clarification'}
                  </label>
                  <textarea
                    id="question"
                    ref={input}
                    value={question}
                    onChange={(event) => {
                      setQuestion(event.target.value)
                      setRequestFeedback(null)
                    }}
                    placeholder={
                      active
                        ? 'What would you like to work through?'
                        : 'Add a note for your mentor…'
                    }
                    required
                    maxLength={8000}
                    rows={3}
                    disabled={messageBlocked}
                    onKeyDown={(event) => {
                      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
                        event.preventDefault()
                        event.currentTarget.form?.requestSubmit()
                      }
                    }}
                  />
                  <div className="composer-footer">
                    <span>
                      {active ? '' : 'This note goes to your mentor.'}{' '}
                      <span className="keyboard-hint">Ctrl + Enter to send</span>
                    </span>
                    <button
                      className="send-button"
                      type="submit"
                      disabled={!question.trim() || messageBlocked}
                      aria-label={active ? 'Send question' : 'Send clarification'}
                    >
                      <Icon name="arrow" />
                    </button>
                  </div>
                </form>
              )}
              <div className="workspace-bottom">
                {!(session.task.exercise && view === 'attempts') && (
                  <button
                    className="text-button"
                    onClick={() => setModal('attempt')}
                    disabled={!active || coachBlocked}
                  >
                    <Icon name="code" size={16} />
                    {session.task.exercise ? 'Write answer' : 'Share an attempt'}
                  </button>
                )}
                <button
                  className="text-button"
                  onClick={() => setModal('completion')}
                  disabled={
                    !active || coachBlocked || completion.busy || Boolean(completion.pending)
                  }
                >
                  Request completion review <Icon name="arrow" size={14} />
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
      {modal === 'mentor' && (
        <Dialog title="Ask your mentor" onClose={() => setModal(null)}>
          <p className="dialog-description">
            A fresh perspective can help. Your conversation, attempts and repository evidence will
            travel with your question.
          </p>
          <form onSubmit={askMentor}>
            <label htmlFor="mentor-question">What would you like a second opinion on?</label>
            <textarea
              id="mentor-question"
              value={mentorQuestion}
              onChange={(event) => setMentorQuestion(event.target.value)}
              required
              maxLength={8000}
              rows={5}
              autoFocus
              disabled={mentor.busy || Boolean(mentor.pending)}
              placeholder="I’m unsure where validation should live…"
            />
            <OperationNotice
              operation={mentor}
              onRetry={() => {
                void mentor.retry().then((result) => {
                  if (result === 'done') {
                    setModal(null)
                    setMentorQuestion('')
                  }
                })
              }}
            />
            <footer className="dialog-actions">
              <button type="button" className="button quiet" onClick={() => setModal(null)}>
                Keep working
              </button>
              <button
                className="button primary"
                disabled={!mentorQuestion.trim() || mentor.busy || Boolean(mentor.pending)}
              >
                {mentor.busy ? <Spinner /> : <Icon name="chat" />}Send mentor request
              </button>
            </footer>
          </form>
        </Dialog>
      )}
      {modal === 'attempt' && (
        <AttemptForm
          user={user}
          session={session}
          operation={coach}
          close={() => setModal(null)}
          onSubmitted={(outcome) => {
            setView('conversation')
            setModal(null)
            setRequestFeedback(
              outcome === 'saved'
                ? {
                    tone: 'info',
                    text: 'Your attempt was saved, but RampUp could not prepare feedback. See the error above to retry or ask your mentor.',
                  }
                : {
                    tone: 'success',
                    text: 'Attempt submitted. RampUp feedback or a mentor handoff will appear in Conversation.',
                  },
            )
          }}
        />
      )}
      {modal === 'completion' && (
        <Dialog title="Ready for a review?" onClose={() => setModal(null)}>
          <p className="dialog-description">
            Your mentor will review your saved work against the task criteria. They’ll confirm
            completion or return it with guidance.
          </p>
          <ul className="review-criteria">
            {session.task.milestones
              .flatMap((milestone) => milestone.criteria)
              .map((criterion) => (
                <li key={criterion}>
                  <Icon name="check" size={15} />
                  {criterion}
                </li>
              ))}
          </ul>
          <OperationNotice
            operation={completion}
            onRetry={() => {
              void completion.retry().then((result) => {
                if (result === 'done') setModal(null)
              })
            }}
          />
          <footer className="dialog-actions">
            <button className="button quiet" onClick={() => setModal(null)}>
              Keep working
            </button>
            <button
              className="button primary"
              disabled={completion.busy || Boolean(completion.pending)}
              onClick={() => {
                void completion
                  .run(
                    `/sessions/${id}/completion-request`,
                    { expected_version: session.version },
                    'completion request',
                  )
                  .then((outcome) => {
                    if (outcome === 'done') setModal(null)
                  })
              }}
            >
              {completion.busy ? <Spinner /> : <Icon name="arrow" />}Request review
            </button>
          </footer>
        </Dialog>
      )}
    </div>
  )
}

function AttemptForm({
  session,
  user,
  operation,
  close,
  onSubmitted,
}: {
  session: Session
  user: User
  operation: ReturnType<typeof useOperation>
  close: () => void
  onSubmitted: (outcome: 'done' | 'saved') => void
}) {
  const scope = `${user.id}.${session.id}.attempt`
  const exercise = session.task.exercise
  const [explanation, setExplanation] = useDraft(`${scope}.explanation`)
  const [code, setCode] = useDraft(`${scope}.code`)
  const [files, setFiles] = useDraft(`${scope}.files`)
  const [tests, setTests] = useDraft(`${scope}.tests`)
  const scriptedTaskOne = session.task.id === 'demo-task-1'
  function loadPreparedAttempt() {
    setExplanation(TASK_ONE_SAMPLE_ATTEMPT.explanation)
    setCode(TASK_ONE_SAMPLE_ATTEMPT.code)
    setFiles(TASK_ONE_SAMPLE_ATTEMPT.file_paths.join('\n'))
    setTests('')
  }
  const paths = files
    .split(/[\n,]/)
    .map((path) => path.trim())
    .filter(Boolean)
  const protectedChange = paths.some((path) =>
    session.task.protected_paths.includes(path.replace(/^\.\//, '')),
  )
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (paths.length > 30 || operation.busy || operation.pending) return
    const outcome = await operation.run(
      `/sessions/${session.id}/attempts`,
      {
        milestone_id: session.current_milestone_id,
        explanation: exercise ? exercise.prompt : explanation.trim(),
        code,
        file_paths: exercise ? [exercise.path] : paths,
        test_output: tests.trim() || null,
      },
      'attempt',
    )
    if (outcome !== 'failed') {
      setExplanation('')
      setCode('')
      setFiles('')
      setTests('')
      onSubmitted(outcome)
    }
  }
  return (
    <Dialog title={exercise ? 'Write your answer' : 'Share an attempt'} onClose={close} wide>
      <p className="dialog-description">
        {exercise
          ? exercise.prompt
          : 'Show your thinking, even if it’s unfinished. Code and test output are reviewed as material you provide.'}
      </p>
      <form onSubmit={submit}>
        <fieldset disabled={operation.busy || Boolean(operation.pending)}>
          {!exercise && (
            <>
              <label htmlFor="attempt-explanation">What did you try?</label>
              <textarea
                id="attempt-explanation"
                value={explanation}
                onChange={(event) => setExplanation(event.target.value)}
                rows={3}
                required
                maxLength={8000}
                autoFocus
                placeholder="My approach was…"
              />
            </>
          )}
          <label htmlFor="attempt-code">
            {exercise ? (
              exercise.answer_label
            ) : (
              <>
                Code or diff <span>Optional</span>
              </>
            )}
          </label>
          <textarea
            className="code-input"
            id="attempt-code"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            rows={7}
            maxLength={16000}
            spellCheck={false}
            placeholder={
              exercise ? exercise.starter : 'Paste a small change or an approach in code'
            }
            required={Boolean(exercise)}
            autoFocus={Boolean(exercise)}
          />
          {!exercise && (
            <div className="form-columns">
              <div>
                <label htmlFor="attempt-paths">
                  File paths <span>Optional</span>
                </label>
                <textarea
                  className="code-input"
                  id="attempt-paths"
                  value={files}
                  onChange={(event) => setFiles(event.target.value)}
                  rows={3}
                  maxLength={6000}
                  spellCheck={false}
                  aria-invalid={paths.length > 30}
                  placeholder={'demo-repo/schemas.py\ndemo-repo/routes.py'}
                />
                <p className="field-help">One path per line, up to 30.</p>
                {paths.length > 30 && (
                  <p role="alert" className="field-error">
                    Use at most 30 paths.
                  </p>
                )}
              </div>
              <div>
                <label htmlFor="attempt-tests">
                  Test output <span>Optional</span>
                </label>
                <textarea
                  className="code-input"
                  id="attempt-tests"
                  value={tests}
                  onChange={(event) => setTests(event.target.value)}
                  rows={3}
                  maxLength={8000}
                  spellCheck={false}
                  placeholder="Paste the output you observed"
                />
              </div>
            </div>
          )}
        </fieldset>
        {protectedChange && (
          <Notice tone="info">
            This attempt includes a protected path. Your mentor will review it before coaching
            continues.
          </Notice>
        )}
        <OperationNotice operation={operation} />
        <footer className="dialog-actions">
          <button className="button quiet" type="button" onClick={close}>
            Keep draft
          </button>
          <button
            className="button primary"
            disabled={
              !(exercise ? code.trim() : explanation.trim()) ||
              paths.length > 30 ||
              operation.busy ||
              Boolean(operation.pending)
            }
          >
            {operation.busy ? <Spinner /> : <Icon name="arrow" />}
            {exercise ? 'Submit answer' : 'Submit attempt'}
          </button>
        </footer>
      </form>
    </Dialog>
  )
}
