import { useState, useCallback, useRef } from 'react'

const API_BASE = ''  // Proxied via react-scripts to localhost:8000

export function useChat() {
  const [messages, setMessages] = useState([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState(null)
  const abortRef = useRef(null)

  const sendMessage = useCallback(async (query, options = {}) => {
    if (isStreaming || !query.trim()) return
    setError(null)

    // Add user message
    const userMsg = { id: crypto.randomUUID(), role: 'user', content: query, timestamp: new Date() }
    setMessages(prev => [...prev, userMsg])

    // Add streaming placeholder for assistant
    const assistantId = crypto.randomUUID()
    setMessages(prev => [...prev, {
      id: assistantId,
      role: 'assistant',
      content: '',
      sources: [],
      timestamp: new Date(),
      streaming: true,
    }])

    setIsStreaming(true)

    // Build history from messages before this turn
    const history = messages.map(m => ({ role: m.role, content: m.content }))

    const body = JSON.stringify({
      query,
      history,
      top_k: options.topK ?? 6,
      use_hybrid: options.useHybrid ?? false,
      source_filter: options.sourceFilter ?? null,
    })

    try {
      abortRef.current = new AbortController()
      const resp = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        signal: abortRef.current.signal,
      })

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Request failed' }))
        throw new Error(err.detail?.message ?? err.detail ?? 'Request failed')
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''
      let sources = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const lines = decoder.decode(value, { stream: true }).split('\n')
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            if (event.type === 'token') {
              accumulated += event.content
              setMessages(prev => prev.map(m =>
                m.id === assistantId ? { ...m, content: accumulated } : m
              ))
            } else if (event.type === 'sources') {
              sources = event.content
            } else if (event.type === 'done') {
              setMessages(prev => prev.map(m =>
                m.id === assistantId ? { ...m, sources, streaming: false } : m
              ))
            } else if (event.type === 'error') {
              throw new Error(event.content)
            }
          } catch (_) { /* skip malformed SSE lines */ }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') return
      setError(err.message)
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, content: '', streaming: false, error: err.message }
          : m
      ))
    } finally {
      setIsStreaming(false)
    }
  }, [messages, isStreaming])

  const clearChat = useCallback(() => {
    abortRef.current?.abort()
    setMessages([])
    setError(null)
    setIsStreaming(false)
  }, [])

  return { messages, isStreaming, error, sendMessage, clearChat }
}
