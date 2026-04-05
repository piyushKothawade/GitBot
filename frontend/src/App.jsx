import React, { useEffect, useRef } from 'react'
import { useChat } from './hooks/useChat'
import { Message } from './components/Message'
import { ChatInput } from './components/ChatInput'
import { Sidebar } from './components/Sidebar'

function EmptyState() {
  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 16,
      padding: 40,
      textAlign: 'center',
    }}>
      {/* Large decorative logo */}
      <div style={{
        width: 72, height: 72,
        background: 'var(--orange-dim)',
        border: '1px solid var(--orange-glow)',
        borderRadius: 20,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: 8,
      }}>
        <svg width="42" height="42" viewBox="0 0 380 380" fill="none">
          <path d="M190 380L257 173H123L190 380Z" fill="#fc6d26"/>
          <path d="M190 380L123 173H24L190 380Z" fill="#fca326" opacity="0.8"/>
          <path d="M24 173L3 237C1 243 3 250 8 254L190 380L24 173Z" fill="#e24329" opacity="0.7"/>
          <path d="M24 173H123L79 41C76 32 63 32 60 41L24 173Z" fill="#fc6d26" opacity="0.9"/>
          <path d="M190 380L257 173H356L190 380Z" fill="#fca326" opacity="0.8"/>
          <path d="M356 173L377 237C379 243 377 250 372 254L190 380L356 173Z" fill="#e24329" opacity="0.7"/>
          <path d="M356 173H257L301 41C304 32 317 32 320 41L356 173Z" fill="#fc6d26" opacity="0.9"/>
        </svg>
      </div>

      <div>
        <h1 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: 32,
          fontWeight: 300,
          fontStyle: 'italic',
          color: 'var(--text-primary)',
          marginBottom: 8,
          letterSpacing: '-0.02em',
        }}>
          Ask GitBot anything.
        </h1>
        <p style={{
          fontSize: 13,
          color: 'var(--text-secondary)',
          maxWidth: 440,
          lineHeight: 1.7,
        }}>
          Grounded answers from GitLab's{' '}
          <a href="https://handbook.gitlab.com" target="_blank" rel="noopener noreferrer"
            style={{ color: 'var(--orange)', textDecoration: 'none' }}>Handbook</a>
          {' '}and{' '}
          <a href="https://about.gitlab.com/direction" target="_blank" rel="noopener noreferrer"
            style={{ color: 'var(--orange)', textDecoration: 'none' }}>Direction</a>
          {' '}pages. Every answer cites its sources.
        </p>
      </div>

      {/* Feature pills */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', marginTop: 8 }}>
        {[
          '🔍 Semantic search across 4,000+ pages',
          '📎 Source citations on every answer',
          '💬 Multi-turn conversation',
          '⚡ Streaming responses',
        ].map(f => (
          <span key={f} style={{
            padding: '4px 12px',
            border: '1px solid var(--border)',
            borderRadius: 20,
            fontSize: 11.5,
            color: 'var(--text-muted)',
            background: 'var(--bg-elevated)',
          }}>
            {f}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function App() {
  const { messages, isStreaming, sendMessage, clearChat } = useChat()
  const bottomRef = useRef(null)
  const chatAreaRef = useRef(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      overflow: 'hidden',
    }}>
      {/* Sidebar */}
      <Sidebar onClear={clearChat} messageCount={messages.length} />

      {/* Main chat area */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        position: 'relative',
      }}>
        {/* Top bar */}
        <header style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 24px',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-base)',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              gitbot
            </span>
            <span style={{ color: 'var(--border)' }}>·</span>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 5,
              fontSize: 11, color: 'var(--green)',
            }}>
              <div style={{
                width: 6, height: 6, borderRadius: '50%',
                background: 'var(--green)',
                boxShadow: '0 0 6px var(--green)',
              }} />
              online
            </div>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            {isStreaming ? (
              <span style={{ color: 'var(--orange)', animation: 'pulse 1s ease infinite' }}>
                ◈ generating...
              </span>
            ) : (
              <span>4,697 vectors indexed</span>
            )}
          </div>
        </header>

        {/* Messages area */}
        <div
          ref={chatAreaRef}
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: messages.length === 0 ? 0 : '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: 24,
          }}
        >
          {messages.length === 0 ? (
            <EmptyState />
          ) : (
            <>
              {messages.map(msg => (
                <Message key={msg.id} message={msg} />
              ))}
              <div ref={bottomRef} />
            </>
          )}
        </div>

        {/* Input area */}
        <ChatInput
          onSend={sendMessage}
          isStreaming={isStreaming}
          hasMessages={messages.length > 0}
        />
      </div>
    </div>
  )
}
