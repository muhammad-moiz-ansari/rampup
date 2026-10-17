import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { api, ApiError, errorMessage } from './api'
import { useResource } from './hooks'
import { LearnerWorkspace } from './Learner'
import { CompletionReview, MentorQueue, MentorReview } from './Mentor'
import type { List, LoginResult, Session, Task, User } from './types'
import {
  Brand,
  Dialog,
  Empty,
  Icon,
  LoadError,
  LoadingPage,
  Notice,
  Spinner,
  TaskBrief,
} from './ui'

function useHash() {
  const [path, setPath] = useState(() => window.location.hash.slice(1) || '/')
  useEffect(() => {
    const update = () => {
      setPath(window.location.hash.slice(1) || '/')
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', update)
    return () => window.removeEventListener('hashchange', update)
  }, [])
  return path
}
function navigate(path: string) {
  window.location.hash = path
}
function clearToken() {
  sessionStorage.removeItem('rampup.token')
  sessionStorage.removeItem('rampup.expires')
}

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [booting, setBooting] = useState(Boolean(sessionStorage.getItem('rampup.token')))
  const [authError, setAuthError] = useState('')
  const [expired, setExpired] = useState(false)
  const path = useHash()
  const restore = useCallback(async () => {
    if (!sessionStorage.getItem('rampup.token')) {
      setBooting(false)
      return
    }
    const expires = sessionStorage.getItem('rampup.expires')
    if (expires && Date.parse(expires) <= Date.now()) {
      clearToken()
      setExpired(true)
      setBooting(false)
      return
    }
    setBooting(true)
    setAuthError('')
    try {
      setUser(await api.get<User>('/auth/me'))
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 401)) setAuthError(errorMessage(error))
    } finally {
      setBooting(false)
    }
  }, [])
  useEffect(() => {
    void restore()
  }, [restore])
  useEffect(() => {
    const reset = () => {
      clearToken()
      setUser(null)
      setExpired(true)
      setAuthError('')
    }
    window.addEventListener('rampup:expired', reset)
    return () => window.removeEventListener('rampup:expired', reset)
  }, [])
  useEffect(() => {
    if (user && path === '/') navigate(user.role === 'MENTOR' ? '/reviews' : '/tasks')
  }, [user, path])
  function loggedIn(result: LoginResult) {
    sessionStorage.setItem('rampup.token', result.access_token)
    sessionStorage.setItem('rampup.expires', result.expires_at)
    setUser(result.user)
    setExpired(false)
    setAuthError('')
    navigate(result.user.role === 'MENTOR' ? '/reviews' : '/tasks')
  }
  if (booting)
    return (
      <div className="auth-loading">
        <Brand />
        <LoadingPage />
      </div>
    )
  if (!user && authError)
    return (
      <div className="auth-recovery">
        <Brand />
        <h1>Let’s reconnect.</h1>
        <Notice
          action={
            <button
              className="text-button"
              onClick={() => {
                void restore()
              }}
            >
              Try again
            </button>
          }
        >
          {authError}
        </Notice>
        <button
          className="button secondary"
          onClick={() => {
            clearToken()
            setAuthError('')
          }}
        >
          Back to sign in
        </button>
      </div>
    )
  if (!user) return <Login onLogin={loggedIn} expired={expired} />
  let content: ReactNode
  if (path.startsWith('/session/'))
    content =
      user.role === 'LEARNER' ? (
        <LearnerWorkspace key={path} id={path.slice(9)} user={user} />
      ) : (
        <NotFound role={user.role} />
      )
  else if (path.startsWith('/review/'))
    content =
      user.role === 'MENTOR' ? (
        <MentorReview key={path} id={path.slice(8)} user={user} />
      ) : (
        <NotFound role={user.role} />
      )
  else if (path.startsWith('/completion/'))
    content =
      user.role === 'MENTOR' ? (
        <CompletionReview key={path} id={path.slice(12)} user={user} />
      ) : (
        <NotFound role={user.role} />
      )
  else if (path === '/reviews' && user.role === 'MENTOR') content = <MentorQueue key="cases" />
  else if (path === '/completions' && user.role === 'MENTOR')
    content = <MentorQueue key="completions" completed />
  else if (path === '/tasks' || path === '/') content = <Tasks user={user} />
  else if (path.startsWith('/task/'))
    content = <TaskDetails key={path} id={path.slice(6)} user={user} />
  else content = <NotFound role={user.role} />
  return (
    <Shell
      user={user}
      path={path}
      logout={() => {
        clearToken()
        setUser(null)
        setExpired(false)
        navigate('/')
      }}
    >
      {content}
    </Shell>
  )
}

