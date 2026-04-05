import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const GITLAB_ICON = (
  <svg width="16" height="16" viewBox="0 0 380 380" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M190 380L257 173H123L190 380Z" fill="#fc6d26"/>
    <path d="M190 380L123 173H24L190 380Z" fill="#fca326" opacity="0.8"/>
    <path d="M24 173L3 237C1 243 3 250 8 254L190 380L24 173Z" fill="#e24329" opacity="0.7"/>
    <path d="M24 173H123L79 41C76 32 63 32 60 41L24 173Z" fill="#fc6d26" opacity="0.9"/>
    <path d="M190 380L257 173H356L190 380Z" fill="#fca326" opacity="0.8"/>
    <path d="M356 173L377 237C379 243 377 250 372 254L190 380L356 173Z" fill="#e24329" opacity="0.7"/>
    <path d="M356 173H257L301 41C304 32 317 32 320 41L356 173Z" fill="#fc6d26" opacity="0.9"/>
  </svg>
)

function TypingIndicator() {
  return (
    <div style={{ display: 'flex', gap: '5px', alignItems: 'center', padding: '4px 0' }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          width: 7, height: 7,
          borderRadius: '50%',
          background: 'var(--orange)',
          animation: 'pulse 1.2s ease infinite',
          animationDelay: `${i * 0.2}s`,
        }} />
      ))}
    </div>
  )
}

function SourceBadge({ source }) {
  const isHandbook = source.source === 'handbook'
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      title={source.url}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '4px 10px',
        background: 'var(--bg-base)',
        border: '1px solid var(--border)',
        borderRadius: 4,
        fontSize: 11,
        color: 'var(--text-secondary)',
        textDecoration: 'none',
        fontFamily: 'var(--font-mono)',
        transition: 'all var(--transition)',
        whiteSpace: 'nowrap',
        maxWidth: 260,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = 'var(--orange)'
        e.currentTarget.style.color = 'var(--orange)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = 'var(--border)'
        e.currentTarget.style.color = 'var(--text-secondary)'
      }}
    >
      <span style={{
        display: 'inline-block', width: 6, height: 6,
        borderRadius: '50%',
        background: isHandbook ? '#2ea04b' : '#58a6ff',
        flexShrink: 0,
      }} />
      {source.title?.slice(0, 35) || source.url}
      <span style={{ marginLeft: 'auto', opacity: 0.5, fontSize: 10 }}>
        {Math.round(source.score * 100)}%
      </span>
    </a>
  )
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 1500)
      }}
      style={{
        background: 'none', border: '1px solid var(--border)',
        borderRadius: 4, padding: '2px 8px',
        color: copied ? 'var(--green)' : 'var(--text-muted)',
        fontFamily: 'var(--font-mono)', fontSize: 11, cursor: 'pointer',
        transition: 'all var(--transition)',
      }}
    >
      {copied ? '✓ copied' : 'copy'}
    </button>
  )
}

