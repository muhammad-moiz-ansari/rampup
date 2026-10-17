import type {
    Activity,
    Attempt,
    CaseSummary,
    Citation,
    DecisionAction,
    List,
    LoginResult,
    MentorCase,
    Message,
    Session,
    SessionSummary,
    Task,
    User,
} from './types'

const STORE_KEY = 'rampup.scripted-demo'
const now = () => new Date().toISOString()
const delay = (milliseconds: number) => new Promise((resolve) => setTimeout(resolve, milliseconds))

const schemaSource: Citation = {
    source_id: 'demo-schema',
    path: 'demo-repo/schemas.py',
    commit_sha: 'demo20261017',
    start_line: 8,
    end_line: 17,
    excerpt: 'class ItemCreate(BaseModel):\n    name: str = Field(min_length=1, max_length=120)\n    price: Decimal = Field(ge=0)\n    description: str | None = Field(default=None, max_length=500)\n\nclass QuantityUpdate(BaseModel):\n    quantity: int = Field(ge=0)',
    url: '',
}
const routeSource: Citation = {
    source_id: 'demo-route',
    path: 'demo-repo/routes.py',
    commit_sha: 'demo20261017',
    start_line: 21,
    end_line: 31,
    excerpt: '@router.post("/items", response_model=ItemRead)\ndef create_item(payload: ItemCreate, service: ItemService = Depends(get_service)):\n    item = service.create(payload)\n    return ItemRead.model_validate(item)\n\n@router.patch("/items/{item_id}/quantity")\ndef update_quantity(item_id: int, payload: QuantityUpdate):\n    return service.update_quantity(item_id, payload.quantity)',
    url: '',
}
const readmeSource: Citation = {
    source_id: 'demo-readme',
    path: 'demo-repo/README.md',
    commit_sha: 'demo20261017',
    start_line: 32,
    end_line: 36,
    excerpt: 'For new endpoints, validate request values in the route before calling the service.\nKeep validation close to the HTTP handler so each route can decide what to accept.\n\nNote: this onboarding section has not been updated with the current schema pattern.',
    url: '',
}

export const TASK_ONE_SCRIPT = [
    {
        question: 'Where should I add the description?',
        response: 'Start in schemas.py. ItemCreate is the request boundary; then check routes.py to see the same model passed to the create service and returned as ItemRead.',
    },
    {
        question: 'What validation pattern should I follow?',
        response: 'Add the optional field beside the existing name and price fields in ItemCreate. Use a nullable string with a default of None and max_length=500; the route already passes that model through to creation.',
    },
] as const

export const TASK_ONE_SAMPLE_ATTEMPT = {
    explanation: 'Add description as an optional string with a 500-character maximum. Keep the existing name and price validation unchanged, and include description in the ItemRead response.',
    code: 'description: str | None = Field(default=None, max_length=500)',
    file_paths: ['demo-repo/schemas.py', 'demo-repo/routes.py'],
}

export function taskOneQuestionCount(messages: Message[]) {
    const scriptedQuestions = new Set(TASK_ONE_SCRIPT.map((item) => item.question.toLowerCase()))
    return messages.filter(
        (message) => message.author === 'LEARNER' && scriptedQuestions.has(message.content.trim().toLowerCase()),
    ).length
}

