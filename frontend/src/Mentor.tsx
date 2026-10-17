import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { api } from './api'
import { newestSession, useDraft, useOperation, useResource } from './hooks'
import type {
  CaseSummary,
  DecisionAction,
  List,
  MentorCase,
  Session,
  SessionSummary,
  User,
} from './types'
import {
  ActivityList,
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
  Timestamp,
} from './ui'

export function MentorQueue({ completed = false }: { completed?: boolean }) {
  const [resolved, setResolved] = useState(false)
  const load = useCallback(async () => {
    const [cases, reviews] = await Promise.all([
      api.get<List<CaseSummary>>(`/mentor/escalations?status=${resolved ? 'RESOLVED' : 'OPEN'}`),
      api.get<List<SessionSummary>>('/mentor/completion-reviews'),
    ])
    return {
      cases: cases.items.sort((a, b) => a.created_at.localeCompare(b.created_at)),
      reviews: reviews.items.sort((a, b) => a.updated_at.localeCompare(b.updated_at)),
    }
  }, [resolved])
  const resource = useResource(load, 5500)
  if (!resource.data)
    return resource.error ? (
      <LoadError error={resource.error} retry={resource.refresh} />
    ) : (
      <LoadingPage />
    )
  const { cases, reviews } = resource.data
  const count = completed ? reviews.length : cases.length
  return (
    <div className="page queue-page">
      <header className="page-heading">
        <div>
          <h1>{completed ? 'Completion reviews' : 'Review queue'}</h1>
        </div>
        <button className="button secondary" onClick={resource.refresh}>
          <Icon name="refresh" />
          Refresh
        </button>
      </header>
      {resource.error && (
        <Notice
          action={
            <button className="text-button" onClick={resource.refresh}>
              Reconnect
            </button>
          }
        >
          The queue couldn’t refresh. {resource.error}
        </Notice>
      )}
      <div className="queue-toolbar">
        <div className="filter-switch">
          {!completed && (
            <>
              <button aria-pressed={!resolved} onClick={() => setResolved(false)}>
                Needs a response
              </button>
              <button aria-pressed={resolved} onClick={() => setResolved(true)}>
                Resolved
              </button>
            </>
          )}
          {completed && <span>Waiting for your review</span>}
        </div>
        <span className="muted">
          {count}{' '}
          {completed ? (count === 1 ? 'review' : 'reviews') : count === 1 ? 'case' : 'cases'}
        </span>
      </div>
      {!count ? (
        <Empty
          title={
            resolved
              ? 'No resolved cases yet.'
              : completed
                ? 'No work waiting for review.'
                : 'Nothing waiting on you.'
          }
          icon={completed ? 'check' : 'inbox'}
        >
          {resolved
            ? 'Cases you resolve will stay here for reference.'
            : completed
              ? 'When a learner requests completion, their work will appear here.'
              : 'New mentor requests will arrive with the conversation, attempts and sources you need.'}
        </Empty>
      ) : (
        <div className="queue-list">
          <div className="queue-labels" aria-hidden="true">
            <span>Learner and task</span>
            <span>{completed ? 'State' : 'Reason'}</span>
            <span>{resolved ? 'Opened' : 'Waiting since'}</span>
            <span />
          </div>
          {completed
            ? reviews.map((review) => (
                <a className="queue-row" href={`#/completion/${review.id}`} key={review.id}>
                  <div>
                    <span className="person-avatar">{review.learner_name.slice(0, 1)}</span>
                    <div>
                      <strong>{review.task_title}</strong>
                      <span>{review.learner_name}</span>
                    </div>
                  </div>
                  <span className="queue-reason">
                    <Icon name="check" size={15} />
                    Completion review
                  </span>
                  <Timestamp date={review.updated_at} />
                  <Icon name="chevron" />
                </a>
              ))
            : cases.map((item) => (
                <a className="queue-row" href={`#/review/${item.id}`} key={item.id}>
                  <div>
                    <span className="person-avatar">{item.learner_name.slice(0, 1)}</span>
                    <div>
                      <strong>{item.task_title}</strong>
                      <span>{item.learner_name}</span>
                    </div>
                  </div>
                  <span className={`queue-reason reason-${item.reason.toLowerCase()}`}>
                    <span className="reason-dot" />
                    {reasons[item.reason]}
                  </span>
                  <Timestamp date={item.created_at} />
                  <Icon name="chevron" />
                </a>
              ))}
        </div>
      )}
      {!completed && reviews.length > 0 && (
        <a className="completion-callout" href="#/completions">
          <span className="callout-icon">
            <Icon name="check" />
          </span>
          <div>
            <strong>
              {reviews.length === 1
                ? 'One learner is ready for a final review.'
                : `${reviews.length} learners are ready for a final review.`}
            </strong>
            <span>Review their work and confirm what comes next.</span>
          </div>
          <Icon name="arrow" />
        </a>
      )}
      <p className="queue-footnote">
        <span className="live-dot" />
        The queue updates automatically. Oldest requests appear first.
      </p>
    </div>
  )
}

