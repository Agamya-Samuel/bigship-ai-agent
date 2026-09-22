import { useState, useEffect, useRef, type KeyboardEvent } from 'react'
import { useNavigate, useLocation } from '@tanstack/react-router'
import {
  Send,
  Plus,
  Trash2,
  LogOut,
  Menu,
  MessageSquare,
  X,
  ChevronDown,
  ChevronRight,
  Loader2,
  Sparkles,
  Copy,
  Check,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import {
  getSessions,
  createSession,
  streamChat,
  getChatHistory,
  deleteSession,
  logout,
} from '../lib/api'
import type { Session, AgentStep } from '../types'
import { ThemeToggle } from '../components/ThemeToggle'
import { IconButton } from '../components/ui/IconButton'
import { BrandLogo } from '../components/ui/BrandIcon'
import { suggestions } from '../lib/suggestions'

const PENDING_PREFIX = 'pending-'

function isPending(id: string | null): boolean {
  if (!id) return false
  return id.startsWith(PENDING_PREFIX) || id === 'new'
}

function normalizeRole(role: string): 'user' | 'assistant' {
  if (role === 'assistant' || role === 'ai') return 'assistant'
  return 'user'
}

type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  steps?: AgentStep[]
  tokens?: number
  tps?: number
  timestamp?: number
  model?: string
}

function normalizeChatMessage(raw: Partial<ChatMessage> & { role: string }): ChatMessage {
  return {
    role: normalizeRole(raw.role),
    content: raw.content ?? '',
    steps: raw.steps,
    tokens: raw.tokens,
    tps: raw.tps,
    timestamp: raw.timestamp,
    model: raw.model,
  }
}

function getThreadIdFromSearch(search?: string): string | undefined {
  if (!search) return undefined
  const params = new URLSearchParams(search)
  return params.get('threadId') || undefined
}