const tasks: Task[] = [
    {
        id: 'demo-task-1',
        title: 'Add optional item descriptions',
        description:
            'Problem: Item creation needs an optional description, limited to 500 characters.\n\nGoal: Extend the request and response while preserving existing name and price validation. The AI coach has the current implementation pattern for this task.\n\nCode structure:\ndemo-repo/\n|-- schemas.py  Request models and field validation\n|-- routes.py   HTTP endpoint and response mapping\n\\-- auth.py     Protected authentication boundary',
        repository: { owner: 'RampUp demo', name: 'inventory-api', commit_sha: 'demo20261017' },
        assistance_mode: 'CONCEPTS',
        protected_paths: ['demo-repo/auth.py'],
        attempt_threshold: 3,
        milestones: [
            {
                id: 'optional-description',
                title: 'Extend item creation safely',
                criteria: [
                    'Make description optional and limit it to 500 characters',
                    'Preserve the existing name and price constraints',
                    'Return the supplied description from the create endpoint',
                ],
            },
        ],
    },
    {
        id: 'demo-task-2',
        title: 'Add inventory quantity updates',
        description:
            'Problem: Add an endpoint to update an item’s stock quantity. The onboarding README recommends route-level validation, while current code validates requests with Pydantic schemas.\n\nGoal: Propose a non-negative integer quantity update, explain how missing items are handled, and keep authentication unchanged. The sources disagree, so a mentor will resolve the design choice.\n\nCode structure:\ndemo-repo/\n|-- README.md       Older onboarding guidance\n|-- schemas.py      Current request validation\n|-- routes.py       HTTP endpoints\n|-- service.py      Item lookup\n\\-- auth.py         Protected authentication boundary',
        repository: { owner: 'RampUp demo', name: 'inventory-api', commit_sha: 'demo20261017' },
        assistance_mode: 'HINTS',
        protected_paths: ['demo-repo/auth.py'],
        attempt_threshold: 3,
        milestones: [
            {
                id: 'quantity-update',
                title: 'Design quantity validation and routing',
                criteria: [
                    'Identify the conflict between the README and current schema pattern',
                    'Represent and validate a non-negative integer quantity',
                    'Keep lookup in the service and preserve authentication',
                ],
            },
        ],
    },
]

interface DemoStore {
    sessions: Record<string, Session>
    cases: Record<string, MentorCase>
}

function readStore(): DemoStore {
    try {
        const parsed = JSON.parse(localStorage.getItem(STORE_KEY) || '{}') as Partial<DemoStore>
        const store = { sessions: parsed.sessions || {}, cases: parsed.cases || {} }
        let changed = false
        for (const session of Object.values(store.sessions)) {
            for (const message of session.messages || []) {
                if (message.content.startsWith('Scripted check:')) {
                    message.content = message.content.replace(/^Scripted check:\s*/, 'Review: ')
                    changed = true
                }
            }
            for (const attempt of session.attempts || []) {
                if (attempt.assessment_note.startsWith('Scripted check:')) {
                    attempt.assessment_note = attempt.assessment_note.replace(/^Scripted check:\s*/, 'Review: ')
                    changed = true
                }
            }
        }
        if (changed) saveStore(store)
        return store
    } catch {
        return { sessions: {}, cases: {} }
    }
}

function saveStore(store: DemoStore) {
    localStorage.setItem(STORE_KEY, JSON.stringify(store))
}

function userForRole(role: 'LEARNER' | 'MENTOR'): User {
    return {
        id: `demo-${role.toLowerCase()}`,
        name: role === 'LEARNER' ? 'Demo Learner' : 'Demo Mentor',
        role,
    }
}

function sessionIdForTask(taskId: string) {
    return `${taskId}-${crypto.randomUUID()}`
}

function makeMessage(author: Message['author'], content: string, citations: Citation[] = []): Message {
    return { id: crypto.randomUUID(), author, content, citations, created_at: now() }
}

function makeActivity(tool: string, summary: string): Activity {
    return { id: crypto.randomUUID(), tool, summary, status: 'SUCCEEDED', created_at: now() }
}

function makeSession(task: Task, id: string): Session {
    return {
        id,
        task_id: task.id,
        task,
        state: 'ACTIVE',
        current_milestone_id: task.milestones[0].id,
        version: 1,
        messages: [],
        attempts: [],
        activity: [],
        open_escalation: null,
        latest_run: null,
        updated_at: now(),
    }
}

function findSession(store: DemoStore, id: string) {
    const session = store.sessions[id]
    if (!session) throw new Error('That demo session no longer exists. Open the task again.')
    return session
}

