import { useEffect, useId, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { safeSourceUrl } from './api'
import type {
  Activity,
  Attempt,
  Citation,
  Message,
  Reason,
  Session,
  SessionState,
  Task,
} from './types'

const paths = {
  arrow: 'M5 12h14m-6-6 6 6-6 6',
  chevron: 'm9 5 7 7-7 7',
  down: 'm6 9 6 6 6-6',
  task: 'M8 4h12v16H4V8m4-4v4H4m5 4h7m-7 4h7',
  inbox: 'M4 4h16v15H4V4Zm0 9h5l1 3h4l1-3h5',
  check: 'm5 12 4 4L19 6',
  close: 'm6 6 12 12M6 18 18 6',
  branch: 'M6 6v12m0-6h7a5 5 0 0 0 5-5M4 4h4v4H4V4Zm0 12h4v4H4v-4Zm12-13h4v4h-4V3Z',
  logout: 'M9 4H4v16h5m4-13 5 5-5 5m-4-5h10',
  chat: 'M20 11a8 8 0 0 1-8 8H4v-8a8 8 0 1 1 16 0ZM8 10h8m-8 4h5',
  code: 'm8 6-6 6 6 6m8-12 6 6-6 6m-3-15-2 18',
  external: 'M14 3h7v7m0-7L10 14m1-10H4v16h16v-7',
  refresh: 'M20 7v5h-5M4 17v-5h5m10-5a8 8 0 0 0-14-2m0 12a8 8 0 0 0 14 2',
  clock: 'M12 8v5l3 2m6-3a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
  plus: 'M12 5v14M5 12h14',
  eye: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Zm13 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z',
  menu: 'M4 6h16M4 12h16M4 18h16',
  file: 'M14 3H5v18h14V8l-5-5Zm0 0v5h5M9 13h6m-6 4h6',
  alert: 'M12 8v5m0 3v.1M12 3 2 21h20L12 3Z',
}
export function Icon({ name, size = 18 }: { name: keyof typeof paths; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.65"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  )
}
export function Mark({ small = false }: { small?: boolean }) {
  return (
    <span className={`brand-mark ${small ? 'small' : ''}`} aria-hidden="true">
      <svg viewBox="0 0 32 32" fill="none">
        <path d="m6 8 8 8-8 8" stroke="currentColor" strokeWidth="3" strokeLinejoin="round" />
        <path d="M17 24h10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      </svg>
    </span>
  )
}
export function Brand() {
  return (
    <span className="brand">
      <Mark />
      <span>RampUp</span>
    </span>
  )
}
export function Spinner({ label = 'Loading' }: { label?: string }) {
  return <span className="spinner" role="status" aria-label={label} />
}
export function Notice({
  children,
  tone = 'error',
  action,
}: {
  children: ReactNode
  tone?: 'error' | 'info' | 'success'
  action?: ReactNode
}) {
  return (
    <div className={`notice ${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
      <Icon name={tone === 'error' ? 'alert' : tone === 'success' ? 'check' : 'clock'} />
      <div>{children}</div>
      {action && <div className="notice-action">{action}</div>}
    </div>
  )
}
export function Empty({
  title,
  children,
  icon = 'inbox',
}: {
  title: string
  children: ReactNode
  icon?: keyof typeof paths
}) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Icon name={icon} size={25} />
      </span>
      <h2>{title}</h2>
      <p>{children}</p>
    </div>
  )
}
export function LoadingPage() {
  return (
    <div className="loading-page" role="status">
      <Spinner />
      <span>Getting your workspace ready…</span>
    </div>
  )
}
export function LoadError({ error, retry }: { error: string; retry: () => void }) {
  return (
    <div className="page">
      <Notice
        action={
          <button className="text-button" onClick={retry}>
            Try again
          </button>
        }
      >
        {error}
      </Notice>
    </div>
  )
}
export function OperationNotice({
  operation,
  blocked = false,
  onRetry,
}: {
  operation: {
    pending: { label: string } | null
    error: string
    busy: boolean
    saved: boolean
    retry: () => Promise<unknown>
  }
  blocked?: boolean
  onRetry?: () => void
}) {
  if (operation.busy || (!operation.error && !operation.pending)) return null
  return (
    <Notice
      tone={operation.saved ? 'info' : 'error'}
      action={
        operation.pending && (
          <button
            className="text-button"
            disabled={blocked || operation.busy}
            onClick={
              onRetry ||
              (() => {
                void operation.retry()
              })
            }
          >
            Retry original request
          </button>
        )
      }
    >
      {operation.error ||
        `An earlier ${operation.pending?.label || 'request'} hasn’t been confirmed. Retry it to safely recover the result.`}
    </Notice>
  )
}
export function Dialog({
  title,
  children,
  onClose,
  wide = false,
  drawer = false,
}: {
  title: string
  children: ReactNode
  onClose: () => void
  wide?: boolean
  drawer?: boolean
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const returnFocus = useRef<HTMLElement | null>(null)
  const id = useId()
  useEffect(() => {
    if (!returnFocus.current)
      returnFocus.current =
        document.activeElement instanceof HTMLElement ? document.activeElement : null
    const dialog = ref.current
    if (dialog && !dialog.open) dialog.showModal()
    dialog
      ?.querySelector<HTMLElement>(
        'input:not(:disabled), textarea:not(:disabled), select:not(:disabled)',
      )
      ?.focus()
    return () => {
      queueMicrotask(() => {
        if (returnFocus.current?.isConnected && !document.querySelector('dialog[open]'))
          returnFocus.current.focus()
      })
    }
  }, [])
  return (
    <dialog
      ref={ref}
      className={`${wide ? 'wide' : ''} ${drawer ? 'drawer' : ''}`}
      aria-labelledby={id}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          const box = event.currentTarget.getBoundingClientRect()
          if (
            event.clientX < box.left ||
            event.clientX > box.right ||
            event.clientY < box.top ||
            event.clientY > box.bottom
          )
            onClose()
        }
      }}
    >
      <div className="dialog-inner">
        <header className="dialog-heading">
          <h2 id={id}>{title}</h2>
          <button className="icon-button" aria-label="Close dialog" onClick={onClose}>
            <Icon name="close" />
          </button>
        </header>
        {children}
      </div>
    </dialog>
  )
}

export const stateNames: Record<SessionState, string> = {
  ACTIVE: 'In progress',
  WAITING_FOR_MENTOR: 'Waiting for your mentor',
  MENTOR_ACTIVE: 'Working with your mentor',
  COMPLETION_REVIEW: 'Ready for review',
  COMPLETED: 'Completed',
}
export const reasons: Record<Reason, string> = {
  MANUAL: 'Mentor requested',
  REPEATED_ATTEMPTS: 'Needs a different approach',
  MISSING_EVIDENCE: 'More context needed',
  SOURCE_CONFLICT: 'Sources disagree',
  PROTECTED_PATH: 'Protected file',
}
export function Status({ state }: { state: SessionState }) {
  return (
    <span className={`status state-${state.toLowerCase()}`}>
      <span />
      {stateNames[state]}
    </span>
  )
}
export function timeAgo(date: string) {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(date).getTime()) / 60000))
  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes} min ago`
  if (minutes < 1440) return `${Math.floor(minutes / 60)} hr ago`
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(
    new Date(date),
  )
}
export function Timestamp({ date }: { date: string }) {
  return (
    <time dateTime={date} title={new Date(date).toLocaleString()}>
      {timeAgo(date)}
    </time>
  )
}

export function CodeExcerpt({ source }: { source: Citation }) {
  return (
    <div className="source-excerpt">
      <div className="source-heading">
        <Icon name="file" />
        <span>{source.path}</span>
        <span className="mono">
          L{source.start_line}–{source.end_line}
        </span>
      </div>
      <pre tabIndex={0} aria-label={`Excerpt from ${source.path}`}>
        {source.excerpt.split('\n').map((line, index) => (
          <span className="code-line" key={index}>
            <span className="line-number" aria-hidden="true">
              {source.start_line + index}
            </span>
            <code>{line || ' '}</code>
          </span>
        ))}
      </pre>
      <footer>
        <span>
          Snapshot <code>{source.commit_sha.slice(0, 7)}</code>
        </span>
        {safeSourceUrl(source.url) && (
          <a href={safeSourceUrl(source.url)} target="_blank" rel="noopener noreferrer">
            View on GitHub <Icon name="external" size={13} />
          </a>
        )}
      </footer>
    </div>
  )
}
export function SourceDrawer({ source, close }: { source: Citation; close: () => void }) {
  return (
    <Dialog title="Repository evidence" onClose={close} drawer>
      <p className="muted drawer-intro">
        The exact excerpt used in this guidance, pinned to a repository snapshot.
      </p>
      <CodeExcerpt source={source} />
    </Dialog>
  )
}
export function Sources({ items }: { items: Citation[] }) {
  const [selected, setSelected] = useState<Citation | null>(null)
  if (!items.length) return null
  return (
    <>
      <div className="citations" aria-label="Sources">
        {items.map((source, index) => (
          <button
            className="citation"
            key={`${source.source_id}-${index}`}
            onClick={() => setSelected(source)}
          >
            <Icon name="file" size={14} />
            <span>{source.path.split('/').pop()}</span>
            <span className="citation-range">
              {source.start_line}–{source.end_line}
            </span>
            <Icon name="external" size={12} />
          </button>
        ))}
      </div>
      {selected && <SourceDrawer source={selected} close={() => setSelected(null)} />}
    </>
  )
}

export function AttemptCard({ attempt, number }: { attempt: Attempt; number?: number }) {
  const labels = {
    PROGRESS: 'Progress made',
    UNRESOLVED: 'Keep working',
    NEEDS_REVIEW: 'Needs review',
  }
  return (
    <details className="attempt-card">
      <summary>
        <span className="attempt-title">
          <Icon name="code" />
          <span>Attempt{number ? ` ${number}` : ''}</span>
        </span>
        <span className={`assessment assessment-${attempt.assessment.toLowerCase()}`}>
          {labels[attempt.assessment]}
        </span>
        <Icon name="down" size={15} />
      </summary>
      <div className="attempt-content">
        <p className="preserve">{attempt.explanation}</p>
        {attempt.file_paths.length > 0 && (
          <div className="file-paths">
            {attempt.file_paths.map((path) => (
              <code key={path}>{path}</code>
            ))}
          </div>
        )}
        {attempt.code && (
          <pre tabIndex={0}>
            <code>{attempt.code}</code>
          </pre>
        )}
        {attempt.test_output && (
          <>
            <h4>Learner-provided test output</h4>
            <pre tabIndex={0}>
              <code>{attempt.test_output}</code>
            </pre>
          </>
        )}
        {attempt.assessment_note && (
          <div className="assessment-note">
            <strong>Coach assessment</strong>
            <p>{attempt.assessment_note}</p>
          </div>
        )}
        <Timestamp date={attempt.created_at} />
      </div>
    </details>
  )
}
export function Conversation({
  messages,
  attempts = [],
  learnerName = 'You',
}: {
  messages: Message[]
  attempts?: Attempt[]
  learnerName?: string
}) {
  const entries = [
    ...messages.map((message) => ({ kind: 'message' as const, date: message.created_at, message })),
    ...attempts.map((attempt, index) => ({
      kind: 'attempt' as const,
      date: attempt.created_at,
      attempt,
      number: index + 1,
    })),
  ].sort((a, b) => a.date.localeCompare(b.date))
  return (
    <div className="conversation" role="log" aria-label="Conversation" aria-live="off">
      {entries.map((entry) => {
        if (entry.kind === 'attempt')
          return (
            <div className="attempt-entry" key={`attempt-${entry.attempt.id}`}>
              <AttemptCard attempt={entry.attempt} number={entry.number} />
            </div>
          )
        const message = entry.message
        if (message.author === 'SYSTEM')
          return (
            <div className="system-message" key={message.id}>
              <span />
              {message.content}
              <span />
            </div>
          )
        const name =
          message.author === 'AI' ? 'RampUp' : message.author === 'MENTOR' ? 'Mentor' : learnerName
        return (
          <article key={message.id} className={`message message-${message.author.toLowerCase()}`}>
            <div className="message-body">
              <header>
                <strong>
                  <span aria-hidden="true">&gt; </span>
                  {name}
                </strong>
                <Timestamp date={message.created_at} />
              </header>
              <div className="message-text">{message.content}</div>
              <Sources items={message.citations} />
            </div>
          </article>
        )
      })}
    </div>
  )
}
export function ActivityList({ activity }: { activity: Activity[] }) {
  if (!activity.length)
    return <p className="muted">Repository reads and coaching activity will appear here.</p>
  return (
    <ol className="activity-list">
      {[...activity].reverse().map((item) => (
        <li key={item.id}>
          <span className={`activity-dot ${item.status.toLowerCase()}`} />
          <div>
            <p>{item.summary}</p>
            <span>
              {item.tool.replaceAll('_', ' ')} · <Timestamp date={item.created_at} />
            </span>
          </div>
        </li>
      ))}
    </ol>
  )
}
export function TaskBrief({ task, session }: { task: Task; session?: Session }) {
  const [activityOpen, setActivityOpen] = useState(false)
  const mode = {
    HINTS: 'Progressive hints',
    CONCEPTS: 'Concept explanations',
    ATTEMPT_REVIEW: 'Attempt review',
  }[task.assistance_mode]
  return (
    <aside className="task-brief">
      <section>
        <h2>The task</h2>
        <p>{task.description}</p>
      </section>
      <section>
        <h3>Milestones</h3>
        {task.milestones.map((milestone, index) => (
          <div className="milestone" key={milestone.id}>
            <div className="milestone-heading">
              <span className="milestone-number">
                {session?.state === 'COMPLETED' ? (
                  <Icon name="check" size={12} />
                ) : (
                  String(index + 1).padStart(2, '0')
                )}
              </span>
              <strong>{milestone.title}</strong>
            </div>
            <ul className="criteria">
              {milestone.criteria.map((criterion) => (
                <li key={criterion}>
                  <span className="criterion-dot" />
                  {criterion}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </section>
      <section className="brief-policy">
        <h3>Task policy</h3>
        <p>
          <Icon name="chat" size={15} />
          {mode}
        </p>
        {task.protected_paths.length > 0 && (
          <>
            <span className="muted">Ask your mentor before changing</span>
            {task.protected_paths.map((path) => (
              <code className="protected-path" key={path}>
                {path}
              </code>
            ))}
          </>
        )}
      </section>
      <div className="brief-footnote">
        <Icon name="branch" size={15} />
        <span>
          Repository reads stay pinned to{' '}
          <code>{task.repository.commit_sha.slice(0, 7) || 'a snapshot'}</code>.
        </span>
      </div>
      {session && (
        <button className="text-button activity-link" onClick={() => setActivityOpen(true)}>
          <Icon name="clock" size={15} />
          View activity <span>{session.activity.length}</span>
        </button>
      )}
      {activityOpen && session && (
        <Dialog title="Workspace activity" onClose={() => setActivityOpen(false)}>
          <ActivityList activity={session.activity} />
        </Dialog>
      )}
    </aside>
  )
}
