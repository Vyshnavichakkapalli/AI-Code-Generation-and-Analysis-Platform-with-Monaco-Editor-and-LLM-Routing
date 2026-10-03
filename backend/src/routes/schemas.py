"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ─── Request Schemas ──────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000, description="Natural language instruction for code generation")
    language: str = Field(..., description="Target programming language (e.g., 'python', 'javascript')")
    task_type: str = Field(default="boilerplate", description="Type of generation task (e.g., 'boilerplate', 'unit_test', 'docstring')")
    code_context: Optional[str] = Field(default="", description="Optional existing code to use as context")


class AnalyzeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50000, description="Source code to analyze")
    language: str = Field(..., description="Programming language of the code")
    task_type: Optional[str] = Field(default="code_review", description="Type of analysis (e.g., 'bug_hunt', 'security_audit', 'code_review')")


# ─── Response Schemas ─────────────────────────────────────────────────────────

class GenerateResponse(BaseModel):
    code: str = Field(..., description="Raw generated code (markdown formatting stripped)")
    explanation: Optional[str] = Field(default="", description="Optional explanation from the AI")
    routed_model: str = Field(..., description="Model identifier that handled this request")
    request_id: str = Field(..., description="UUID of this request in the history table")


class StaticAnalysisIssue(BaseModel):
    line_number: int
    message: str
    column: Optional[int] = None
    type: Optional[str] = None
    rule: Optional[str] = None


class LLMFeedbackIssue(BaseModel):
    issue_type: str
    description: str
    suggested_fix: str
    severity: Optional[str] = "medium"


class AnalyzeResponse(BaseModel):
    static_analysis: List[StaticAnalysisIssue] = Field(default_factory=list)
    llm_feedback: List[LLMFeedbackIssue] = Field(default_factory=list)
    routed_model: str
    request_id: str


class HistoryItem(BaseModel):
    id: str
    endpoint_used: str
    language: str
    task_type: Optional[str]
    user_input: str
    model_routed_to: str
    response_payload: Any
    created_at: datetime


class HistoryResponse(BaseModel):
    items: List[HistoryItem]
    total: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