function createCase(session: Session, reason: 'SOURCE_CONFLICT' | 'MANUAL', question: string, evidence: Citation[]) {
    const detail: MentorCase = {
        id: crypto.randomUUID(),
        session_id: session.id,
        task_title: session.task.title,
        learner_name: 'Demo Learner',
        reason,
        status: 'OPEN',
        revision: 1,
        created_at: now(),
        learner_question: question,
        milestone_id: session.current_milestone_id,
        summary:
            reason === 'SOURCE_CONFLICT'
                ? 'The onboarding README directs validation into the route, but the current implementation validates request data in Pydantic schemas. The learner needs a mentor to confirm which convention to follow.'
                : 'The learner requested a mentor review and included their current question.',
        unresolved_question: question,
        evidence,
        attempts: [...session.attempts],
        prior_hints: session.messages.filter((message) => message.author === 'AI'),
        proposed_guidance:
            'Follow the current code: add a QuantityUpdate Pydantic model in schemas.py with quantity: int = Field(ge=0). Keep the route thin, call the service for the update, and let the existing not-found handling map a missing item to 404. Leave auth.py unchanged.',
        mentor_messages: [],
    }
    session.open_escalation = detail
    session.state = 'WAITING_FOR_MENTOR'
    session.version++
    session.updated_at = now()
    session.activity.push(makeActivity('open_mentor_case', 'Opened a mentor case with the conflicting sources.'))
    return detail
}

function reviewTaskOneAttempt(body: Record<string, unknown>) {
    const explanation = String(body.explanation || '')
    const code = String(body.code || '')
    const text = `${explanation}\n${code}`
    const paths = Array.isArray(body.file_paths) ? body.file_paths.map(String) : []
    const criteria = [
        {
            met: /description/i.test(text) && /\b(optional|nullable|null|none)\b|str\s*\|\s*none/i.test(text),
            label: 'describe description as optional',
        },
        {
            met: /max_length\s*=\s*500|\b500[\s-]*(?:character|char)/i.test(text),
            label: 'set the 500-character limit',
        },
        {
            met: /\bname\b/i.test(text) && /\bprice\b/i.test(text) && /\b(preserv\w*|keep|retain\w*|unchanged)\b/i.test(text),
            label: 'preserve the existing name and price rules',
        },
        {
            met: /\bdescription\b.{0,80}\b(itemread|response|return(?:ed)?)\b|\b(itemread|response|return(?:ed)?)\b.{0,80}\bdescription\b/i.test(text),
            label: 'include the description in the create response',
        },
    ]
    const missing = criteria.filter((criterion) => !criterion.met).map((criterion) => criterion.label)
    return {
        passed: missing.length === 0,
        note: missing.length
            ? `Review your work: ${missing.join('; ')}.`
            : 'Your explanation and code cover all four task criteria.',
    }
}

function messageSession(store: DemoStore, id: string, body: Record<string, unknown>) {
    const session = findSession(store, id)
    const content = String(body.content || '').trim()
    if (!content) throw new Error('Write a question before sending.')
    if (session.task_id === 'demo-task-1') {
        const expected = TASK_ONE_SCRIPT[taskOneQuestionCount(session.messages)]
        if (!expected || content.toLowerCase() !== expected.question.toLowerCase()) {
            throw new Error('Choose the next question shown in the workspace.')
        }
    }
    session.messages.push(makeMessage('LEARNER', content))
    session.version++
    session.updated_at = now()
    if (session.state !== 'ACTIVE') {
        session.messages.push(makeMessage('SYSTEM', 'Your note was added to the mentor case.'))
    } else if (session.task_id === 'demo-task-2') {
        const reply = 'I found conflicting guidance: the README says to validate in the route, while the current schema uses Pydantic field constraints. I won’t guess which convention your team wants. I’ve opened a mentor case with both excerpts so they can decide.'
        session.messages.push(makeMessage('AI', reply, [readmeSource, schemaSource]))
        session.activity.push(makeActivity('search_project_context', 'Found the older README and current schema pattern.'))
        session.activity.push(makeActivity('open_mentor_case', 'Escalated the unresolved source conflict to your mentor.'))
        const detail = createCase(session, 'SOURCE_CONFLICT', content, [readmeSource, schemaSource])
        store.cases[detail.id] = detail
    } else {
        const reply = TASK_ONE_SCRIPT[taskOneQuestionCount(session.messages) - 1].response
        session.messages.push(makeMessage('AI', reply, [schemaSource, routeSource]))
        session.activity.push(makeActivity('search_project_context', 'Found the request schema and create-route example.'))
    }
    session.updated_at = now()
    saveStore(store)
    return session
}

