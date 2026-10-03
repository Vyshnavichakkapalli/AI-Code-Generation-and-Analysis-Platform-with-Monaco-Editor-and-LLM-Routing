/**
 * History view component.
 * Displays paginated request history from the database.
 */

import { useState, useEffect } from 'react'
import { getHistory } from '../api/client'
import { FiRefreshCw, FiClock, FiCode, FiSearch } from 'react-icons/fi'

function formatRelativeTime(isoString) {
  if (!isoString) return ''
  const now = new Date()
  const then = new Date(isoString)
  const diffMs = now - then
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  return then.toLocaleDateString()
}

function HistoryCard({ item, onClick }) {
  const endpointClass = `history-card__endpoint history-card__endpoint--${item.endpoint_used}`
  const truncatedInput = item.user_input?.length > 80
    ? item.user_input.slice(0, 80) + '…'
    : item.user_input

  return (
    <div
      className="history-card"
      onClick={() => onClick(item)}
      id={`history-item-${item.id}`}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick(item)}
    >
      <div className="history-card__meta">
        <span className={endpointClass}>{item.endpoint_used}</span>
        <span className="history-card__lang">{item.language}</span>
        {item.task_type && (
          <span className="history-card__lang" style={{ opacity: 0.7 }}>{item.task_type}</span>
        )}
        <span className="history-card__time">
          <FiClock size={10} style={{ marginRight: 3 }} />
          {formatRelativeTime(item.created_at)}
        </span>
      </div>
      <div className="history-card__input">
        <FiCode size={11} style={{ marginRight: 4, opacity: 0.5 }} />
        {truncatedInput}
      </div>
      {item.model_routed_to && (
        <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{
            fontSize: '0.65rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-tertiary)',
            background: 'var(--bg-overlay)',
            padding: '1px 6px',
            borderRadius: '4px',
          }}>
            {item.model_routed_to}
          </span>
        </div>
      )}
    </div>
  )
}

function HistoryDetailModal({ item, onClose }) {
  if (!item) return null

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.7)',
        backdropFilter: 'blur(8px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        animation: 'fade-in 150ms ease-out',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-soft)',
          borderRadius: 'var(--radius-xl)',
          padding: '24px',
          maxWidth: '700px',
          width: '100%',
          maxHeight: '80vh',
          overflow: 'auto',
          boxShadow: 'var(--shadow-lg)',
        }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
              Request Detail
            </h3>
            <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>
              {item.id}
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'var(--bg-overlay)',
              border: 'none',
              color: 'var(--text-secondary)',
              borderRadius: 'var(--radius-sm)',
              padding: '6px 12px',
              cursor: 'pointer',
              fontSize: '0.8rem',
            }}
          >
            Close
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
          {[
            { label: 'Endpoint', value: item.endpoint_used },
            { label: 'Language', value: item.language },
            { label: 'Task Type', value: item.task_type || '—' },
            { label: 'Model', value: item.model_routed_to },
          ].map(({ label, value }) => (
            <div key={label} style={{ background: 'var(--bg-glass)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-tertiary)', marginBottom: '4px' }}>
                {label}
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                {value}
              </div>
            </div>
          ))}
        </div>

        <div style={{ marginBottom: '12px' }}>
          <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-tertiary)', marginBottom: '8px' }}>
            Input
          </div>
          <pre style={{
            background: 'var(--bg-deep)',
            padding: '12px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.8rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-secondary)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            maxHeight: '200px',
            overflow: 'auto',
            border: '1px solid var(--border-subtle)',
          }}>
            {item.user_input}
          </pre>
        </div>

        <div>
          <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-tertiary)', marginBottom: '8px' }}>
            Response Payload
          </div>
          <pre style={{
            background: 'var(--bg-deep)',
            padding: '12px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.75rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-secondary)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            maxHeight: '300px',
            overflow: 'auto',
            border: '1px solid var(--border-subtle)',
          }}>
            {JSON.stringify(item.response_payload, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  )
}

function History() {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedItem, setSelectedItem] = useState(null)
  const [filter, setFilter] = useState('')

  const fetchHistory = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getHistory(100, 0)
      const list = Array.isArray(data) ? data : (data.items || [])
      setItems(list)
      setTotal(Array.isArray(data) ? data.length : (data.total || list.length))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchHistory() }, [])

  const filtered = filter
    ? items.filter(item =>
        item.user_input?.toLowerCase().includes(filter.toLowerCase()) ||
        item.language?.toLowerCase().includes(filter.toLowerCase()) ||
        item.endpoint_used?.toLowerCase().includes(filter.toLowerCase())
      )
    : items

  return (
    <div className="history-view">
      <div className="history-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h2>Request History</h2>
            <div className="history-subtitle">{total} total requests stored in PostgreSQL</div>
          </div>
          <button
            className="btn btn-ghost"
            onClick={fetchHistory}
            disabled={loading}
            id="refresh-history-btn"
          >
            <FiRefreshCw size={14} className={loading ? 'spin' : ''} />
            Refresh
          </button>
        </div>

        {/* Filter */}
        <div style={{ position: 'relative', marginTop: '16px' }}>
          <FiSearch size={14} style={{
            position: 'absolute',
            left: '12px',
            top: '50%',
            transform: 'translateY(-50%)',
            color: 'var(--text-tertiary)',
          }} />
          <input
            type="text"
            placeholder="Filter by language, endpoint, or content…"
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="control-input"
            style={{ paddingLeft: '36px' }}
            id="history-filter-input"
          />
        </div>
      </div>

      {error && (
        <div style={{
          padding: '16px',
          background: 'var(--accent-danger-dim)',
          border: '1px solid rgba(239, 68, 68, 0.2)',
          borderRadius: 'var(--radius-md)',
          color: 'var(--accent-danger)',
          fontSize: '0.875rem',
          marginBottom: '16px',
        }}>
          ⚠️ {error}
        </div>
      )}

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '48px', color: 'var(--text-tertiary)' }}>
          <div style={{ width: 24, height: 24, border: '2px solid var(--border-soft)', borderTopColor: 'var(--accent-primary)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
        </div>
      ) : (
        <div className="history-list">
          {filtered.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px', color: 'var(--text-tertiary)' }}>
              {filter ? 'No results match your filter' : 'No history yet — generate or analyze some code!'}
            </div>
          ) : (
            filtered.map(item => (
              <HistoryCard key={item.id} item={item} onClick={setSelectedItem} />
            ))
          )}
        </div>
      )}

      {selectedItem && (
        <HistoryDetailModal item={selectedItem} onClose={() => setSelectedItem(null)} />
      )}
    </div>
  )
}

export default History