function Login({ onLogin, expired }: { onLogin: (result: LoginResult) => void; expired: boolean }) {
  const [busy, setBusy] = useState(false)
  async function startDemo(role: 'LEARNER' | 'MENTOR') {
    setBusy(true)
    try {
      onLogin(await api.post<LoginResult>('/auth/demo-login', { role }))
    } finally {
      setBusy(false)
    }
  }
  return (
    <main className="login-page">
      <section className="login-story">
        <Brand />
        <div className="login-story-content">
          <h1>
            Get into
            <br />
            the code.
            <span className="terminal-cursor" aria-hidden="true" />
          </h1>
          <p>
            Repository context. Guided practice.
            <br />A mentor when you need one.
          </p>
          <pre className="login-terminal" aria-hidden="true">
            {'$ rampup start\n> read the context\n> try a change\n> get feedback'}
          </pre>
        </div>
      </section>
      <section className="login-form-side">
        <div className="login-form-wrap">
          <div className="login-mini-brand">
            <Brand />
          </div>
          <h2>Choose a demo role</h2>
          <p className="login-description">Choose a role to enter the learning workspace.</p>
          {expired && (
            <Notice tone="info">Choose a role to continue the saved demo.</Notice>
          )}
          <div className="demo-role-actions">
            <button className="button primary full-width" disabled={busy} onClick={() => void startDemo('LEARNER')}>
              {busy ? <Spinner label="Opening learner demo" /> : <Icon name="task" />}
              Enter as learner
              {!busy && <Icon name="arrow" />}
            </button>
            <button className="button secondary full-width" disabled={busy} onClick={() => void startDemo('MENTOR')}>
              {busy ? <Spinner label="Opening mentor demo" /> : <Icon name="inbox" />}
              Enter as mentor
              {!busy && <Icon name="arrow" />}
            </button>
          </div>
        </div>
      </section>
    </main>
  )
}

