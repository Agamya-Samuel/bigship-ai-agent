import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from '@tanstack/react-router'
import { Send, Plus, Trash2, LogOut, Menu, GitBranch, X, ChevronRight, ChevronDown, Cloud } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { getSessions, createSession, streamChat, getChatHistory, deleteSession, logout } from '../lib/api'
import type { Session, AgentStep } from '../types'
import { ThemeToggle } from '../components/ThemeToggle'
import { IconButton } from '../components/ui/IconButton'
import { AccentButton } from '../components/ui/AccentButton'
import { BrandIcon } from '../components/ui/BrandIcon'

const PENDING_PREFIX = 'pending-'

function isPending(id: string | null): boolean {
  if (!id) return false
  return id.startsWith(PENDING_PREFIX) || id === 'new'
}

function normalizeRole(role: string): 'user' | 'assistant' {
  if (role === 'assistant' || role === 'ai') return 'assistant'
  return 'user'
}

type ChatMessage = { role: 'user' | 'assistant'; content: string; steps?: AgentStep[]; tokens?: number; tps?: number; timestamp?: number; model?: string }

function ReasoningChip({ text, live, isLatest }: { text: string; live?: boolean; isLatest?: boolean }) {
  const [open, setOpen] = useState(false)
  useEffect(() => {
    if (isLatest && live) {
      setOpen(true)
    }
  }, [isLatest, live])
  return (
    <div className="text-xs text-(--text-tertiary)">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 hover:text-(--text-secondary) transition-colors cursor-pointer"
      >
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        {open ? 'Hide reasoning' : 'See reasoning'}
      </button>
      {open && (
        <div className="mt-1 ml-4 px-4 py-2 bg-(--bg-secondary) text-(--text-secondary)">
          <div className="markdown-body text-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
              {text}
            </ReactMarkdown>
          </div>
          {live && <span className="animate-pulse">▍</span>}
        </div>
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
    <div className="space-y-1.5 px-1">
      {steps.map((s, i) => {
        const nextStep = steps[i + 1]
        const isLastReasoningBeforeTools = s.type === 'reasoning' && i === lastReasoningIdx && nextStep?.type === 'tool_call'
        const showPuttingTogether = isLastReasoningBeforeTools && live
        return (
          <>
            {s.type === 'reasoning' && <ReasoningChip key={`reasoning-${i}`} text={s.text} live={live && i === lastReasoningIdx} isLatest={i === lastReasoningIdx} />}
            {showPuttingTogether && (
              <div key={`putting-${i}`} className="flex items-start gap-1.5 text-xs text-(--text-tertiary)">
                <Cloud className="w-3 h-3 shrink-0 mt-0.5" />
                <span className="italic">Putting it all together<span className="thinking-dots"></span></span>
              </div>
            )}
            {s.type === 'tool_call' && <ToolCallItem key={`tool-${i}`} step={s} processing={!toolResultIds.has((s as { tool_call_id?: string }).tool_call_id)} />}
            {s.type === 'tool_result' && <ToolResultItem key={`result-${i}`} step={s} />}
          </>
        )
      })}
    </div>
  )
}

function ToolCallItem({ step, processing }: { step: AgentStep; processing?: boolean }) {
  const [open, setOpen] = useState(false)
  if (step.type !== 'tool_call') return null
  const argsStr = step.args && Object.keys(step.args).length > 0 ? JSON.stringify(step.args, null, 2) : '{}'
  return (
    <div className="text-xs text-(--text-tertiary)">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 hover:text-(--text-secondary) transition-colors cursor-pointer"
      >
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        <span className="truncate">{step.name}</span>
        {processing && <span className="thinking-dots"></span>}
      </button>
      {open && (
        <pre className="mt-1 ml-4 text-(--text-secondary) whitespace-pre-wrap break-words bg-(--bg-tertiary) px-2 py-1.5 rounded border border-(--border-secondary)">
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
    <div className="text-xs text-(--text-tertiary)">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 hover:text-(--text-secondary) transition-colors cursor-pointer"
      >
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        <span className="truncate">{step.name} result</span>
      </button>
      {open && (
        <pre className="mt-1 ml-4 text-(--text-secondary) whitespace-pre-wrap break-words bg-(--bg-tertiary) px-2 py-1.5 rounded border border-(--border-secondary)">
          {formatted}
        </pre>
      )}
    </div>
  )
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="markdown-body text-sm">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          table: ({ node, ...props }) => (
            <table className="w-full border-collapse my-2 text-xs" {...props} />
          ),
          th: ({ node, ...props }) => (
            <th className="border border-(--border-secondary) px-2 py-1 text-left font-medium text-(--text-secondary)" {...props} />
          ),
          td: ({ node, ...props }) => (
            <td className="border border-(--border-secondary) px-2 py-1 align-top text-(--text-secondary)" {...props} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

function getThreadIdFromSearch(search?: string): string | undefined {
  if (!search) return undefined
  const params = new URLSearchParams(search)
  return params.get('threadId') || undefined
}

function MobileSidebarContent({ onClose, sessions, activeThreadId, handleNewSession, handleSessionClick, handleDeleteSession }: {
  onClose: () => void
  sessions: Session[]
  activeThreadId: string | null
  handleNewSession: () => void
  handleSessionClick: (id: string) => void
  handleDeleteSession: (id: string) => void
}) {
  return (
    <>
      <div className="p-3 border-b border-(--border-primary) flex items-center justify-between">
        <AccentButton size="sm" onClick={handleNewSession} className="w-full">
          <Plus className="w-3 h-3" />
          New Chat
        </AccentButton>
        <IconButton onClick={onClose} ariaLabel="Close history" className="ml-2">
          <X className="w-4 h-4" />
        </IconButton>
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className="p-2 space-y-1">
          {sessions.map((session) => (
            <div
              key={session.thread_id}
              className={`group flex items-center justify-between px-3 py-2 text-sm rounded cursor-pointer ${
                activeThreadId === session.thread_id
                  ? 'bg-(--accent)/10 text-(--accent)'
                  : 'text-(--text-secondary) hover:bg-(--bg-tertiary)'
              }`}
              onClick={() => handleSessionClick(session.thread_id)}
            >
              <span className="truncate flex-1">
                {session.label || 'Chat'}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleDeleteSession(session.thread_id)
                }}
                className="ml-2 opacity-0 group-hover:opacity-100 text-(--text-tertiary) hover:text-red-500 transition-opacity"
                title="Delete chat"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}

export default function ChatPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const urlThreadId = getThreadIdFromSearch(location.search)
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [streamingActive, setStreamingActive] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [showMobileSidebar, setShowMobileSidebar] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const prevThreadIdRef = useRef<string | null>(null)

  const userName = localStorage.getItem('user_name') || 'User'

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 768px)')
    setSidebarCollapsed(mq.matches)
    const handler = (e: MediaQueryListEvent) => setSidebarCollapsed(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
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
        return [...prev, { id: '', thread_id: urlThreadId, label: 'Chat', created_at: '', last_used_at: '' }]
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
            (data.messages || []).map((m: { role: string; content: string; steps?: AgentStep[] }) => ({
              role: normalizeRole(m.role),
              content: m.content,
              steps: m.steps,
            }))
          )
        }
      } catch {
        if (!cancelled) {
          setMessages([])
        }
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

  const loadSessions = async () => {
    try {
      const data = await getSessions()
      setSessions(data.sessions)
      const effectiveThreadId = urlThreadId || activeThreadId || (data.sessions.length > 0 ? data.sessions[0].thread_id : null)
      if (effectiveThreadId && effectiveThreadId !== activeThreadId) {
        setActiveThreadId(effectiveThreadId)
        if (effectiveThreadId !== urlThreadId) {
          navigate({ to: '/chat', search: { threadId: effectiveThreadId } })
        }
      }
    } catch {
      // ignore
    }
  }

  const handleNewSession = () => {
    const pendingId = `${PENDING_PREFIX}${Date.now()}`
    setActiveThreadId(pendingId)
    setMessages([])
    setSessions((prev) => [...prev, { id: '', thread_id: pendingId, label: 'New Chat', created_at: '', last_used_at: '' }])
    navigate({ to: '/chat', search: { threadId: pendingId } })
  }

  const handleSessionClick = async (threadId: string) => {
    setActiveThreadId(threadId)
    setMessages([])
    try {
      const data = await getChatHistory(threadId)
      setMessages(
        (data.messages || []).map((m: { role: string; content: string; steps?: AgentStep[] }) => ({
          role: normalizeRole(m.role),
          content: m.content,
          steps: m.steps,
        }))
      )
    } catch {
      setMessages([])
    }
    navigate({ to: '/chat', search: { threadId } })
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
      // ignore
    }
  }

  const ensureThreadId = async (): Promise<string | null> => {
    if (!activeThreadId) return null
    if (!isPending(activeThreadId)) return activeThreadId
    try {
      const data = await createSession('New Chat')
      const threadId = data.thread_id
      setActiveThreadId(threadId)
      setSessions((prev) =>
        prev.map((s) =>
          s.thread_id === activeThreadId ? { ...s, thread_id: threadId, label: 'New Chat' } : s,
        ),
      )
      navigate({ to: '/chat', search: { threadId } })
      return threadId
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Error: failed to start chat' }])
      return null
    }
  }

  const handleSend = async () => {
    if (!input.trim() || !activeThreadId || loading) return
    const userMessage = input.trim()
    const userTimestamp = Date.now()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMessage, timestamp: userTimestamp }, { role: 'assistant', content: '', steps: [] }])
    setLoading(true)
    setStreamingActive(true)
    try {
      const threadId = await ensureThreadId()
      if (!threadId) return
      await streamChat(threadId, userMessage, (ev) => {
        if (ev.type === 'done' || ev.type === 'error') {
          setStreamingActive(false)
        }
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
              steps: [...(last.steps ?? []), { type: 'tool_call', name: ev.name, args: ev.args, tool_call_id: ev.tool_call_id }],
            }
            return next
          }
          if (ev.type === 'tool_result') {
            const next = [...prev]
            const steps = next[idx].steps ?? []
            const matchIdx = steps.map((s) => (s.type === 'tool_call' ? s.tool_call_id : '')).lastIndexOf(ev.tool_call_id)
             if (matchIdx >= 0) {
              steps[matchIdx] = { ...steps[matchIdx], result: ev.result } as AgentStep
            } else {
              steps.push({ type: 'tool_result', tool_call_id: ev.tool_call_id, name: ev.name, result: ev.result })
            }
            next[idx] = { ...last, steps }
            return next
          }
          if (ev.type === 'done') {
            return [...prev.slice(0, idx), { role: 'assistant', content: ev.response, steps: ev.steps ?? [], tokens: ev.tokens, tps: ev.tps, timestamp: Date.now() }]
          }
          if (ev.type === 'error') {
            const next = [...prev]
            next[idx] = { ...last, content: last.content || 'Error: failed to send message' }
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

  return (
    <div className="min-h-screen bg-(--bg-primary) text-(--text-secondary) font-sans antialiased">
      {/* Header */}
      <header className="border-b border-(--border-primary) bg-(--bg-primary)" style={{ height: 'calc(3rem + env(safe-area-inset-top))' }}>
        <div className="h-12 px-4 flex items-center justify-between" style={{ paddingTop: 'env(safe-area-inset-top)' }}>
          <div className="flex items-center gap-3">
            <IconButton
              onClick={() => {
                if (window.matchMedia('(max-width: 768px)').matches) {
                  setShowMobileSidebar(true)
                } else {
                  setSidebarCollapsed(!sidebarCollapsed)
                }
              }}
              ariaLabel={sidebarCollapsed ? 'Show history' : 'Hide history'}
            >
              <Menu className="w-5 h-5" />
            </IconButton>
            <div className="flex items-center gap-2">
              <BrandIcon size="sm" />
              <span className="text-xs font-semibold tracking-wide text-(--text-primary)">BIGSHIP</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <IconButton onClick={handleNewSession} ariaLabel="New chat">
              <Plus className="w-5 h-5" />
            </IconButton>
            <ThemeToggle />
            <div className="w-px h-5 bg-(--border-primary)" />
            <span className="text-xs text-(--text-tertiary)">{userName}</span>
            <IconButton onClick={handleLogout} ariaLabel="Log out" variant="destructive">
              <LogOut className="w-5 h-5" />
            </IconButton>
          </div>
        </div>
      </header>

      {/* Mobile sidebar overlay */}
      {showMobileSidebar && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-40 md:hidden"
            onClick={() => setShowMobileSidebar(false)}
          />
          <aside className="fixed inset-y-0 left-0 w-64 border-r border-(--border-primary) bg-(--bg-secondary) flex flex-col z-50 md:hidden">
            <MobileSidebarContent
              onClose={() => setShowMobileSidebar(false)}
              sessions={sessions}
              activeThreadId={activeThreadId}
              handleNewSession={handleNewSession}
              handleSessionClick={handleSessionClick}
              handleDeleteSession={handleDeleteSession}
            />
          </aside>
        </>
      )}

      {/* Main layout */}
      <div className="flex h-[calc(100vh-3rem)] overflow-hidden">
        {/* Chat History Sidebar (desktop) */}
        {!sidebarCollapsed && (
          <aside className="hidden w-64 border-r border-(--border-primary) bg-(--bg-secondary) flex-col md:flex">
            <div className="p-3 border-b border-(--border-primary)">
              <AccentButton size="sm" onClick={handleNewSession} className="w-full">
                <Plus className="w-3 h-3" />
                New Chat
              </AccentButton>
            </div>
            <div className="flex-1 overflow-y-auto">
              <div className="p-2 space-y-1">
                {sessions.map((session) => (
                  <div
                    key={session.thread_id}
                    className={`group flex items-center justify-between px-3 py-2 text-sm rounded cursor-pointer ${
                      activeThreadId === session.thread_id
                        ? 'bg-(--accent)/10 text-(--accent)'
                        : 'text-(--text-secondary) hover:bg-(--bg-tertiary)'
                    }`}
                    onClick={() => handleSessionClick(session.thread_id)}
                  >
                    <span className="truncate flex-1">
                      {session.label || 'Chat'}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteSession(session.thread_id)
                      }}
                      className="ml-2 opacity-0 group-hover:opacity-100 text-(--text-tertiary) hover:text-red-500 transition-opacity"
                      title="Delete chat"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        )}

        {/* Main Chat Area */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-6" style={{ paddingBottom: 'calc(4rem + env(safe-area-inset-bottom))' }}>
            {messages.length === 0 ? (
              <div className="h-full flex items-center justify-center text-center">
                <div>
                  <GitBranch className="w-8 h-8 text-(--accent)/30 mx-auto mb-3" />
                  <p className="text-sm text-(--text-tertiary) mb-2">Start a new conversation</p>
                  <p className="text-xs text-(--text-tertiary)">
                    Type a message below to begin.
                  </p>
                </div>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'user' ? (
                    <div className="max-w-[80%] sm:max-w-[70%]">
                      <p className="text-[10px] font-semibold tracking-wider text-(--accent) mb-1 text-right uppercase">You</p>
                      <div className="px-4 py-2 bg-(--accent) text-(--bg-primary)">
                        <p className="text-sm whitespace-pre-wrap break-words">{msg.content}</p>
                      </div>
                      {msg.timestamp && (
                        <p className="text-[10px] text-(--text-tertiary) mt-1 text-right">
                          {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className="max-w-[80%] sm:max-w-[70%] space-y-2 min-w-0">
                      <p className="text-[10px] font-semibold tracking-wider text-orange-400 mb-1 uppercase">Bigship Agent</p>
                      <StepTrace steps={msg.steps} live={streamingActive && idx === messages.length - 1} />
                      {msg.content && (
                        <div className="px-4 py-2 bg-(--bg-secondary) text-(--text-secondary)">
                          <MarkdownContent content={msg.content} />
                        </div>
                      )}
                      {msg.tokens != null && msg.tps != null && (
                        <p className="text-[10px] text-(--text-tertiary)">
                          {msg.tokens} tokens · {msg.tps} TPS
                        </p>
                      )}
                      {msg.timestamp && (
                        <p className="text-[10px] text-(--text-tertiary)">
                          {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}
            {(() => {
              const last = messages[messages.length - 1]
              const showThinking =
                loading && (!last || last.role !== 'assistant' || (!last.content && !(last.steps && last.steps.length > 0)))
              return showThinking ? (
                <div className="flex justify-start">
                  <div className="px-4 py-2 bg-(--bg-secondary) text-(--text-tertiary)">
                    <span className="text-xs">Thinking<span className="thinking-dots"></span></span>
                  </div>
                </div>
              ) : null
            })()}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          {!activeThreadId && (
            <div className="px-4 sm:px-6 py-3 border-t border-(--border-primary) bg-(--bg-secondary)">
              <p className="text-xs text-(--text-tertiary) text-center">
                No active conversation. Create a new chat to start.
              </p>
            </div>
          )}
          <div
            className="p-4 border-t border-(--border-primary) bg-(--bg-primary)"
            style={{ paddingBottom: 'calc(1rem + env(safe-area-inset-bottom))' }}
          >
            <div className="max-w-4xl mx-auto flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder={activeThreadId ? 'Type a message...' : 'Create a new chat to start'}
                className="flex-1 px-3 py-2.5 sm:py-2 text-base sm:text-sm bg-(--bg-secondary) border border-(--border-secondary) text-(--text-primary) placeholder-(--text-tertiary) focus:outline-none focus:border-(--accent) focus:ring-1 focus:ring-(--accent)/20 transition-colors disabled:opacity-50"
                disabled={loading || !activeThreadId}
              />
              <button
                onClick={handleSend}
                disabled={loading || !input.trim() || !activeThreadId}
                className="min-w-11 min-h-11 px-3 py-2 bg-(--accent) text-(--bg-primary) hover:bg-(--accent-hover) disabled:opacity-50 transition-colors flex items-center justify-center"
                aria-label="Send message"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
