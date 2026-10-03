/**
 * Results panel component.
 * Displays synthesized static analysis + LLM feedback with rich UI.
 */

import { useState } from 'react'
import { FiAlertTriangle, FiShield, FiCpu, FiCopy, FiCheck, FiChevronDown, FiChevronUp } from 'react-icons/fi'

/* ─── Helpers ─────────────────────────────────────────────────────────────── */

function getSeverityClass(severity = '') {
  const s = severity.toLowerCase()
  if (s === 'critical' || s === 'error') return 'critical'
  if (s === 'high') return 'high'
  if (s === 'warning' || s === 'medium') return s
  if (s === 'low' || s === 'info' || s === 'convention') return s
  return 'medium'
}

function formatTime(isoString) {
  if (!isoString) return ''
  return new Date(isoString).toLocaleTimeString()
}

/* ─── Copy Button ─────────────────────────────────────────────────────────── */
function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      console.warn('Copy failed')
    }
  }

  return (
    <button
      className={`copy-btn ${copied ? 'copied' : ''}`}
      onClick={handleCopy}
      aria-label="Copy to clipboard"
      id="copy-code-btn"
    >
      {copied ? <FiCheck size={11} /> : <FiCopy size={11} />}
      {copied ? 'Copied!' : 'Copy'}
    </button>
  )
}

/* ─── Model Routing Badge ────────────────────────────────────────────────── */
function ModelBadge({ model }) {
  if (!model) return null
  const isReasoning = model.includes('gpt') || model.includes('gemini') || model.includes('claude')
  return (
    <span className={`model-badge ${isReasoning ? 'model-badge--reasoning' : 'model-badge--fast'}`}>
      <FiCpu size={10} />
      {model}
    </span>
  )
}

/* ─── Static Analysis Issue Card ─────────────────────────────────────────── */
function StaticIssueCard({ issue, index }) {
  const severityClass = getSeverityClass(issue.type)
  return (
    <div
      className={`issue-card issue-card--${severityClass}`}
      id={`static-issue-${index}`}
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className="issue-card__line-badge">
        L{issue.line_number}
      </div>
      <div className="issue-card__content">
        <div className="issue-card__type">
          {issue.type || 'lint'}{issue.rule ? ` · ${issue.rule}` : ''}
        </div>
        <div className="issue-card__message">{issue.message}</div>
        {issue.column != null && issue.column > 0 && (
          <span className="issue-card__rule">col {issue.column}</span>
        )}
      </div>
    </div>
  )
}

/* ─── LLM Feedback Card ──────────────────────────────────────────────────── */
function LLMIssueCard({ issue, index }) {
  const [expanded, setExpanded] = useState(true)
  const severityClass = getSeverityClass(issue.severity)

  return (
    <div
      className={`issue-card issue-card--${severityClass}`}
      id={`llm-issue-${index}`}
      style={{ flexDirection: 'column', animationDelay: `${index * 40}ms` }}
    >
      <div
        style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
        onClick={() => setExpanded(e => !e)}
      >
        <div className="issue-card__content" style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span className="issue-card__type">{issue.issue_type}</span>
            <span className={`severity-badge severity-badge--${severityClass}`}>
              {issue.severity || 'medium'}
            </span>
          </div>
          <div className="issue-card__message">{issue.description}</div>
        </div>
        <span style={{ color: 'var(--text-tertiary)', flexShrink: 0 }}>
          {expanded ? <FiChevronUp size={14} /> : <FiChevronDown size={14} />}
        </span>
      </div>

      {expanded && issue.suggested_fix && (
        <div className="issue-card__fix">
          <div className="issue-card__fix-label">💡 Suggested Fix</div>
          {issue.suggested_fix}
        </div>
      )}
    </div>
  )
}

