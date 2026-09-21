export interface AccountInfo {
  account_id: string
  user_name: string
}

export interface Session {
  id: string
  thread_id: string
  label: string
  created_at: string
  last_used_at: string
}

export interface SessionListResponse {
  sessions: Session[]
}

export interface LoginRequest {
  user_name: string
  password: string
  access_key: string
}

export interface LoginResponse {
  access_token: string
  account_id: string
  token_type: string
}

export interface ChatRequest {
  thread_id: string
  message: string
}

export type AgentStep =
  | { type: 'reasoning'; text: string }
  | { type: 'tool_call'; name: string; args: Record<string, unknown>; tool_call_id?: string; result?: string }
  | { type: 'tool_result'; tool_call_id: string; name: string; result: string }

export interface ChatResponse {
  response: string
  steps?: AgentStep[]
}

export type StreamEvent =
  | { type: 'start' }
  | { type: 'text_delta'; text: string }
  | { type: 'reasoning_delta'; text: string }
  | { type: 'reasoning'; text: string }
  | { type: 'tool_call'; name: string; args: Record<string, unknown>; tool_call_id?: string }
  | { type: 'tool_result'; tool_call_id: string; name: string; result: string }
  | { type: 'done'; response: string; steps: AgentStep[]; tokens?: number; tps?: number }
  | { type: 'error'; detail?: string }