export function Message({ message }) {
  const isUser = message.role === 'user'
  const hasSources = message.sources?.length > 0
  const hasError = !!message.error

  return (
    <div style={{
      animation: 'fadeSlideUp 0.2s ease forwards',
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      alignItems: isUser ? 'flex-end' : 'flex-start',
    }}>
      {/* Avatar + Role label */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        flexDirection: isUser ? 'row-reverse' : 'row',
      }}>
        <div style={{
          width: 28, height: 28,
          borderRadius: isUser ? 6 : '50%',
          background: isUser ? 'var(--orange-dim)' : 'var(--bg-elevated)',
          border: `1px solid ${isUser ? 'var(--orange)' : 'var(--border)'}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 12, flexShrink: 0,
        }}>
          {isUser ? '◈' : GITLAB_ICON}
        </div>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          {isUser ? 'you' : 'gitbot'}
        </span>
        <span style={{ fontSize: 10, color: 'var(--text-muted)', opacity: 0.6 }}>
          {message.timestamp?.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>

      {/* Message bubble */}
      <div style={{
        maxWidth: '82%',
        padding: isUser ? '10px 14px' : '14px 18px',
        background: isUser ? 'var(--orange-dim)' : 'var(--bg-surface)',
        border: `1px solid ${isUser ? 'rgba(252,109,38,0.25)' : 'var(--border)'}`,
        borderRadius: isUser
          ? 'var(--radius-lg) var(--radius) var(--radius-lg) var(--radius-lg)'
          : 'var(--radius) var(--radius-lg) var(--radius-lg) var(--radius-lg)',
        position: 'relative',
      }}>
        {hasError ? (
          <div style={{ color: 'var(--red)', fontSize: 13 }}>
            ⚠ {message.error}
          </div>
        ) : message.streaming && !message.content ? (
          <TypingIndicator />
        ) : (
          <>
            {!isUser && (
              <div style={{ position: 'absolute', top: 10, right: 12 }}>
                <CopyButton text={message.content} />
              </div>
            )}
            <div className="markdown-body" style={{
              fontSize: 13.5,
              lineHeight: 1.75,
              color: 'var(--text-primary)',
            }}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ inline, children, ...props }) {
                    return inline ? (
                      <code style={{
                        background: 'var(--bg-elevated)',
                        border: '1px solid var(--border)',
                        borderRadius: 3,
                        padding: '1px 5px',
                        fontSize: '0.88em',
                        color: 'var(--orange)',
                      }} {...props}>{children}</code>
                    ) : (
                      <pre style={{
                        background: 'var(--bg-base)',
                        border: '1px solid var(--border)',
                        borderRadius: 6,
                        padding: '12px 14px',
                        overflowX: 'auto',
                        margin: '8px 0',
                      }}>
                        <code style={{ fontSize: '0.85em', color: 'var(--text-primary)' }} {...props}>{children}</code>
                      </pre>
                    )
                  },
                  a({ href, children }) {
                    return (
                      <a href={href} target="_blank" rel="noopener noreferrer"
                        style={{ color: 'var(--orange)', textDecoration: 'underline', textDecorationStyle: 'dotted' }}>
                        {children}
                      </a>
                    )
                  },
                  ul({ children }) {
                    return <ul style={{ paddingLeft: 20, margin: '6px 0' }}>{children}</ul>
                  },
                  ol({ children }) {
                    return <ol style={{ paddingLeft: 20, margin: '6px 0' }}>{children}</ol>
                  },
                  li({ children }) {
                    return <li style={{ margin: '3px 0' }}>{children}</li>
                  },
                  h1({ children }) { return <h1 style={{ fontSize: 18, fontFamily: 'var(--font-serif)', fontWeight: 500, margin: '12px 0 6px' }}>{children}</h1> },
                  h2({ children }) { return <h2 style={{ fontSize: 15, fontFamily: 'var(--font-serif)', fontWeight: 500, margin: '10px 0 5px' }}>{children}</h2> },
                  h3({ children }) { return <h3 style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--orange)', margin: '8px 0 4px' }}>{children}</h3> },
                  blockquote({ children }) {
                    return (
                      <blockquote style={{
                        borderLeft: '3px solid var(--orange)',
                        paddingLeft: 12, margin: '8px 0',
                        color: 'var(--text-secondary)',
                      }}>{children}</blockquote>
                    )
                  },
                  strong({ children }) {
                    return <strong style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{children}</strong>
                  },
                  p({ children }) {
                    return <p style={{ margin: '6px 0' }}>{children}</p>
                  },
                  table({ children }) {
                    return (
                      <div style={{ overflowX: 'auto', margin: '8px 0' }}>
                        <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 12.5 }}>{children}</table>
                      </div>
                    )
                  },
                  th({ children }) {
                    return <th style={{ border: '1px solid var(--border)', padding: '6px 10px', background: 'var(--bg-elevated)', textAlign: 'left' }}>{children}</th>
                  },
                  td({ children }) {
                    return <td style={{ border: '1px solid var(--border)', padding: '6px 10px' }}>{children}</td>
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
              {message.streaming && (
                <span style={{
                  display: 'inline-block', width: 2, height: '1em',
                  background: 'var(--orange)', marginLeft: 2, verticalAlign: 'middle',
                  animation: 'blink 0.8s step-end infinite',
                }} />
              )}
            </div>
          </>
        )}
      </div>

      {/* Sources */}
      {hasSources && (
        <div style={{
          display: 'flex', flexWrap: 'wrap', gap: 6,
          maxWidth: '82%',
          animation: 'fadeSlideUp 0.3s ease forwards',
        }}>
          <span style={{ fontSize: 10, color: 'var(--text-muted)', alignSelf: 'center', marginRight: 2 }}>
            sources →
          </span>
          {message.sources.map((s, i) => <SourceBadge key={i} source={s} />)}
        </div>
      )}
    </div>
  )
}