interface ReviewData {
  case: MentorCase
  session: Session
}
function newestReview(previous: ReviewData | null, next: ReviewData) {
  return previous?.case.id === next.case.id && previous.session.version > next.session.version
    ? previous
    : next
}
const actionLabels: Record<DecisionAction, string> = {
  SEND_GUIDANCE: 'Send guidance',
  ASK_QUESTION: 'Ask a question',
  TAKE_OVER: 'Take over',
  REJECT_SUGGESTION: 'Reject suggestion',
}
const descriptions: Record<DecisionAction, string> = {
  SEND_GUIDANCE: 'Your exact text will be delivered, and the learner can continue with coaching.',
  ASK_QUESTION: 'Ask for the detail you need. Coaching stays paused while the case is open.',
  TAKE_OVER: 'Let the learner know how you’ll work together. Coaching stays paused.',
  REJECT_SUGGESTION:
    'Record why the draft should not be used. Your note stays in mentor review; the case remains open.',
}

export function MentorReview({ id, user }: { id: string; user: User }) {
  const load = useCallback(async () => {
    const detail = await api.get<MentorCase>(`/escalations/${id}`)
    const session = await api.get<Session>(`/sessions/${detail.session_id}`)
    return {
      case: session.open_escalation?.id === detail.id ? session.open_escalation : detail,
      session,
    }
  }, [id])
  const resource = useResource(load, 5500, newestReview)
  const scope = `${user.id}.${id}`
  const [response, setResponse] = useDraft(`${scope}.guidance`)
  const [reviewed, setReviewed] = useDraft(`${scope}.revision`)
  const [actionDraft, setActionDraft] = useDraft(`${scope}.action`)
  const action: DecisionAction = Object.hasOwn(actionLabels, actionDraft)
    ? (actionDraft as DecisionAction)
    : 'SEND_GUIDANCE'
  const [tab, setTab] = useState<'context' | 'conversation' | 'attempts' | 'activity'>('context')
  const [sent, setSent] = useState('')
  const initialized = useRef(false)
  const changed = useCallback(
    (session: Session) => {
      resource.setData((previous) =>
        previous && previous.session.version <= session.version
          ? {
              session,
              case:
                session.open_escalation?.id === id
                  ? session.open_escalation
                  : { ...previous.case, status: 'RESOLVED' },
            }
          : previous,
      )
      if (session.open_escalation?.id === id) setReviewed(String(session.open_escalation.revision))
    },
    [id, resource.setData, setReviewed],
  )
  const operation = useOperation(`${scope}.decision`, changed, resource.refresh)
  useEffect(() => {
    const pendingAction = operation.pending?.body.action
    if (
      !actionDraft &&
      typeof pendingAction === 'string' &&
      Object.hasOwn(actionLabels, pendingAction)
    ) {
      setActionDraft(pendingAction)
    }
  }, [actionDraft, operation.pending, setActionDraft])
  useEffect(() => {
    if (resource.data && !initialized.current) {
      if (!response && !reviewed) setResponse(resource.data.case.proposed_guidance)
      if (!reviewed) setReviewed(String(resource.data.case.revision))
      initialized.current = true
    }
  }, [resource.data, response, reviewed, setResponse, setReviewed])
  if (!resource.data)
    return resource.error ? (
      <LoadError error={resource.error} retry={resource.refresh} />
    ) : (
      <LoadingPage />
    )
  const detail = resource.data.case,
    session = resource.data.session
  const open = detail.status === 'OPEN' && session.open_escalation?.id === id
  const stale = Number(reviewed) !== detail.revision
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (stale || !open || operation.busy || operation.pending || !response.trim()) return
    const result = await operation.run(
      `/escalations/${id}/decision`,
      { action, expected_revision: Number(reviewed), text: response.trim() },
      'mentor decision',
    )
    if (result === 'done') {
      setResponse('')
      setSent(
        action === 'SEND_GUIDANCE'
          ? 'Guidance sent. The learner can continue.'
          : action === 'ASK_QUESTION'
            ? 'Your question is with the learner. The case stays open.'
            : action === 'TAKE_OVER'
              ? 'You’ve taken over this conversation.'
              : 'Suggestion rejected. Choose the next way to help.',
      )
    }
  }
  return (
    <div className="workspace-page review-page">
      <header className="page-heading">
        <div>
          <a className="back-link" href="#/reviews">
            <Icon name="arrow" />
            Review queue
          </a>
          <h1>{detail.task_title}</h1>
          <div className="review-meta">
            <span className="person-avatar small">{detail.learner_name.slice(0, 1)}</span>
            <span>{detail.learner_name}</span>
            <span className="meta-divider">·</span>
            <span>{reasons[detail.reason]}</span>
            <span className="meta-divider">·</span>
            <Timestamp date={detail.created_at} />
          </div>
        </div>
        <button className="icon-button" aria-label="Refresh case" onClick={resource.refresh}>
          <Icon name="refresh" />
        </button>
      </header>
      {resource.error && (
        <Notice
          action={
            <button className="text-button" onClick={resource.refresh}>
              Reconnect
            </button>
          }
        >
          {resource.error}
        </Notice>
      )}
      {sent && <Notice tone="success">{sent}</Notice>}
      {!open && (
        <Notice tone="success">
          This case is resolved. The saved discussion and evidence remain available.
        </Notice>
      )}
      <div className="mentor-grid">
        <section className="review-context">
          <div className="panel-tabs" aria-label="Case views">
            {(['context', 'conversation', 'attempts', 'activity'] as const).map((view) => (
              <button
                key={view}
                aria-pressed={tab === view}
                className={tab === view ? 'selected' : ''}
                onClick={() => setTab(view)}
              >
                {view === 'context'
                  ? 'Context'
                  : view === 'conversation'
                    ? 'Conversation'
                    : view === 'attempts'
                      ? `Attempts · ${session.attempts.length}`
                      : 'Activity'}
              </button>
            ))}
          </div>
          <div className="review-content">
            {tab === 'context' && (
              <>
                <div className="case-question">
                  <span className="case-question-icon">
                    <Icon name="chat" size={22} />
                  </span>
                  <h2>Review request</h2>
                  <p>{detail.unresolved_question || detail.learner_question}</p>
                </div>
                {detail.summary && (
                  <section className="review-section">
                    <h3>Reason for review</h3>
                    <p className="preserve">{detail.summary}</p>
                  </section>
                )}
                {detail.learner_question &&
                  detail.learner_question !== detail.unresolved_question && (
                    <section className="review-section">
                      <h3>In their words</h3>
                      <blockquote>{detail.learner_question}</blockquote>
                    </section>
                  )}
                <section className="review-section">
                  <h3>
                    Repository evidence{' '}
                    <span>
                      {detail.evidence.length}{' '}
                      {detail.evidence.length === 1 ? 'excerpt' : 'excerpts'}
                    </span>
                  </h3>
                  {detail.evidence.length ? (
                    detail.evidence.map((source, index) => (
                      <CodeExcerpt key={`${source.source_id}-${index}`} source={source} />
                    ))
                  ) : (
                    <p className="muted">
                      No repository excerpts are attached. Use the conversation and attempts for
                      context.
                    </p>
                  )}
                </section>
                {session.attempts.length > 0 && (
                  <section className="review-section">
                    <h3>Latest attempt</h3>
                    <AttemptCard
                      attempt={session.attempts.at(-1)!}
                      number={session.attempts.length}
                    />
                  </section>
                )}
                <details className="policy-details">
                  <summary>
                    Task criteria and working agreement <Icon name="down" size={14} />
                  </summary>
                  <TaskBrief task={session.task} />
                </details>
              </>
            )}
            {tab === 'conversation' &&
              (session.messages.length ? (
                <Conversation messages={session.messages} learnerName={detail.learner_name} />
              ) : (
                <Empty title="No messages yet." icon="chat">
                  The learner’s conversation will stay here as it develops.
                </Empty>
              ))}
            {tab === 'attempts' &&
              (session.attempts.length ? (
                <div className="attempt-history">
                  {session.attempts.map((attempt, index) => (
                    <AttemptCard key={attempt.id} attempt={attempt} number={index + 1} />
                  ))}
                </div>
              ) : (
                <Empty title="No attempts submitted." icon="code">
                  The learner can ask for a mentor before submitting code.
                </Empty>
              ))}
            {tab === 'activity' && <ActivityList activity={session.activity} />}
          </div>
        </section>
        <aside className="decision-panel">
          <div className="decision-intro">
            <span className="decision-symbol">
              <Icon name="chat" size={22} />
            </span>
            <h2>Your response</h2>
          </div>
          <OperationNotice
            operation={operation}
            onRetry={() => {
              void operation.retry().then((result) => {
                if (result === 'done') {
                  setResponse('')
                  setSent('Your decision was saved.')
                }
              })
            }}
          />
          {open ? (
            <form onSubmit={submit}>
              <label htmlFor="decision-action">How would you like to help?</label>
              <select
                id="decision-action"
                value={action}
                onChange={(event) => {
                  setActionDraft(event.target.value)
                  operation.clearError()
                  setSent('')
                }}
                disabled={operation.busy || Boolean(operation.pending)}
              >
                {Object.entries(actionLabels).map(([value, label]) => (
                  <option
                    key={value}
                    value={value}
                    disabled={value === 'REJECT_SUGGESTION' && !detail.proposed_guidance}
                  >
                    {label}
                  </option>
                ))}
              </select>
              <p className="field-help action-description">{descriptions[action]}</p>
              <label htmlFor="mentor-response">
                {action === 'REJECT_SUGGESTION' ? 'Reason for rejection' : 'Your response'}
              </label>
              <textarea
                id="mentor-response"
                value={response}
                onChange={(event) => {
                  setResponse(event.target.value)
                  setSent('')
                }}
                rows={10}
                required
                maxLength={8000}
                placeholder={
                  detail.proposed_guidance
                    ? 'Review and edit the suggested guidance…'
                    : 'Start with the next small, useful step…'
                }
                disabled={operation.busy || Boolean(operation.pending)}
              />
              {detail.proposed_guidance && action !== 'REJECT_SUGGESTION' && (
                <p className="field-help">
                  The suggestion is a draft. Review the evidence and make it your own.
                </p>
              )}
              {stale && (
                <Notice
                  tone="info"
                  action={
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => setReviewed(String(detail.revision))}
                    >
                      I’ve reviewed the update
                    </button>
                  }
                >
                  New context arrived. Read the latest conversation and evidence before sending.
                  Your draft is preserved.
                </Notice>
              )}
              <button
                className="button primary full-width"
                disabled={stale || !response.trim() || operation.busy || Boolean(operation.pending)}
              >
                {operation.busy ? (
                  <Spinner />
                ) : (
                  <Icon name={action === 'REJECT_SUGGESTION' ? 'close' : 'arrow'} />
                )}
                {actionLabels[action]}
              </button>
              <p className="decision-footnote">
                {action === 'REJECT_SUGGESTION'
                  ? 'The learner will not receive the rejected draft.'
                  : 'Your exact response is saved and delivered once.'}
              </p>
            </form>
          ) : (
            <div className="resolved-panel">
              <Icon name="check" size={26} />
              <h3>Review saved</h3>
              <p>
                This review is saved. You can return to the queue to help with the next question.
              </p>
              <a className="button secondary full-width" href="#/reviews">
                Back to the queue <Icon name="arrow" />
              </a>
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}

export function CompletionReview({ id, user }: { id: string; user: User }) {
  const load = useCallback(() => api.get<Session>(`/sessions/${id}`), [id])
  const resource = useResource(load, 5500, newestSession)
  const [response, setResponse] = useDraft(`${user.id}.${id}.completion-note`)
  const [reviewed, setReviewed] = useDraft(`${user.id}.${id}.completion-version`)
  const [confirm, setConfirm] = useState(false)
  const form = useRef<HTMLFormElement>(null)
  const initialized = useRef(false)
  const changed = useCallback(
    (session: Session) => resource.setData((previous) => newestSession(previous, session)),
    [resource.setData],
  )
  const operation = useOperation(`${user.id}.${id}.completion-decision`, changed, resource.refresh)
  useEffect(() => {
    if (resource.data && !initialized.current) {
      if (!reviewed) setReviewed(String(resource.data.version))
      initialized.current = true
    }
  }, [resource.data, reviewed, setReviewed])
  if (!resource.data)
    return resource.error ? (
      <LoadError error={resource.error} retry={resource.refresh} />
    ) : (
      <LoadingPage />
    )
  const session = resource.data,
    open = session.state === 'COMPLETION_REVIEW',
    stale = Number(reviewed) !== session.version
  async function decide(approved: boolean) {
    if (!open || stale || operation.busy || operation.pending || !response.trim()) return
    const result = await operation.run(
      `/sessions/${id}/completion-decision`,
      { expected_version: Number(reviewed), approved, text: response.trim() },
      'completion decision',
    )
    if (result === 'done') {
      setConfirm(false)
      setResponse('')
      setReviewed('')
    }
  }
  return (
    <div className="workspace-page">
      <header className="page-heading">
        <div>
          <a className="back-link" href="#/completions">
            <Icon name="arrow" />
            Completion reviews
          </a>
          <h1>{session.task.title}</h1>
          <div className="review-meta">
            <Status state={session.state} />
            <span>
              {session.attempts.length} saved{' '}
              {session.attempts.length === 1 ? 'attempt' : 'attempts'}
            </span>
          </div>
        </div>
        <button
          className="icon-button"
          aria-label="Refresh completion review"
          onClick={resource.refresh}
        >
          <Icon name="refresh" />
        </button>
      </header>
      {resource.error && (
        <Notice
          action={
            <button className="text-button" onClick={resource.refresh}>
              Reconnect
            </button>
          }
        >
          {resource.error}
        </Notice>
      )}
      <div className="mentor-grid">
        <section className="review-context completion-context">
          <header className="section-heading">
            <h2>The work so far</h2>
            <span>Saved conversation and attempts</span>
          </header>
          <Conversation
            messages={session.messages}
            attempts={session.attempts}
            learnerName="Learner"
          />
        </section>
        <aside className="decision-panel completion-decision">
          <h2>Review completion</h2>
          <p className="muted">
            Review the work against these criteria, then leave a note for the learner.
          </p>
          <ul className="review-criteria">
            {session.task.milestones
              .flatMap((milestone) => milestone.criteria)
              .map((criterion) => (
                <li key={criterion}>
                  <span className="criterion-dot" />
                  {criterion}
                </li>
              ))}
          </ul>
          <OperationNotice operation={operation} />
          {open ? (
            <form
              ref={form}
              onSubmit={(event: FormEvent) => {
                event.preventDefault()
                void decide(false)
              }}
            >
              <label htmlFor="completion-note">Your review note</label>
              <textarea
                id="completion-note"
                value={response}
                onChange={(event) => setResponse(event.target.value)}
                required
                maxLength={8000}
                rows={7}
                placeholder="What went well, or what should they revisit?"
                disabled={operation.busy || Boolean(operation.pending)}
              />
              {stale && (
                <Notice
                  tone="info"
                  action={
                    <button
                      className="text-button"
                      type="button"
                      onClick={() => setReviewed(String(session.version))}
                    >
                      I’ve reviewed the update
                    </button>
                  }
                >
                  The learner’s work changed. Review the latest context before deciding.
                </Notice>
              )}
              <button
                className="button primary full-width"
                type="button"
                disabled={stale || !response.trim() || operation.busy || Boolean(operation.pending)}
                onClick={() => {
                  if (form.current?.reportValidity()) setConfirm(true)
                }}
              >
                <Icon name="check" />
                Confirm completion
              </button>
              <button
                className="button secondary full-width return-button"
                type="submit"
                disabled={stale || !response.trim() || operation.busy || Boolean(operation.pending)}
              >
                {operation.busy ? <Spinner /> : <Icon name="arrow" />}Return for changes
              </button>
            </form>
          ) : (
            <Notice tone="success">
              {session.state === 'COMPLETED'
                ? 'You confirmed completion. The learner’s work and your note are saved.'
                : 'This review is closed. The learner can continue with your feedback.'}
            </Notice>
          )}
        </aside>
      </div>
      {confirm && (
        <Dialog title="Confirm this task is complete?" onClose={() => setConfirm(false)}>
          <p className="dialog-description">
            This finishes the learner’s task. Your review note will be saved with their work.
          </p>
          <blockquote>{response}</blockquote>
          <OperationNotice operation={operation} />
          <footer className="dialog-actions">
            <button className="button quiet" onClick={() => setConfirm(false)}>
              Keep reviewing
            </button>
            <button
              className="button primary"
              disabled={operation.busy || stale || Boolean(operation.pending)}
              onClick={() => {
                void decide(true)
              }}
            >
              {operation.busy ? <Spinner /> : <Icon name="check" />}Confirm completion
            </button>
          </footer>
        </Dialog>
      )}
    </div>
  )
}