function submitAttempt(store: DemoStore, id: string, body: Record<string, unknown>) {
    const session = findSession(store, id)
    if (session.task_id === 'demo-task-1' && taskOneQuestionCount(session.messages) < TASK_ONE_SCRIPT.length) {
        throw new Error('Answer both questions before sharing your work.')
    }
    const taskOneReview = session.task_id === 'demo-task-1' ? reviewTaskOneAttempt(body) : null
    const attempt: Attempt = {
        id: crypto.randomUUID(),
        milestone_id: session.current_milestone_id,
        explanation: String(body.explanation || ''),
        code: String(body.code || ''),
        file_paths: Array.isArray(body.file_paths) ? body.file_paths.map(String) : [],
        test_output: typeof body.test_output === 'string' ? body.test_output : null,
        assessment: taskOneReview ? (taskOneReview.passed ? 'PROGRESS' : 'UNRESOLVED') : 'NEEDS_REVIEW',
        assessment_note:
            taskOneReview
                ? taskOneReview.note
                : 'Your mentor can review this implementation against the agreed validation convention.',
        created_at: now(),
    }
    session.attempts.push(attempt)
    if (session.task_id === 'demo-task-1') {
        session.messages.push(makeMessage(
            'AI',
            taskOneReview!.passed
                ? 'Your work meets the task criteria. Task complete.'
                : taskOneReview!.note,
            [schemaSource, routeSource],
        ))
        if (taskOneReview!.passed) session.state = 'COMPLETED'
    } else if (session.messages.some((message) => message.author === 'MENTOR')) {
        session.messages.push(
            makeMessage('AI', 'Your revised attempt is saved. The agreed schema, service, and protected-auth boundaries are all represented; I’ve sent it to your mentor for the final completion check.', [schemaSource, routeSource]),
        )
        session.state = 'COMPLETION_REVIEW'
    } else {
        session.messages.push(makeMessage('AI', 'I’ve saved your attempt, but the source conflict still needs your mentor’s decision before I can review the design.'))
    }
    session.version++
    session.updated_at = now()
    session.activity.push(makeActivity('review_attempt', 'Saved the learner’s implementation for review.'))
    saveStore(store)
    return session
}

function summaries(store: DemoStore, status?: string): CaseSummary[] {
    return Object.values(store.cases)
        .filter((item) => !status || item.status === status)
        .map(({ id, session_id, task_title, learner_name, reason, revision, created_at, status: caseStatus }) => ({
            id,
            session_id,
            task_title,
            learner_name,
            reason,
            revision,
            created_at,
            status: caseStatus,
        }))
}

function completionReviews(store: DemoStore): SessionSummary[] {
    return Object.values(store.sessions)
        .filter((session) => session.state === 'COMPLETION_REVIEW')
        .map((session) => ({
            id: session.id,
            task_title: session.task.title,
            learner_name: 'Demo Learner',
            state: session.state,
            version: session.version,
            updated_at: session.updated_at,
        }))
}

