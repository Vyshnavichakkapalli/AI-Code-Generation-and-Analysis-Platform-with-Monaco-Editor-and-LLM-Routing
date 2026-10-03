/**
 * Main Application Component
 * AI Code Generation and Analysis Platform
 */

import { useState, useCallback, useEffect } from 'react'
import { Toaster, toast } from 'react-hot-toast'
import { FiZap, FiSearch, FiClock, FiCode, FiTrash2, FiDownload } from 'react-icons/fi'

import Editor from './components/Editor'
import Results from './components/Results'
import History from './components/History'
import { generateCode, analyzeCode, checkHealth } from './api/client'

/* ─── Language Configuration ─────────────────────────────────────────────── */
const LANGUAGES = [
  { value: 'python',     label: 'Python',     monacoId: 'python' },
  { value: 'javascript', label: 'JavaScript',  monacoId: 'javascript' },
  { value: 'typescript', label: 'TypeScript',  monacoId: 'typescript' },
  { value: 'jsx',        label: 'React (JSX)', monacoId: 'javascript' },
  { value: 'sql',        label: 'SQL',         monacoId: 'sql' },
  { value: 'go',         label: 'Go',          monacoId: 'go' },
  { value: 'rust',       label: 'Rust',        monacoId: 'rust' },
  { value: 'java',       label: 'Java',        monacoId: 'java' },
  { value: 'cpp',        label: 'C++',         monacoId: 'cpp' },
]

const GENERATE_TASK_TYPES = [
  { value: 'boilerplate',  label: 'Boilerplate / Scaffold' },
  { value: 'unit_test',    label: 'Unit Tests' },
  { value: 'docstring',    label: 'Add Docstrings' },
  { value: 'format',       label: 'Format Code' },
  { value: 'refactor',     label: 'Refactor' },
  { value: 'completion',   label: 'Complete Code' },
  { value: 'translate',    label: 'Translate Language' },
]

const ANALYZE_TASK_TYPES = [
  { value: 'code_review',     label: 'Code Review' },
  { value: 'bug_hunt',        label: 'Bug Hunt' },
  { value: 'security_audit',  label: 'Security Audit' },
]

const PLACEHOLDER_CODE = {
  python: `# Paste your Python code here for analysis
def calculate_fibonacci(n):
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    
    sequence = [0, 1]
    for i in range(2, n):
        next_val = sequence[i-1] + sequence[i-2]
        sequence.append(next_val)
    
    return sequence

result = calculate_fibonacci(10)
print(result)
`,
  javascript: `// Paste your JavaScript code here for analysis
function fetchUserData(userId) {
  return fetch(\`/api/users/\${userId}\`)
    .then(response => response.json())
    .then(data => {
      console.log(data)
      return data
    })
}

var users = []
fetchUserData(1)
`,
}

