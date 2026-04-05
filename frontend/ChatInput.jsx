import React, { useState, useRef, useEffect } from 'react'

const SUGGESTIONS = [
  "What are GitLab's core values?",
  "How does GitLab handle remote work?",
  "What is GitLab's AI strategy?",
  "How does GitLab approach hiring?",
  "What is GitLab's product direction for 2025?",
  "What is the GitLab handbook?",
]

export function ChatInput({ onSend, isStreaming, hasMessages }) {
  const [input, setInput] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [sourceFilter, setSourceFilter] = useState(null)
  const [useHybrid, setUseHybrid] = useState(false)
  const textareaRef = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }, [input])

  const handleSubmit = () => {
    const q = input.trim()
    if (!q || isStreaming) return
    onSend(q, { sourceFilter, useHybrid })
    setInput('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const filterBtn = (label, value, isActive) => (
    <button
      onClick={() => {
        if (label === 'hybrid') {
          setUseHybrid(!useHybrid)
          setSourceFilter(null)
        } else {
          setSourceFilter(isActive ? null : value)
          setUseHybrid(false)
        }
      }}
      style={{
        padding: '3px 10px',
        borderRadius: 4,
        border: `1px solid ${isActive ? 'var(--orange)' : 'var(--border)'}`,
        background: isActive ? 'var(--orange-dim)' : 'transparent',
        color: isActive ? 'var(--orange)' : 'var(--text-muted)',
        fontSize: 11,
        cursor: 'pointer',
        fontFamily: 'var(--font-mono)',
        transition: 'all var(--transition)',
      }}
    >
      {label}
    </button>
  )

  return (
    <div style={{ padding: '16px 20px 20px', borderTop: '1px solid var(--border)', background: 'var(--bg-base)' }}>

      {/* Suggestions — only when no messages yet */}
      {!hasMessages && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>
            try asking →
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {SUGGESTIONS.map((s, i) => (
              <button
                key={i}
                onClick={() => { setInput(s); textareaRef.current?.focus() }}
                style={{
                  padding: '5px 12px',
                  border: '1px solid var(--border)',
                  borderRadius: 20,
                  background: 'transparent',
                  color: 'var(--text-secondary)',
                  fontSize: 12,
                  cursor: 'pointer',
                  fontFamily: 'var(--font-mono)',
                  transition: 'all var(--transition)',
                  whiteSpace: 'nowrap',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'var(--orange)'
                  e.currentTarget.style.color = 'var(--orange)'
                  e.currentTarget.style.background = 'var(--orange-dim)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'var(--border)'
                  e.currentTarget.style.color = 'var(--text-secondary)'
                  e.currentTarget.style.background = 'transparent'
                }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Filter controls */}
      {showFilters && (
        <div style={{
          display: 'flex', gap: 8, alignItems: 'center',
          marginBottom: 10, padding: '8px 12px',
          background: 'var(--bg-elevated)', borderRadius: 6,
          border: '1px solid var(--border)',
          animation: 'fadeSlideUp 0.15s ease forwards',
        }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)', marginRight: 4 }}>source:</span>
          {filterBtn('handbook', 'handbook', sourceFilter === 'handbook')}
          {filterBtn('direction', 'direction', sourceFilter === 'direction')}
          {filterBtn('hybrid', null, useHybrid)}
        </div>
      )}

      {/* Input row */}
      <div style={{
        display: 'flex', gap: 10, alignItems: 'flex-end',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-bright)',
        borderRadius: 10,
        padding: '10px 12px',
        transition: 'border-color var(--transition)',
      }}
        onFocus={e => e.currentTarget.style.borderColor = 'var(--orange)'}
        onBlur={e => e.currentTarget.style.borderColor = 'var(--border-bright)'}
      >
        {/* Filter toggle */}
        <button
          onClick={() => setShowFilters(f => !f)}
          title="Filter by source"
          style={{
            background: showFilters ? 'var(--orange-dim)' : 'none',
            border: `1px solid ${showFilters ? 'var(--orange)' : 'var(--border)'}`,
            borderRadius: 5,
            padding: '4px 8px',
            color: showFilters ? 'var(--orange)' : 'var(--text-muted)',
            cursor: 'pointer',
            fontSize: 12,
            flexShrink: 0,
            transition: 'all var(--transition)',
          }}
        >
          ⊟
        </button>

        <textarea
          ref={textareaRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about GitLab..."
          rows={1}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            resize: 'none',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-mono)',
            fontSize: 13.5,
            lineHeight: 1.6,
            overflowY: 'auto',
            caretColor: 'var(--orange)',
          }}
        />

        <button
          onClick={handleSubmit}
          disabled={!input.trim() || isStreaming}
          style={{
            flexShrink: 0,
            width: 36, height: 36,
            borderRadius: 8,
            background: input.trim() && !isStreaming ? 'var(--orange)' : 'var(--bg-elevated)',
            border: 'none',
            color: input.trim() && !isStreaming ? '#fff' : 'var(--text-muted)',
            cursor: input.trim() && !isStreaming ? 'pointer' : 'not-allowed',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16,
            transition: 'all var(--transition)',
            transform: input.trim() && !isStreaming ? 'scale(1)' : 'scale(0.95)',
          }}
        >
          {isStreaming ? '◻' : '↑'}
        </button>
      </div>

      <p style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 8, textAlign: 'center', opacity: 0.6 }}>
        Answers grounded in GitLab Handbook & Direction pages · Enter to send · Shift+Enter for new line
      </p>
    </div>
  )
}
