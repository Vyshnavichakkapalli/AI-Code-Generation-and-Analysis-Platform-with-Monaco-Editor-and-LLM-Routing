/**
 * Monaco Editor wrapper component.
 * Provides VS Code-like editing experience with language-aware syntax highlighting.
 */

import { useRef, useCallback } from 'react'
import MonacoEditor from '@monaco-editor/react'

const MONACO_OPTIONS = {
  fontSize: 13,
  fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
  fontLigatures: true,
  lineHeight: 22,
  minimap: { enabled: true, maxColumn: 60 },
  scrollBeyondLastLine: false,
  automaticLayout: true,
  tabSize: 2,
  insertSpaces: true,
  wordWrap: 'on',
  renderWhitespace: 'selection',
  bracketPairColorization: { enabled: true },
  guides: { bracketPairs: true, indentation: true },
  cursorBlinking: 'phase',
  cursorSmoothCaretAnimation: 'on',
  smoothScrolling: true,
  overviewRulerBorder: false,
  renderLineHighlight: 'all',
  renderLineHighlightOnlyWhenFocus: false,
  padding: { top: 12, bottom: 12 },
  scrollbar: {
    verticalScrollbarSize: 6,
    horizontalScrollbarSize: 6,
    useShadows: false,
  },
  suggest: {
    showKeywords: true,
    showSnippets: true,
  },
  quickSuggestions: { other: true, comments: false, strings: false },
}

const MONACO_THEME_DATA = {
  base: 'vs-dark',
  inherit: true,
  rules: [
    { token: 'comment', foreground: '4a5568', fontStyle: 'italic' },
    { token: 'keyword', foreground: '818cf8' },
    { token: 'string', foreground: '34d399' },
    { token: 'number', foreground: 'f59e0b' },
    { token: 'type', foreground: '06b6d4' },
    { token: 'function', foreground: 'a78bfa' },
    { token: 'variable', foreground: 'e2e8f0' },
    { token: 'class', foreground: 'f472b6' },
    { token: 'operator', foreground: '94a3b8' },
  ],
  colors: {
    'editor.background': '#10151f',
    'editor.foreground': '#e2e8f0',
    'editor.lineHighlightBackground': '#1a2035',
    'editor.selectionBackground': '#2d3a5a',
    'editor.selectionHighlightBackground': '#1e2d48',
    'editorCursor.foreground': '#818cf8',
    'editorLineNumber.foreground': '#374151',
    'editorLineNumber.activeForeground': '#6366f1',
    'editorGutter.background': '#0d1220',
    'editorIndentGuide.background': '#1e2535',
    'editorIndentGuide.activeBackground': '#364165',
    'scrollbar.shadow': '#00000040',
    'scrollbarSlider.background': '#1e2540',
    'scrollbarSlider.hoverBackground': '#293554',
    'scrollbarSlider.activeBackground': '#3d4f7a',
    'editorWidget.background': '#141927',
    'editorSuggestWidget.background': '#141927',
    'editorSuggestWidget.border': '#1a2035',
    'editorSuggestWidget.selectedBackground': '#1a2a50',
    'minimap.background': '#0d1220',
    'editorBracketHighlight.foreground1': '#818cf8',
    'editorBracketHighlight.foreground2': '#06b6d4',
    'editorBracketHighlight.foreground3': '#a78bfa',
  },
}

/**
 * @param {Object} props
 * @param {string} props.value - Editor content
 * @param {function} props.onChange - Called when content changes
 * @param {string} props.language - Monaco language identifier
 * @param {boolean} [props.readOnly] - Read-only mode
 * @param {number} [props.height] - Fixed height in pixels
 */
function Editor({ value, onChange, language, readOnly = false, height }) {
  const editorRef = useRef(null)

  const handleMount = useCallback((editor, monaco) => {
    editorRef.current = editor

    // Define custom dark theme
    monaco.editor.defineTheme('codeai-dark', MONACO_THEME_DATA)
    monaco.editor.setTheme('codeai-dark')

    // Add keyboard shortcut: Ctrl+Shift+F to format
    editor.addAction({
      id: 'format-document',
      label: 'Format Document',
      keybindings: [
        monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.KeyF,
      ],
      run: (ed) => ed.getAction('editor.action.formatDocument')?.run(),
    })
  }, [])

  return (
    <div style={{ height: height || '100%', minHeight: '300px' }}>
      <MonacoEditor
        height="100%"
        language={language}
        value={value}
        onChange={onChange}
        onMount={handleMount}
        options={{
          ...MONACO_OPTIONS,
          readOnly,
        }}
        loading={
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: '#64748b',
            fontSize: '0.875rem',
            fontFamily: 'Inter, sans-serif',
          }}>
            <span>Loading Monaco Editor…</span>
          </div>
        }
      />
    </div>
  )
}

export default Editor
