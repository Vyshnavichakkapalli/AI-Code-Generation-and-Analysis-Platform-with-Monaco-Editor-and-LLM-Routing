/**
 * Frontend component tests
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import Results from '../src/components/Results'

describe('Results Component', () => {
  it('renders empty state when no result', () => {
    render(<Results result={null} mode={null} isLoading={false} />)
    expect(screen.getByText(/Results appear here/i)).toBeInTheDocument()
  })

  it('renders loading state', () => {
    render(<Results result={null} mode="generate" isLoading={true} />)
    expect(screen.getByText(/Generating code/i)).toBeInTheDocument()
  })

  it('renders loading state for analysis', () => {
    render(<Results result={null} mode="analyze" isLoading={true} />)
    expect(screen.getByText(/Analyzing code/i)).toBeInTheDocument()
  })

  it('renders static analysis results', () => {
    const result = {
      static_analysis: [
        { line_number: 5, message: 'Missing docstring', type: 'convention', rule: 'C0116', column: 0 }
      ],
      llm_feedback: [
        { issue_type: 'Code Quality', description: 'Variable name is too short', suggested_fix: 'Use descriptive names', severity: 'low' }
      ],
      routed_model: 'openai/gpt-4o-mini',
      request_id: 'test-uuid',
    }
    render(<Results result={result} mode="analyze" isLoading={false} />)

    expect(screen.getByText(/Missing docstring/i)).toBeInTheDocument()
    expect(screen.getByText(/Variable name is too short/i)).toBeInTheDocument()
    expect(screen.getByText(/Static Analysis/i)).toBeInTheDocument()
    expect(screen.getByText(/AI Code Review/i)).toBeInTheDocument()
  })

  it('renders generated code', () => {
    const result = {
      code: "def hello():\n    return 'world'",
      explanation: 'A simple hello function',
      routed_model: 'groq/llama3-8b-8192',
      request_id: 'test-uuid-2',
    }
    render(<Results result={result} mode="generate" isLoading={false} />)
    expect(screen.getByText(/def hello/)).toBeInTheDocument()
    expect(screen.getByText(/Generated Code/i)).toBeInTheDocument()
  })

  it('shows zero static issues message when clean', () => {
    const result = {
      static_analysis: [],
      llm_feedback: [],
      routed_model: 'openai/gpt-4o-mini',
      request_id: 'test-uuid-3',
    }
    render(<Results result={result} mode="analyze" isLoading={false} />)
    expect(screen.getAllByText(/No static analysis issues found/i).length).toBeGreaterThan(0)
  })
})

describe('Results - Analysis Summary', () => {
  it('displays correct issue counts', () => {
    const result = {
      static_analysis: [
        { line_number: 1, message: 'Issue 1', type: 'error', rule: 'E001', column: 0 },
        { line_number: 2, message: 'Issue 2', type: 'warning', rule: 'W001', column: 0 },
      ],
      llm_feedback: [
        { issue_type: 'Bug', description: 'Null check missing', suggested_fix: 'Add null check', severity: 'high' },
      ],
      routed_model: 'openai/gpt-4o-mini',
      request_id: 'test-summary',
    }
    render(<Results result={result} mode="analyze" isLoading={false} />)
    expect(screen.getByText(/2 static issue/i)).toBeInTheDocument()
    expect(screen.getByText(/1 AI insight/i)).toBeInTheDocument()
  })
})
