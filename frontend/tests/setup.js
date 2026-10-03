import '@testing-library/jest-dom'
import React from 'react'

// Mock Monaco Editor to avoid worker/browser API issues in tests
vi.mock('@monaco-editor/react', () => ({
  default: ({ value, onChange, language }) =>
    React.createElement('textarea', {
      'data-testid': 'monaco-editor',
      'data-language': language,
      value: value,
      onChange: (e) => onChange && onChange(e.target.value),
    }),
}))
