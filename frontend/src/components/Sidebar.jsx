import React from 'react'

export function Sidebar({ onClear, messageCount }) {
  return (
    <aside style={{
      width: 220,
      flexShrink: 0,
      display: 'flex',
      flexDirection: 'column',
      borderRight: '1px solid var(--border)',
      background: 'var(--bg-surface)',
      padding: '24px 16px',
      gap: 24,
    }}>
      {/* Brand */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
          <div style={{
            width: 32, height: 32,
            background: 'var(--orange)',
            borderRadius: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 18,
          }}>
            <svg width="20" height="20" viewBox="0 0 380 380" fill="none">
              <path d="M190 380L257 173H123L190 380Z" fill="white"/>
              <path d="M190 380L123 173H24L190 380Z" fill="white" opacity="0.7"/>
              <path d="M24 173L3 237C1 243 3 250 8 254L190 380L24 173Z" fill="white" opacity="0.5"/>
              <path d="M24 173H123L79 41C76 32 63 32 60 41L24 173Z" fill="white" opacity="0.85"/>
              <path d="M190 380L257 173H356L190 380Z" fill="white" opacity="0.7"/>
              <path d="M356 173L377 237C379 243 377 250 372 254L190 380L356 173Z" fill="white" opacity="0.5"/>
              <path d="M356 173H257L301 41C304 32 317 32 320 41L356 173Z" fill="white" opacity="0.85"/>
            </svg>
          </div>
          <div>
            <div style={{
              fontFamily: 'var(--font-serif)',
              fontSize: 18,
              fontWeight: 500,
              color: 'var(--text-primary)',
              letterSpacing: '-0.02em',
            }}>
              GitBot
            </div>
          </div>
        </div>
        <p style={{
          fontSize: 11,
          color: 'var(--text-muted)',
          lineHeight: 1.5,
          paddingLeft: 42,
        }}>
          Knowledge assistant for GitLab Handbook & Direction
        </p>
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: 'var(--border)' }} />

      {/* Source legend */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Sources
        </p>
        {[
          { color: '#2ea04b', label: 'Handbook', desc: 'Policies, culture, processes' },
          { color: '#58a6ff', label: 'Direction', desc: 'Product roadmap & strategy' },
        ].map(({ color, label, desc }) => (
          <div key={label} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: color, flexShrink: 0, marginTop: 4,
            }} />
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-primary)' }}>{label}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{desc}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: 'var(--border)' }} />

      {/* Stats */}
      {messageCount > 0 && (
        <div style={{
          padding: '10px 12px',
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          borderRadius: 8,
          fontSize: 11,
          color: 'var(--text-muted)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span>Messages</span>
            <span style={{ color: 'var(--text-primary)' }}>{messageCount}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>Session</span>
            <span style={{ color: 'var(--green)' }}>active</span>
          </div>
        </div>
      )}

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Actions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {messageCount > 0 && (
          <button
            onClick={onClear}
            style={{
              padding: '8px 12px',
              background: 'transparent',
              border: '1px solid var(--border)',
              borderRadius: 6,
              color: 'var(--text-muted)',
              fontSize: 12,
              cursor: 'pointer',
              fontFamily: 'var(--font-mono)',
              textAlign: 'left',
              transition: 'all var(--transition)',
              display: 'flex', alignItems: 'center', gap: 8,
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = 'var(--red)'
              e.currentTarget.style.color = 'var(--red)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = 'var(--border)'
              e.currentTarget.style.color = 'var(--text-muted)'
            }}
          >
            ⊗ clear chat
          </button>
        )}
        <a
          href="https://handbook.gitlab.com"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            padding: '8px 12px',
            background: 'transparent',
            border: '1px solid var(--border)',
            borderRadius: 6,
            color: 'var(--text-muted)',
            fontSize: 12,
            textDecoration: 'none',
            fontFamily: 'var(--font-mono)',
            display: 'flex', alignItems: 'center', gap: 8,
            transition: 'all var(--transition)',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = 'var(--border-bright)'
            e.currentTarget.style.color = 'var(--text-primary)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = 'var(--border)'
            e.currentTarget.style.color = 'var(--text-muted)'
          }}
        >
          ↗ handbook.gitlab.com
        </a>
      </div>
    </aside>
  )
}