function post(store: DemoStore, path: string, body: Record<string, unknown>): unknown {
    if (path === '/auth/demo-login' || path === '/auth/login') {
        const role = body.role === 'MENTOR' || String(body.email || '').toLowerCase().includes('mentor')
            ? 'MENTOR'
            : 'LEARNER'
        const user = userForRole(role)
        return {
            access_token: `demo-${role.toLowerCase()}`,
            token_type: 'bearer',
            expires_at: new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString(),
            user,
        } satisfies LoginResult
    }
    if (path === '/sessions') {
        const task = tasks.find((item) => item.id === body.task_id)
        if (!task) throw new Error('That demo task was not found.')
        const id = sessionIdForTask(task.id)
        const session = makeSession(task, id)
        const updated = readStore()
        updated.sessions[id] = session
        saveStore(updated)
        return session
    }
    const messageMatch = /^\/sessions\/([^/]+)\/(messages|attempts|escalations|completion-request|completion-decision)$/.exec(path)
    if (messageMatch) {
        const [, id, action] = messageMatch
        if (action === 'messages') return messageSession(store, id, body)
        const session = findSession(store, id)
        if (action === 'attempts') return submitAttempt(store, id, body)
        if (action === 'escalations') {
            const question = String(body.question || 'I would like a second opinion on this task.')
            session.messages.push(makeMessage('LEARNER', question))
            const detail = createCase(
                session,
                'MANUAL',
                question,
                session.task_id === 'demo-task-2' ? [readmeSource, schemaSource] : [schemaSource],
            )
            store.cases[detail.id] = detail
            saveStore(store)
            return session
        }
        if (action === 'completion-request') {
            session.state = 'COMPLETION_REVIEW'
            session.version++
            session.updated_at = now()
            session.messages.push(makeMessage('SYSTEM', 'The learner requested a completion review.'))
            saveStore(store)
            return session
        }
        const approved = body.approved === true
        session.messages.push(makeMessage('MENTOR', String(body.text || (approved ? 'Task complete.' : 'Please revisit the requested changes.'))))
        session.state = approved ? 'COMPLETED' : 'ACTIVE'
        session.version++
        session.updated_at = now()
        saveStore(store)
        return session
    }
    const caseDecision = /^\/escalations\/([^/]+)\/decision$/.exec(path)
    if (caseDecision) {
        const detail = store.cases[caseDecision[1]]
        if (!detail) throw new Error('This mentor case was not found.')
        const session = findSession(store, detail.session_id)
        const action = body.action as DecisionAction
        const text = String(body.text || '')
        detail.mentor_messages.push(makeMessage('MENTOR', text))
        detail.revision++
        if (action === 'SEND_GUIDANCE' || action === 'TAKE_OVER') {
            detail.status = 'RESOLVED'
            session.open_escalation = null
            session.state = 'ACTIVE'
            session.messages.push(makeMessage('MENTOR', text))
        } else if (action === 'ASK_QUESTION') {
            session.messages.push(makeMessage('MENTOR', text))
        }
        session.version++
        session.updated_at = now()
        session.activity.push(makeActivity('mentor_decision', 'Mentor reviewed the case and sent guidance.'))
        saveStore(store)
        return session
    }
    throw new Error(`No demo response is available for ${path}.`)
}

function get(store: DemoStore, path: string): unknown {
    if (path === '/auth/me') {
        const role = sessionStorage.getItem('rampup.token')?.includes('mentor') ? 'MENTOR' : 'LEARNER'
        return userForRole(role)
    }
    if (path === '/tasks') return { items: tasks } satisfies List<Task>
    const taskMatch = /^\/tasks\/([^/]+)$/.exec(path)
    if (taskMatch) {
        const task = tasks.find((item) => item.id === taskMatch[1])
        if (!task) throw new Error('That demo task was not found.')
        return task
    }
    const sessionMatch = /^\/sessions\/([^/]+)$/.exec(path)
    if (sessionMatch) return findSession(store, sessionMatch[1])
    if (path.startsWith('/mentor/escalations')) {
        const status = new URLSearchParams(path.split('?')[1] || '').get('status') || undefined
        return { items: summaries(store, status) } satisfies List<CaseSummary>
    }
    if (path === '/mentor/completion-reviews') return { items: completionReviews(store) } satisfies List<SessionSummary>
    const caseMatch = /^\/escalations\/([^/]+)$/.exec(path)
    if (caseMatch) {
        const detail = store.cases[caseMatch[1]]
        if (!detail) throw new Error('This mentor case was not found.')
        return detail
    }
    throw new Error(`No demo response is available for ${path}.`)
}

export async function demoRequest<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
    const wait = method === 'GET' ? 180 : path.endsWith('/messages') || path.endsWith('/attempts') || path.endsWith('/decision') ? 1250 : 450
    await delay(wait)
    const store = readStore()
    const result = method === 'GET' ? get(store, path) : post(store, path, (body || {}) as Record<string, unknown>)
    return result as T
}