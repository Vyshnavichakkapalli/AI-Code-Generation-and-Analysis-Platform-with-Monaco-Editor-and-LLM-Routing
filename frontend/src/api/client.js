/**
 * API client for the AI Code Platform backend.
 * Uses axios with centralized error handling.
 */

import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : '/api/v1'

const client = axios.create({
  baseURL: API_BASE,
  timeout: 90000, // 90s for LLM calls
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor: normalize errors
client.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      const message =
        data?.detail?.detail ||
        data?.detail ||
        data?.error ||
        `HTTP ${status} error`
      return Promise.reject(new Error(message))
    } else if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('Request timed out. The LLM provider may be slow.'))
    } else if (!error.response) {
      return Promise.reject(new Error('Network error — is the backend running?'))
    }
    return Promise.reject(error)
  }
)

/**
 * Generate code from a natural language prompt.
 * @param {Object} params
 * @param {string} params.prompt - Natural language instruction
 * @param {string} params.language - Target language
 * @param {string} params.task_type - Task type (boilerplate, unit_test, etc.)
 * @param {string} [params.code_context] - Optional existing code
 * @returns {Promise<{code, explanation, routed_model, request_id}>}
 */
export async function generateCode({ prompt, language, task_type, code_context = '' }) {
  const { data } = await client.post('/generate', {
    prompt,
    language,
    task_type,
    code_context,
  })
  return data
}

/**
 * Analyze code with static tools + LLM review.
 * @param {Object} params
 * @param {string} params.code - Source code to analyze
 * @param {string} params.language - Programming language
 * @param {string} [params.task_type] - Analysis type (bug_hunt, security_audit, etc.)
 * @returns {Promise<{static_analysis, llm_feedback, routed_model, request_id}>}
 */
export async function analyzeCode({ code, language, task_type = 'code_review' }) {
  const { data } = await client.post('/analyze', {
    code,
    language,
    task_type,
  })
  return data
}

/**
 * Fetch request history.
 * @param {number} [limit=50] - Max items to return
 * @param {number} [offset=0] - Offset for pagination
 * @returns {Promise<{items, total}>}
 */
export async function getHistory(limit = 50, offset = 0) {
  const { data } = await client.get('/history', { params: { limit, offset } })
  return data
}

/**
 * Check backend health.
 * @returns {Promise<{status, version}>}
 */
export async function checkHealth() {
  const { data } = await client.get('/health', { baseURL: import.meta.env.VITE_API_URL || '' })
  return data
}
