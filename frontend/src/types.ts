export type Role = 'LEARNER' | 'MENTOR'
export type SessionState =
  'ACTIVE' | 'WAITING_FOR_MENTOR' | 'MENTOR_ACTIVE' | 'COMPLETION_REVIEW' | 'COMPLETED'
export type Reason =
  'MANUAL' | 'REPEATED_ATTEMPTS' | 'MISSING_EVIDENCE' | 'SOURCE_CONFLICT' | 'PROTECTED_PATH'
export type DecisionAction = 'SEND_GUIDANCE' | 'ASK_QUESTION' | 'TAKE_OVER' | 'REJECT_SUGGESTION'
export interface User {
  id: string
  name: string
  role: Role
}
export interface LoginResult {
  access_token: string
  token_type: 'bearer'
  expires_at: string
  user: User
}
export interface Citation {
  source_id: string
  path: string
  commit_sha: string
  start_line: number
  end_line: number
  excerpt: string
  url: string
}
export interface Milestone {
  id: string
  title: string
  criteria: string[]
}
export interface Task {
  id: string
  title: string
  description: string
  repository: { owner: string; name: string; commit_sha: string }
  assistance_mode: 'HINTS' | 'CONCEPTS' | 'ATTEMPT_REVIEW'
  protected_paths: string[]
  attempt_threshold: number
  milestones: Milestone[]
  exercise?: { prompt: string; starter: string; answer_label: string; path: string } | null
  suggested_questions?: string[]
}
export interface Message {
  id: string
  author: 'LEARNER' | 'AI' | 'MENTOR' | 'SYSTEM'
  content: string
  citations: Citation[]
  created_at: string
}
export interface Attempt {
  id: string
  milestone_id: string
  explanation: string
  code: string
  file_paths: string[]
  test_output: string | null
  assessment: 'UNRESOLVED' | 'PROGRESS' | 'NEEDS_REVIEW'
  assessment_note: string
  created_at: string
}
export interface Activity {
  id: string
  tool: string
  status: 'SUCCEEDED' | 'FAILED'
  summary: string
  created_at: string
}
export interface CaseSummary {
  id: string
  session_id: string
  task_title: string
  learner_name: string
  reason: Reason
  status: 'OPEN' | 'RESOLVED'
  revision: number
  created_at: string
}
export interface MentorCase extends CaseSummary {
  learner_question: string
  milestone_id: string
  summary: string
  unresolved_question: string
  evidence: Citation[]
  attempts: Attempt[]
  prior_hints: Message[]
  proposed_guidance: string
  mentor_messages: Message[]
}
export interface SessionSummary {
  id: string
  task_title: string
  learner_name: string
  state: SessionState
  version: number
  updated_at: string
}
export interface Session {
  id: string
  task_id: string
  task: Task
  state: SessionState
  current_milestone_id: string
  version: number
  messages: Message[]
  attempts: Attempt[]
  activity: Activity[]
  open_escalation: MentorCase | null
  latest_run: { id: string; status: 'RUNNING' | 'SUCCEEDED' | 'FAILED' } | null
  updated_at: string
}
export interface List<T> {
  items: T[]
}