/* ─── App ─────────────────────────────────────────────────────────────────── */
function App() {
  const [activeView, setActiveView] = useState('editor') // 'editor' | 'history'
  const [language, setLanguage] = useState('python')
  const [taskType, setTaskType] = useState('boilerplate')
  const [analyzeTaskType, setAnalyzeTaskType] = useState('code_review')
  const [prompt, setPrompt] = useState('')
  const [code, setCode] = useState(PLACEHOLDER_CODE.python)
  const [result, setResult] = useState(null)
  const [lastMode, setLastMode] = useState(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [backendStatus, setBackendStatus] = useState('checking')

  // Get Monaco language ID
  const monacoLang = LANGUAGES.find(l => l.value === language)?.monacoId || language

  // Check backend health on mount
  useEffect(() => {
    checkHealth()
      .then(() => setBackendStatus('online'))
      .catch(() => setBackendStatus('offline'))
  }, [])

  // Update code placeholder when language changes
  const handleLanguageChange = useCallback((e) => {
    const newLang = e.target.value
    setLanguage(newLang)
    if (!code || code === PLACEHOLDER_CODE[language]) {
      setCode(PLACEHOLDER_CODE[newLang] || '')
    }
  }, [code, language])

  // ── Generate Code ───────────────────────────────────────────────────────
  const handleGenerate = async () => {
    if (!prompt.trim()) {
      toast.error('Please enter a prompt describing what to generate')
      return
    }
    setIsGenerating(true)
    setResult(null)
    setLastMode('generate')

    const toastId = toast.loading('⚡ Routing to optimal model…')
    try {
      const data = await generateCode({
        prompt: prompt.trim(),
        language,
        task_type: taskType,
        code_context: code,
      })
      setResult(data)
      // Auto-populate editor with generated code
      if (data.code) {
        setCode(data.code)
      }
      toast.success(`✓ Generated via ${data.routed_model}`, { id: toastId, duration: 4000 })
    } catch (err) {
      toast.error(err.message || 'Generation failed', { id: toastId, duration: 6000 })
    } finally {
      setIsGenerating(false)
    }
  }

  // ── Analyze Code ────────────────────────────────────────────────────────
  const handleAnalyze = async () => {
    if (!code.trim()) {
      toast.error('Please paste some code in the editor to analyze')
      return
    }
    setIsAnalyzing(true)
    setResult(null)
    setLastMode('analyze')

    const toastId = toast.loading('🔍 Running static analysis + AI review…')
    try {
      const data = await analyzeCode({
        code: code.trim(),
        language,
        task_type: analyzeTaskType,
      })
      setResult(data)
      const staticCount = data.static_analysis?.length || 0
      const llmCount = data.llm_feedback?.length || 0
      toast.success(
        `✓ Found ${staticCount} static + ${llmCount} AI issues via ${data.routed_model}`,
        { id: toastId, duration: 5000 }
      )
    } catch (err) {
      toast.error(err.message || 'Analysis failed', { id: toastId, duration: 6000 })
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleClearCode = () => {
    setCode('')
    setResult(null)
    toast.success('Editor cleared')
  }

  const handleDownloadCode = () => {
    if (!code) return
    const ext = language === 'python' ? 'py' : language === 'javascript' ? 'js' : language
    const blob = new Blob([code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `generated.${ext}`
    a.click()
    URL.revokeObjectURL(url)
  }

  const isLoading = isGenerating || isAnalyzing

  return (
    <div className="app">
      {/* ─── Header ─────────────────────────────────────────────────────── */}
      <header className="header" role="banner">
        <div className="header__logo">
          <div className="header__logo-icon" aria-hidden="true">⚡</div>
          <span className="header__logo-text">AI Code Platform</span>
          <span className="header__badge">Monaco + LLM</span>
        </div>

        <nav className="header__nav" aria-label="Main navigation">
          <button
            id="nav-editor-btn"
            className={`header__nav-btn ${activeView === 'editor' ? 'active' : ''}`}
            onClick={() => setActiveView('editor')}
            aria-current={activeView === 'editor' ? 'page' : undefined}
          >
            <FiCode size={14} />
            Editor
          </button>
          <button
            id="nav-history-btn"
            className={`header__nav-btn ${activeView === 'history' ? 'active' : ''}`}
            onClick={() => setActiveView('history')}
            aria-current={activeView === 'history' ? 'page' : undefined}
          >
            <FiClock size={14} />
            History
          </button>
        </nav>
      </header>

      {activeView === 'editor' ? (
        <main className="main" aria-label="Code editor workspace">
          {/* ─── Control Panel ─────────────────────────────────────────── */}
          <section className="control-panel" aria-label="Editor controls">
            {/* Language Selector */}
            <div className="control-group">
              <label className="control-label" htmlFor="language-select">Language</label>
              <select
                id="language-select"
                className="control-select"
                value={language}
                onChange={handleLanguageChange}
                disabled={isLoading}
              >
                {LANGUAGES.map(lang => (
                  <option key={lang.value} value={lang.value}>{lang.label}</option>
                ))}
              </select>
            </div>

            {/* Generate Task Type */}
            <div className="control-group">
              <label className="control-label" htmlFor="task-type-select">Generate Task</label>
              <select
                id="task-type-select"
                className="control-select"
                value={taskType}
                onChange={e => setTaskType(e.target.value)}
                disabled={isLoading}
              >
                {GENERATE_TASK_TYPES.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>

            {/* Analyze Task Type */}
            <div className="control-group">
              <label className="control-label" htmlFor="analyze-type-select">Analyze Type</label>
              <select
                id="analyze-type-select"
                className="control-select"
                value={analyzeTaskType}
                onChange={e => setAnalyzeTaskType(e.target.value)}
                disabled={isLoading}
              >
                {ANALYZE_TASK_TYPES.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>

            {/* Generate Button */}
            <button
              id="generate-btn"
              className="btn btn-generate"
              onClick={handleGenerate}
              disabled={isLoading}
              aria-label="Generate code from prompt"
            >
              {isGenerating ? (
                <><span className="btn-spinner" /><span>Generating…</span></>
              ) : (
                <><FiZap size={15} /><span>Generate</span></>
              )}
            </button>

            {/* Analyze Button */}
            <button
              id="analyze-btn"
              className="btn btn-analyze"
              onClick={handleAnalyze}
              disabled={isLoading}
              aria-label="Analyze code in editor"
            >
              {isAnalyzing ? (
                <><span className="btn-spinner" /><span>Analyzing…</span></>
              ) : (
                <><FiSearch size={15} /><span>Analyze</span></>
              )}
            </button>
          </section>

          {/* ─── Workspace ─────────────────────────────────────────────── */}
          <div className="workspace">
            {/* ── Left: Editor Panel ── */}
            <div className="panel panel--accent">
              {/* Panel header */}
              <div className="panel__header">
                <div className="panel__title">
                  <div className="panel__title-dot" />
                  Monaco Editor
                  <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', textTransform: 'none', fontWeight: 400, letterSpacing: 0 }}>
                    — {monacoLang}
                  </span>
                </div>
                <div className="panel__actions">
                  <button
                    className="btn btn-ghost"
                    style={{ height: 28, padding: '0 10px', fontSize: '0.75rem' }}
                    onClick={handleDownloadCode}
                    disabled={!code}
                    data-tooltip="Download code"
                    id="download-code-btn"
                  >
                    <FiDownload size={12} />
                  </button>
                  <button
                    className="btn btn-ghost"
                    style={{ height: 28, padding: '0 10px', fontSize: '0.75rem' }}
                    onClick={handleClearCode}
                    data-tooltip="Clear editor"
                    id="clear-code-btn"
                  >
                    <FiTrash2 size={12} />
                  </button>
                </div>
              </div>

              {/* Prompt area */}
              <div className="prompt-area">
                <textarea
                  id="prompt-input"
                  className="prompt-textarea"
                  placeholder="Describe what to generate… e.g. 'Write a Python class for a binary search tree with insert, search, and delete methods'"
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleGenerate()
                  }}
                  disabled={isLoading}
                  aria-label="Natural language prompt for code generation"
                />
              </div>

              {/* Monaco Editor */}
              <div className="editor-container">
                <Editor
                  value={code}
                  onChange={setCode}
                  language={monacoLang}
                />
              </div>
            </div>

            {/* ── Right: Results Panel ── */}
            <div className="panel">
              <div className="panel__header">
                <div className="panel__title">
                  <div className="panel__title-dot" style={{ background: lastMode === 'analyze' ? 'var(--accent-secondary)' : 'var(--accent-purple)' }} />
                  {lastMode === 'analyze' ? 'Analysis Results' : 'Generated Output'}
                </div>
                {result && (
                  <div className="panel__actions">
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>
                      {lastMode === 'analyze'
                        ? `${result.static_analysis?.length || 0} static · ${result.llm_feedback?.length || 0} AI`
                        : `${result.code?.split('\n').length || 0} lines`
                      }
                    </span>
                  </div>
                )}
              </div>
              <Results
                result={result}
                mode={lastMode}
                isLoading={isLoading}
              />
            </div>
          </div>
        </main>
      ) : (
        <main className="main" aria-label="Request history">
          <div className="panel" style={{ flex: 1 }}>
            <History />
          </div>
        </main>
      )}

      {/* ─── Status Bar ─────────────────────────────────────────────────── */}
      <footer className="status-bar" role="contentinfo">
        <div className="status-bar__item">
          <div className={`status-indicator status-indicator--${
            backendStatus === 'online' ? 'green' :
            backendStatus === 'offline' ? 'red' : 'yellow'
          }`} />
          <span>Backend {backendStatus}</span>
        </div>
        <div className="status-bar__item">
          <span>Language: <strong>{language}</strong></span>
        </div>
        <div className="status-bar__item" style={{ marginLeft: 'auto' }}>
          <span style={{ color: 'var(--text-tertiary)' }}>
            ⌘+Enter to Generate
          </span>
        </div>
      </footer>

      {/* Toast notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--bg-elevated)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-soft)',
            borderRadius: '10px',
            fontSize: '0.85rem',
            fontFamily: 'Inter, sans-serif',
          },
          success: {
            iconTheme: { primary: '#10b981', secondary: '#10151f' },
          },
          error: {
            iconTheme: { primary: '#ef4444', secondary: '#10151f' },
          },
        }}
      />
    </div>
  )
}

export default App