function Shell({
  user,
  path,
  logout,
  children,
}: {
  user: User
  path: string
  logout: () => void
  children: ReactNode
}) {
  const [menu, setMenu] = useState(false)
  const mentor = user.role === 'MENTOR'
  const links = mentor
    ? [
      {
        href: '/reviews',
        label: 'Review queue',
        icon: 'inbox' as const,
        active: path.startsWith('/review'),
      },
      {
        href: '/completions',
        label: 'Completion reviews',
        icon: 'check' as const,
        active: path.startsWith('/completion'),
      },
      {
        href: '/tasks',
        label: 'Assigned tasks',
        icon: 'task' as const,
        active: path.startsWith('/task'),
      },
    ]
    : [
      {
        href: '/tasks',
        label: 'My tasks',
        icon: 'task' as const,
        active: path.startsWith('/task') || path.startsWith('/session'),
      },
    ]
  function navigation() {
    return (
      <>
        <nav aria-label="Main navigation">
          {links.map((link) => (
            <a
              key={link.href}
              href={`#${link.href}`}
              className={`nav-link ${link.active ? 'active' : ''}`}
              aria-current={link.active ? 'page' : undefined}
              onClick={(event) => {
                event.preventDefault()
                navigate(link.href)
                setMenu(false)
              }}
            >
              <Icon name={link.icon} />
              <span>{link.label}</span>
              {link.active && <span className="nav-indicator" />}
            </a>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="profile">
            <span className="profile-avatar">
              {user.name
                .split(' ')
                .map((word) => word[0])
                .slice(0, 2)
                .join('')}
            </span>
            <div>
              <strong>{user.name}</strong>
              <span>{mentor ? 'Mentor' : 'Learner'}</span>
            </div>
            <button className="icon-button" aria-label="Sign out" onClick={logout}>
              <Icon name="logout" size={17} />
            </button>
          </div>
        </div>
      </>
    )
  }
  return (
    <div className="app-shell">
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault()
          document.getElementById('main-content')?.focus()
        }}
      >
        Skip to content
      </a>
      <aside className="sidebar">
        <a
          className="sidebar-brand"
          href={`#${mentor ? '/reviews' : '/tasks'}`}
          aria-label="RampUp home"
        >
          <Brand />
        </a>
        {navigation()}
      </aside>
      <div className="app-main">
        <header className="app-topbar">
          <div className="mobile-brand">
            <Brand />
          </div>
          <span className="topbar-location">
            <span className="workspace-glyph">
              <Icon name={mentor ? 'inbox' : 'task'} size={15} />
            </span>
            {mentor ? 'Mentor workspace' : 'Learning workspace'}
          </span>
          <span className="demo-mode">DEMO</span>
          <button
            className="icon-button mobile-menu"
            aria-label="Open navigation"
            onClick={() => setMenu(true)}
          >
            <Icon name="menu" />
          </button>
        </header>
        <main id="main-content" tabIndex={-1}>
          {children}
        </main>
      </div>
      {menu && (
        <Dialog title="Your workspace" onClose={() => setMenu(false)}>
          <div className="mobile-navigation">{navigation()}</div>
        </Dialog>
      )}
    </div>
  )
}

function Tasks({ user }: { user: User }) {
  const load = useCallback(() => api.get<List<Task>>('/tasks'), [])
  const resource = useResource(load)
  const [opening, setOpening] = useState(''),
    [error, setError] = useState('')
  const keys = useRef(new Map<string, string>()),
    lock = useRef(false)
  async function openTask(task: Task) {
    if (lock.current) return
    lock.current = true
    setOpening(task.id)
    setError('')
    const key = keys.current.get(task.id) || crypto.randomUUID()
    keys.current.set(task.id, key)
    try {
      const session = await api.post<Session>('/sessions', { task_id: task.id }, key)
      keys.current.delete(task.id)
      navigate(`/session/${session.id}`)
    } catch (failure) {
      setError(errorMessage(failure))
    } finally {
      lock.current = false
      setOpening('')
    }
  }
  if (!resource.data)
    return resource.error ? (
      <LoadError error={resource.error} retry={resource.refresh} />
    ) : (
      <LoadingPage />
    )
  const tasks = resource.data.items,
    mentor = user.role === 'MENTOR'
  return (
    <div className="page tasks-page">
      <header className="page-heading">
        <div>
          <h1>{mentor ? 'Assigned tasks' : 'Your tasks'}</h1>
        </div>
        <span className="task-count">
          {tasks.length} {tasks.length === 1 ? 'task' : 'tasks'}
        </span>
      </header>
      {error && <Notice>{error} Open the task again to retry the same request.</Notice>}
      {!tasks.length ? (
        <Empty title="No tasks assigned" icon="task">
          Your team’s assigned tasks will appear here.
        </Empty>
      ) : (
        <div className="task-list">
          {tasks.map((task, index) => (
            <article className="task-row" key={task.id}>
              <span className="task-index">{String(index + 1).padStart(2, '0')}</span>
              <div className="task-row-main">
                <div className="task-row-top">
                  <span className="task-repository">
                    <Icon name="branch" size={14} />
                    {task.repository.name}
                  </span>
                  <span className="task-mode">
                    {
                      {
                        HINTS: 'Progressive hints',
                        CONCEPTS: 'Concepts',
                        ATTEMPT_REVIEW: 'Attempt review',
                      }[task.assistance_mode]
                    }
                  </span>
                </div>
                <h2>
                  <a href={`#/task/${task.id}`}>{task.title}</a>
                </h2>
                <p>{taskSummary(task.description)}</p>
                <div className="task-row-bottom">
                  <span>
                    <Icon name="task" size={14} />
                    {task.milestones.length}{' '}
                    {task.milestones.length === 1 ? 'milestone' : 'milestones'}
                  </span>
                  <a href={`#/task/${task.id}`}>
                    View task details <Icon name="chevron" size={13} />
                  </a>
                </div>
              </div>
              <div className="task-row-action">
                {mentor ? (
                  <a className="button secondary" href={`#/task/${task.id}`}>
                    View task <Icon name="arrow" />
                  </a>
                ) : (
                  <button
                    className="button primary"
                    disabled={Boolean(opening)}
                    onClick={() => {
                      void openTask(task)
                    }}
                  >
                    {opening === task.id ? <Spinner /> : null}
                    {opening === task.id ? 'Opening…' : 'Open workspace'}
                    {!opening && <Icon name="arrow" />}
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}

function taskSummary(description: string) {
  const firstBlock = description.split(/\n\s*\n/, 1)[0].trim()
  return firstBlock.replace(/^Problem:\s*/i, '')
}

function TaskDetails({ id, user }: { id: string; user: User }) {
  const load = useCallback(() => api.get<Task>(`/tasks/${id}`), [id])
  const resource = useResource(load)
  const [busy, setBusy] = useState(false),
    [error, setError] = useState('')
  const key = useRef(crypto.randomUUID())
  if (!resource.data)
    return resource.error ? (
      <LoadError error={resource.error} retry={resource.refresh} />
    ) : (
      <LoadingPage />
    )
  const task = resource.data
  return (
    <div className="page task-detail-page">
      <header className="page-heading">
        <div>
          <a className="back-link" href="#/tasks">
            <Icon name="arrow" />
            Assigned tasks
          </a>
          <h1>{task.title}</h1>
          <div className="repository">
            <Icon name="branch" size={15} />
            {task.repository.owner} / {task.repository.name}
          </div>
        </div>
      </header>
      {error && <Notice>{error}</Notice>}
      <div className="task-details-layout">
        <details className="task-description-disclosure" open>
          <summary>
            <span>
              <strong>Task brief</strong>
              <small>Problem, goal, code structure, and acceptance criteria</small>
            </span>
            <Icon name="down" />
          </summary>
          <TaskBrief task={task} />
        </details>
        <aside className="task-start-panel">
          <Icon name="task" size={27} />
          <h2>{user.role === 'LEARNER' ? 'Start task' : 'Task details'}</h2>
          <p>
            {user.role === 'LEARNER'
              ? 'Ask a question, share an approach, or bring your mentor in. Your workspace keeps the thread together.'
              : 'These are the criteria and boundaries the learner is working with. Task settings are managed by your team.'}
          </p>
          {user.role === 'LEARNER' && (
            <button
              className="button primary"
              disabled={busy}
              onClick={() => {
                if (busy) return
                setBusy(true)
                void api
                  .post<Session>('/sessions', { task_id: id }, key.current)
                  .then((session) => navigate(`/session/${session.id}`))
                  .catch((failure) => setError(errorMessage(failure)))
                  .finally(() => setBusy(false))
              }}
            >
              {busy ? <Spinner /> : <Icon name="arrow" />}Open workspace
            </button>
          )}
          {user.role === 'MENTOR' && (
            <a className="button secondary" href="#/reviews">
              Go to review queue <Icon name="arrow" />
            </a>
          )}
        </aside>
      </div>
    </div>
  )
}
function NotFound({ role }: { role: User['role'] }) {
  return (
    <div className="page">
      <Empty title="That page isn’t here." icon="file">
        Return to your workspace to find the task or review you need.
      </Empty>
      <a className="button secondary" href={`#${role === 'MENTOR' ? '/reviews' : '/tasks'}`}>
        Back to your workspace <Icon name="arrow" />
      </a>
    </div>
  )
}