function getQueryFromSearch(search?: string): string {
  if (!search) return ''
  const params = new URLSearchParams(search)
  return params.get('q') ?? ''
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* noop */
    }
  }
  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] transition-colors"
      title="Copy message"
    >
      {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

function ReasoningChip({ text, live, isLatest }: { text: string; live?: boolean; isLatest?: boolean }) {
  const [open, setOpen] = useState(false)
  useEffect(() => {
    if (isLatest) setOpen(true)
  }, [isLatest])
  return (
    <div className="mt-2 text-xs">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-colors"
      >
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        {open ? 'Hide reasoning' : 'See reasoning'}
      </button>
      {open && (
        <div className="mt-1.5 px-3 py-2 rounded-lg bg-[var(--bg-subtle)] border border-[var(--border-subtle)] text-[var(--text-secondary)] leading-relaxed">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
            {text}
          </ReactMarkdown>
          {live && <span className="streaming-cursor" />}
        </div>
      )}
    </div>
  )
}

function ToolCallItem({ step, processing }: { step: AgentStep; processing?: boolean }) {
  const [open, setOpen] = useState(false)
  if (step.type !== 'tool_call') return null
  const argsStr = step.args && Object.keys(step.args).length > 0 ? JSON.stringify(step.args, null, 2) : '{}'
  return (
    <div className="text-xs">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1.5 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-colors"
      >
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <span className="font-mono">{step.name}</span>
        {processing && <span className="typing-dots text-[var(--text-tertiary)]"><span /><span /><span /></span>}
      </button>
      {open && (
        <pre className="mt-1.5 ml-4 px-3 py-2 rounded-lg bg-[var(--bg-subtle)] border border-[var(--border-subtle)] text-[var(--text-secondary)] whitespace-pre-wrap break-words text-[11px] leading-relaxed overflow-x-auto">
          {argsStr}
        </pre>
      )}
    </div>
  )
}

function ToolResultItem({ step }: { step: AgentStep }) {
  const [open, setOpen] = useState(false)
  if (step.type !== 'tool_result') return null
  const formatResult = (value: string) => {
    const trimmed = String(value || '').trim()
    if (!trimmed) return ''
    const tryParse = (raw: string) => {
      try {
        return JSON.stringify(JSON.parse(raw), null, 2)
      } catch {
        return null
      }
    }
    let formatted = tryParse(trimmed)
    if (formatted !== null) return formatted
    const asJson = trimmed
      .replace(/'/g, '"')
      .replace(/\bTrue\b/g, 'true')
      .replace(/\bFalse\b/g, 'false')
      .replace(/\bNone\b/g, 'null')
    formatted = tryParse(asJson)
    return formatted ?? trimmed
  }
  const formatted = formatResult(step.result)
  return (
    <div className="text-xs">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1.5 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-colors"
      >
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <span className="font-mono">{step.name} result</span>
      </button>
      {open && (
        <pre className="mt-1.5 ml-4 px-3 py-2 rounded-lg bg-[var(--bg-subtle)] border border-[var(--border-subtle)] text-[var(--text-secondary)] whitespace-pre-wrap break-words text-[11px] leading-relaxed overflow-x-auto max-h-72">
          {formatted}
        </pre>
      )}
    </div>
  )
}

function StepTrace({ steps, live }: { steps?: AgentStep[]; live?: boolean }) {
  if (!steps || steps.length === 0) return null
  let lastReasoningIdx = -1
  steps.forEach((s, i) => {
    if (s.type === 'reasoning') lastReasoningIdx = i
  })
  const toolResultIds = new Set(
    steps.filter((s) => s.type === 'tool_result').map((s) => (s as { tool_call_id?: string }).tool_call_id),
  )
  return (
    <div className="mt-2 space-y-1.5">
      {steps.map((s, i) => (
        <div key={i}>
          {s.type === 'reasoning' && (
            <ReasoningChip text={s.text} live={live && i === lastReasoningIdx} isLatest={i === lastReasoningIdx} />
          )}
          {s.type === 'tool_call' && (
            <ToolCallItem
              step={s}
              processing={live && !toolResultIds.has((s as { tool_call_id?: string }).tool_call_id)}
            />
          )}
          {s.type === 'tool_result' && <ToolResultItem step={s} />}
        </div>
      ))}
    </div>
  )
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="markdown-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          table: ({ node: _node, ...props }) => <table className="w-full border-collapse my-2" {...props} />,
          th: ({ node: _node, ...props }) => (
            <th className="border border-[var(--border-subtle)] px-2 py-1 text-left font-medium" {...props} />
          ),
          td: ({ node: _node, ...props }) => <td className="border border-[var(--border-subtle)] px-2 py-1 align-top" {...props} />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

function EmptyState({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-16 sm:py-24 text-center slide-up">
      <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[var(--accent)] text-white mb-5 shadow-[var(--shadow-sm)]">
        <Sparkles className="h-6 w-6" strokeWidth={2.25} />
      </div>
      <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[var(--text-primary)] mb-2">
        How can I help you ship today?
      </h2>
      <p className="text-sm sm:text-base text-[var(--text-secondary)] mb-8 max-w-md mx-auto">
        Ask anything about your orders, warehouses, or rates — the agent will pull live data from your Bigship account.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-left">
        {suggestions.map((s) => {
          const Icon = s.icon
          return (
            <button
              key={s.title}
              onClick={() => onPick(s.prompt)}
              className="group flex items-start gap-3 p-3.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] hover:bg-[var(--bg-subtle)] hover:border-[var(--border-default)] transition-all hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-base)]"
            >
              <Icon className="h-4 w-4 mt-0.5 text-[var(--text-tertiary)] group-hover:text-[var(--accent)] transition-colors" />
              <div>
                <div className="text-sm font-medium text-[var(--text-primary)]">{s.title}</div>
                <div className="text-xs text-[var(--text-tertiary)] mt-0.5 line-clamp-2">{s.prompt}</div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function MessageBubble({ msg, isLatest, streaming }: {
  msg: ChatMessage
  isLatest: boolean
  streaming: boolean
}) {
  const isUser = msg.role === 'user'
  if (isUser) {
    return (
      <div className="flex justify-end fade-in">
        <div className="max-w-[85%] sm:max-w-[75%] px-4 py-2.5 rounded-2xl bg-[var(--accent)] text-white text-[0.9375rem] leading-relaxed whitespace-pre-wrap break-words">
          {msg.content}
        </div>
      </div>
    )
  }
  const showCursor = streaming && isLatest
  return (
    <div className="flex justify-start fade-in">
      <div className="max-w-[85%] sm:max-w-[75%] min-w-0">
        <StepTrace steps={msg.steps} live={streaming && isLatest} />
        {msg.content && (
          <>
            <div className="px-4 py-3 rounded-2xl bg-[var(--bg-elevated)] border border-[var(--border-subtle)] text-[0.9375rem] text-[var(--text-primary)]">
              <MarkdownContent content={msg.content} />
              {showCursor && !msg.content.endsWith(' ') && <span className="streaming-cursor" />}
            </div>
            {!streaming && msg.content && (
              <div className="mt-1.5 flex items-center gap-2">
                <CopyButton text={msg.content} />
                {msg.model && (
                  <span className="text-[10px] text-[var(--text-quaternary)] font-mono">
                    {msg.model.replace(/:free$/, '')}
                  </span>
                )}
                {msg.tokens != null && msg.tps != null && (
                  <span className="text-[10px] text-[var(--text-quaternary)]">
                    {msg.tokens} tokens · {msg.tps} TPS
                  </span>
                )}
              </div>
            )}
          </>
        )}
        {!msg.content && streaming && isLatest && (
          <div className="px-4 py-3 rounded-2xl bg-[var(--bg-elevated)] border border-[var(--border-subtle)] text-[var(--text-tertiary)] text-sm">
            <span className="typing-dots"><span /><span /><span /></span>
          </div>
        )}
      </div>
    </div>
  )
}

function SidebarContent({
  onClose,
  sessions,
  activeThreadId,
  handleNewSession,
  handleSessionClick,
  handleDeleteSession,
  userName,
  handleLogout,
}: {
  onClose?: () => void
  sessions: Session[]
  activeThreadId: string | null
  handleNewSession: () => void
  handleSessionClick: (id: string) => void
  handleDeleteSession: (id: string) => void
  userName: string
  handleLogout: () => void
}) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-3 pt-3 pb-2 flex items-center justify-between">
        <BrandLogo size="sm" />
        {onClose && (
          <IconButton onClick={onClose} ariaLabel="Close sidebar" size="sm">
            <X className="h-4 w-4" />
          </IconButton>
        )}
      </div>
      <div className="px-3 pb-3">
        <button
          onClick={handleNewSession}
          className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-[var(--border-default)] bg-[var(--bg-elevated)] text-sm font-medium text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-base)]"
        >
          <Plus className="h-4 w-4" />
          New chat
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        <div className="px-2 pt-1 pb-1.5 text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
          Recent
        </div>
        <div className="space-y-0.5">
          {sessions.length === 0 && (
            <p className="px-2 py-3 text-xs text-[var(--text-tertiary)] text-center">
              No conversations yet
            </p>
          )}
          {sessions.map((session) => {
            const active = activeThreadId === session.thread_id
            return (
              <div
                key={session.thread_id}
                className={`group flex items-center gap-1 pl-2 pr-1 py-1.5 text-sm rounded-lg cursor-pointer transition-colors ${
                  active
                    ? 'bg-[var(--accent-soft)] text-[var(--text-primary)]'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)]'
                }`}
                onClick={() => handleSessionClick(session.thread_id)}
              >
                <MessageSquare className="h-3.5 w-3.5 shrink-0 opacity-60" />
                <span className="truncate flex-1 text-[13px]">{session.label || 'Chat'}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDeleteSession(session.thread_id)
                  }}
                  className="opacity-0 group-hover:opacity-100 text-[var(--text-tertiary)] hover:text-[var(--danger)] transition-all p-1 rounded"
                  title="Delete chat"
                  aria-label="Delete chat"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            )
          })}
        </div>
      </div>
      <div className="border-t border-[var(--border-subtle)] p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 rounded-full bg-[var(--accent)] text-white flex items-center justify-center text-xs font-medium shrink-0">
              {userName.charAt(0).toUpperCase()}
            </div>
            <span className="text-sm text-[var(--text-primary)] truncate">{userName}</span>
          </div>
          <IconButton onClick={handleLogout} ariaLabel="Log out" variant="destructive" size="sm">
            <LogOut className="h-4 w-4" />
          </IconButton>
        </div>
      </div>
    </div>
  )
}

export default function ChatPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const urlThreadId = getThreadIdFromSearch(location.search)
  const urlPrompt = getQueryFromSearch(location.search)

  const [sessions, setSessions] = useState<Session[]>([])
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [streamingActive, setStreamingActive] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const prevThreadIdRef = useRef<string | null>(null)
  const promptConsumedRef = useRef(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const userName = localStorage.getItem('user_name') || 'User'

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 768px)')
    const update = () => setSidebarOpen(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    loadSessions()
  }, [])

  useEffect(() => {
    if (urlThreadId && urlThreadId !== activeThreadId) {
      setActiveThreadId(urlThreadId)
      if (!isPending(activeThreadId)) {
        setMessages([])
      }
      setSessions((prev) => {
        if (prev.some((s) => s.thread_id === urlThreadId)) return prev
        return [
            ...prev,
            { id: '', thread_id: urlThreadId, label: 'Chat', created_at: '', last_used_at: '' },
          ]
      })
    }
  }, [urlThreadId])

  useEffect(() => {
    if (!activeThreadId) return
    const wasPending = isPending(prevThreadIdRef.current)
    prevThreadIdRef.current = activeThreadId
    if (isPending(activeThreadId)) return
    if (wasPending) return
    let cancelled = false
    const loadHistory = async () => {
      try {
        const data = await getChatHistory(activeThreadId)
        if (!cancelled) {
          setMessages(
            (data.messages || []).map((m: ChatMessage) => normalizeChatMessage(m)),
          )
        }
      } catch {
        if (!cancelled) setMessages([])
      }
    }
    loadHistory()
    return () => {
      cancelled = true
    }
  }, [activeThreadId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (urlPrompt && !promptConsumedRef.current && activeThreadId) {
      promptConsumedRef.current = true
      setInput(urlPrompt)
      // strip the q param so a refresh doesn't re-populate
      navigate({ to: '/chat', search: { threadId: activeThreadId }, replace: true })
      // auto-send once thread is ready
      setTimeout(() => {
        const ta = textareaRef.current
        if (ta) ta.focus()
      }, 0)
    }
  }, [urlPrompt, activeThreadId])

  const loadSessions = async () => {
    try {
      const data = await getSessions()
      setSessions(data.sessions)
      const effectiveThreadId =
        urlThreadId ||
        activeThreadId ||
        (data.sessions.length > 0 ? data.sessions[0].thread_id : null)
      if (effectiveThreadId && effectiveThreadId !== activeThreadId) {
        setActiveThreadId(effectiveThreadId)
        if (effectiveThreadId !== urlThreadId) {
          navigate({ to: '/chat', search: { threadId: effectiveThreadId } })
        }
      }
    } catch {
      /* ignore */
    }
  }

  const handleNewSession = () => {
    const pendingId = `${PENDING_PREFIX}${Date.now()}`
    setActiveThreadId(pendingId)
    setMessages([])
    promptConsumedRef.current = false
    setSessions((prev) => [
      ...prev,
      { id: '', thread_id: pendingId, label: 'New chat', created_at: '', last_used_at: '' },
    ])
    navigate({ to: '/chat', search: { threadId: pendingId } })
    setMobileSidebarOpen(false)
  }

  const handleSessionClick = async (threadId: string) => {
    setActiveThreadId(threadId)
    setMessages([])
    promptConsumedRef.current = true
    try {
      const data = await getChatHistory(threadId)
      setMessages(
        (data.messages || []).map((m: { role: string; content: string; steps?: AgentStep[] }) => ({
          role: normalizeRole(m.role),
          content: m.content,
          steps: m.steps,
        })),
      )
    } catch {
      setMessages([])
    }
    navigate({ to: '/chat', search: { threadId } })
    setMobileSidebarOpen(false)
  }

  const handleDeleteSession = async (threadId: string) => {
    try {
      await deleteSession(threadId)
      setSessions((prev) => prev.filter((s) => s.thread_id !== threadId))
      if (activeThreadId === threadId) {
        setActiveThreadId(null)
        setMessages([])
        const remaining = sessions.filter((s) => s.thread_id !== threadId)
        if (remaining.length > 0) {
          handleSessionClick(remaining[0].thread_id)
        } else {
          navigate({ to: '/chat', search: {} })
        }
      }
    } catch {
      /* ignore */
    }
  }

  const ensureThreadId = async (): Promise<string | null> => {
    if (!activeThreadId) return null
    if (!isPending(activeThreadId)) return activeThreadId
    try {
      const data = await createSession('New chat')
      const threadId = data.thread_id
      setActiveThreadId(threadId)
      setSessions((prev) =>
        prev.map((s) =>
          s.thread_id === activeThreadId ? { ...s, thread_id: threadId, label: 'New chat' } : s,
        ),
      )
      navigate({ to: '/chat', search: { threadId } })
      return threadId
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Error: failed to start chat' },
      ])
      return null
    }
  }

  const handleSend = async () => {
    if (!input.trim() || !activeThreadId || loading) return
    const userMessage = input.trim()
    const userTimestamp = Date.now()
    setInput('')
    promptConsumedRef.current = true
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: userMessage, timestamp: userTimestamp },
      { role: 'assistant', content: '', steps: [] },
    ])
    setLoading(true)
    setStreamingActive(true)
    try {
      const threadId = await ensureThreadId()
      if (!threadId) return
      await streamChat(threadId, userMessage, (ev) => {
        if (ev.type === 'done' || ev.type === 'error') setStreamingActive(false)
        setMessages((prev) => {
          if (prev.length === 0) return prev
          const idx = prev.length - 1
          const last = prev[idx]
          if (last.role !== 'assistant') return prev
          if (ev.type === 'text_delta') {
            const next = [...prev]
            next[idx] = { ...last, content: last.content + ev.text }
            return next
          }
          if (ev.type === 'reasoning_delta') {
            const steps = [...(last.steps ?? [])]
            const lastStep = steps[steps.length - 1]
            if (lastStep && lastStep.type === 'reasoning') {
              steps[steps.length - 1] = { type: 'reasoning', text: lastStep.text + ev.text }
            } else {
              steps.push({ type: 'reasoning', text: ev.text })
            }
            const next = [...prev]
            next[idx] = { ...last, steps }
            return next
          }
          if (ev.type === 'reasoning') {
            const next = [...prev]
            next[idx] = {
              ...last,
              content: '',
              steps: [...(last.steps ?? []), { type: 'reasoning', text: ev.text }],
            }
            return next
          }
          if (ev.type === 'tool_call') {
            const next = [...prev]
            next[idx] = {
              ...last,
              steps: [
                ...(last.steps ?? []),
                { type: 'tool_call', name: ev.name, args: ev.args, tool_call_id: ev.tool_call_id },
              ],
            }
            return next
          }
          if (ev.type === 'tool_result') {
            const next = [...prev]
            const steps = next[idx].steps ?? []
            const matchIdx = steps
              .map((s) => (s.type === 'tool_call' ? s.tool_call_id : ''))
              .lastIndexOf(ev.tool_call_id)
            if (matchIdx >= 0) {
              steps[matchIdx] = { ...steps[matchIdx], result: ev.result } as AgentStep
            } else {
              steps.push({
                type: 'tool_result',
                tool_call_id: ev.tool_call_id,
                name: ev.name,
                result: ev.result,
              })
            }
            next[idx] = { ...last, steps }
            return next
          }
          if (ev.type === 'done') {
            return [
              ...prev.slice(0, idx),
              normalizeChatMessage({
                role: 'assistant',
                content: ev.response,
                steps: ev.steps ?? [],
                tokens: ev.tokens,
                tps: ev.tps,
                timestamp: Date.now(),
                model: ev.model,
              }),
            ]
          }
          if (ev.type === 'error') {
            const next = [...prev]
            const rateLimitMessage =
              ev.error_type === 'rate_limited'
                ? `Rate limit reached. Please try again${ev.retry_after ? ` in ~${ev.retry_after}s` : ' in a few seconds'}.`
                : null
            next[idx] = {
              ...last,
              content: last.content || rateLimitMessage || 'Error: failed to send message',
            }
            return next
          }
          return prev
        })
      })
    } catch {
      setStreamingActive(false)
      setMessages((prev) => {
        const idx = prev.length - 1
        const last = prev[idx]
        if (last && last.role === 'assistant' && !last.content) {
          return [...prev.slice(0, idx), { ...last, content: 'Error: failed to send message' }]
        }
        return prev
      })
    } finally {
      setLoading(false)
      setStreamingActive(false)
    }
  }

  const handleLogout = async () => {
    try {
      await logout()
    } finally {
      localStorage.clear()
      navigate({ to: '/login' })
    }
  }

  const autoResize = (el: HTMLTextAreaElement) => {
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const pickSuggestion = (prompt: string) => {
    if (!activeThreadId) {
      handleNewSession()
    }
    setInput(prompt)
    promptConsumedRef.current = true
    setTimeout(() => textareaRef.current?.focus(), 0)
  }

  return (
    <div className="h-screen flex bg-[var(--bg-base)] text-[var(--text-primary)] overflow-hidden">
      {/* Desktop sidebar */}
      {sidebarOpen && (
        <aside
          className="hidden md:flex w-64 shrink-0 border-r border-[var(--border-subtle)] bg-[var(--bg-subtle)]/40 flex-col"
          style={{ paddingTop: 'env(safe-area-inset-top)' }}
        >
          <SidebarContent
            sessions={sessions}
            activeThreadId={activeThreadId}
            handleNewSession={handleNewSession}
            handleSessionClick={handleSessionClick}
            handleDeleteSession={handleDeleteSession}
            userName={userName}
            handleLogout={handleLogout}
          />
        </aside>
      )}

      {/* Mobile sidebar overlay */}
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden"
          role="dialog"
          aria-modal="true"
        >
          <div
            className="absolute inset-0 bg-black/40 fade-in"
            onClick={() => setMobileSidebarOpen(false)}
          />
          <aside
            className="absolute inset-y-0 left-0 w-72 bg-[var(--bg-base)] border-r border-[var(--border-subtle)] slide-up"
            style={{ paddingTop: 'env(safe-area-inset-top)' }}
          >
            <SidebarContent
              onClose={() => setMobileSidebarOpen(false)}
              sessions={sessions}
              activeThreadId={activeThreadId}
              handleNewSession={handleNewSession}
              handleSessionClick={handleSessionClick}
              handleDeleteSession={handleDeleteSession}
              userName={userName}
              handleLogout={handleLogout}
            />
          </aside>
        </div>
      )}

      {/* Main */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Top header */}
        <header
          className="h-14 shrink-0 border-b border-[var(--border-subtle)] bg-[var(--bg-base)]/85 backdrop-blur-md flex items-center justify-between px-3 sm:px-5"
          style={{ paddingTop: 'env(safe-area-inset-top)' }}
        >
          <div className="flex items-center gap-1.5">
            <IconButton
              onClick={() => {
                if (window.matchMedia('(min-width: 768px)').matches) {
                  setSidebarOpen(!sidebarOpen)
                } else {
                  setMobileSidebarOpen(true)
                }
              }}
              ariaLabel={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
            >
              <Menu className="h-4 w-4" />
            </IconButton>
            <span className="text-sm font-medium text-[var(--text-primary)] ml-1 truncate">
              {messages.length > 0 ? 'Bigship Agent' : 'New chat'}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <IconButton
              onClick={handleNewSession}
              ariaLabel="New chat"
              variant="subtle"
            >
              <Plus className="h-4 w-4" />
            </IconButton>
            <ThemeToggle />
          </div>
        </header>

        {/* Messages area */}
        <div
          className="flex-1 overflow-y-auto"
          style={{ paddingBottom: 'calc(7rem + env(safe-area-inset-bottom))' }}
        >
          {messages.length === 0 ? (
            <EmptyState onPick={pickSuggestion} />
          ) : (
            <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10 space-y-5">
              {messages.map((msg, idx) => (
                <MessageBubble
                  key={idx}
                  msg={msg}
                  isLatest={idx === messages.length - 1}
                  streaming={streamingActive}
                />
              ))}
              {loading &&
                (() => {
                  const last = messages[messages.length - 1]
                  if (last && last.role === 'assistant' && last.content) return null
                  if (last && last.role === 'assistant' && last.steps && last.steps.length > 0) return null
                  return (
                    <div className="flex justify-start fade-in">
                      <div className="px-4 py-3 rounded-2xl bg-[var(--bg-elevated)] border border-[var(--border-subtle)] text-[var(--text-tertiary)] text-sm">
                        <span className="typing-dots"><span /><span /><span /></span>
                      </div>
                    </div>
                  )
                })()}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Floating composer */}
        <div
          className="absolute bottom-0 left-0 right-0 md:left-64"
          style={{ paddingBottom: 'calc(1rem + env(safe-area-inset-bottom))' }}
        >
          <div className="max-w-3xl mx-auto px-3 sm:px-6">
              {!activeThreadId ? (
                <div className="text-center text-sm text-[var(--text-tertiary)] py-4">
                  Start a new chat to begin
                </div>
              ) : (
                <div className="composer-glow relative flex items-end gap-2 px-3 py-2 bg-[var(--bg-elevated)] border border-[var(--border-default)] rounded-2xl shadow-[var(--shadow-md)] transition-shadow">
                  <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => {
                      setInput(e.target.value)
                      autoResize(e.target)
                    }}
                    onKeyDown={handleKeyDown}
                    placeholder="Message Bigship Agent…"
                    rows={1}
                    className="flex-1 resize-none bg-transparent text-base sm:text-[0.9375rem] text-[var(--text-primary)] placeholder:text-[var(--text-quaternary)] focus:outline-none px-1 py-2 max-h-48 leading-relaxed"
                    disabled={loading}
                  />
                  <button
                    onClick={handleSend}
                    disabled={loading || !input.trim()}
                    className="shrink-0 inline-flex items-center justify-center w-8 h-8 rounded-lg bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-elevated)]"
                    aria-label="Send message"
                  >
                    {loading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </button>
                </div>
              )}
              <p className="mt-2 text-[11px] text-center text-[var(--text-tertiary)]">
                Bigship Agent can make mistakes. Verify order-critical data before acting.
              </p>
            </div>
        </div>
      </main>
    </div>
  )
}