/* ─── Generated Code Output ──────────────────────────────────────────────── */
function GeneratedCodeOutput({ result }) {
  if (!result) return null

  return (
    <div className="code-output">
      <div className="code-output__header">
        <span className="code-output__lang">Generated Code</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ModelBadge model={result.routed_model} />
          <CopyButton text={result.code} />
        </div>
      </div>
      <pre className="code-output__content">{result.code}</pre>
      {result.explanation && (
        <div style={{
          padding: '12px 16px',
          background: 'rgba(99, 102, 241, 0.04)',
          borderTop: '1px solid var(--border-subtle)',
          fontSize: '0.825rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.6,
        }}>
          <span style={{ color: 'var(--accent-primary-light)', fontWeight: 600, fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            AI Note
          </span>
          <p style={{ marginTop: '4px' }}>{result.explanation}</p>
        </div>
      )}
    </div>
  )
}

/* ─── Main Results Component ─────────────────────────────────────────────── */
function Results({ result, mode, isLoading }) {
  if (isLoading) {
    return (
      <div className="results-panel">
        <div className="empty-state">
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
            <div style={{
              width: 48,
              height: 48,
              border: '3px solid rgba(99, 102, 241, 0.2)',
              borderTopColor: 'var(--accent-primary)',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
            }} />
            <div>
              <div className="empty-state__title" style={{ marginBottom: '8px' }}>
                {mode === 'generate' ? '⚡ Generating code…' : '🔍 Analyzing code…'}
              </div>
              <div className="empty-state__subtitle">
                {mode === 'generate'
                  ? 'Routing to optimal LLM based on task type'
                  : 'Running static analysis + LLM review concurrently'}
              </div>
            </div>
            <div className="loading-bar" style={{ width: '200px', borderRadius: '999px', overflow: 'hidden' }} />
          </div>
        </div>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="results-panel">
        <div className="empty-state">
          <div className="empty-state__icon">🤖</div>
          <div className="empty-state__title">Results appear here</div>
          <div className="empty-state__subtitle">
            Write a prompt and click <strong>Generate</strong> to create code,
            or paste code and click <strong>Analyze</strong> to get AI feedback with static analysis.
          </div>
        </div>
      </div>
    )
  }

  /* ── Analysis Results ── */
  if (mode === 'analyze' && result.static_analysis !== undefined) {
    const staticCount = result.static_analysis?.length || 0
    const llmCount = result.llm_feedback?.length || 0

    return (
      <div className="results-panel">
        {/* Summary bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '12px 16px',
          background: 'var(--bg-glass)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          marginBottom: '4px',
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-tertiary)', marginBottom: '6px' }}>
              Analysis Summary
            </div>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  🔬 {staticCount} static issue{staticCount !== 1 ? 's' : ''}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  🧠 {llmCount} AI insight{llmCount !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
          </div>
          <ModelBadge model={result.routed_model} />
        </div>

        {/* Static Analysis Section */}
        <div className="result-section" id="static-analysis-results">
          <div className="result-section__header">
            <div className="result-section__title" style={{ color: 'var(--accent-warning)' }}>
              <FiAlertTriangle size={13} />
              Static Analysis (Pylint / ESLint)
            </div>
            <span className="result-section__count">{staticCount}</span>
          </div>
          <div className="issue-list">
            {staticCount === 0 ? (
              <div style={{ padding: '16px', textAlign: 'center', color: 'var(--accent-success)', fontSize: '0.825rem' }}>
                ✅ No static analysis issues found!
              </div>
            ) : (
              result.static_analysis.map((issue, i) => (
                <StaticIssueCard key={i} issue={issue} index={i} />
              ))
            )}
          </div>
        </div>

        {/* LLM Feedback Section */}
        <div className="result-section" id="llm-feedback-results">
          <div className="result-section__header">
            <div className="result-section__title" style={{ color: 'var(--accent-purple)' }}>
              <FiShield size={13} />
              AI Code Review
            </div>
            <span className="result-section__count">{llmCount}</span>
          </div>
          <div className="issue-list">
            {llmCount === 0 ? (
              <div style={{ padding: '16px', textAlign: 'center', color: 'var(--accent-success)', fontSize: '0.825rem' }}>
                ✅ No issues detected by AI review!
              </div>
            ) : (
              result.llm_feedback.map((issue, i) => (
                <LLMIssueCard key={i} issue={issue} index={i} />
              ))
            )}
          </div>
        </div>
      </div>
    )
  }

  /* ── Generation Results ── */
  if (mode === 'generate' && result.code !== undefined) {
    return (
      <div className="results-panel">
        <GeneratedCodeOutput result={result} />
        {result.request_id && (
          <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
            req: {result.request_id}
          </div>
        )}
      </div>
    )
  }

  return null
}

export default Results
