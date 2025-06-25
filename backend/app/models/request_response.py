from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class QuestionRequest(BaseModel):
    username: str
    question: str

class QueryResponse(BaseModel):
    question: str
    resolved_question: str
    query: str
    result: Optional[str] = ""
    answer: str
    success: bool
    error: Optional[str] = None


class QueryApprovalRequest(BaseModel):
    state_hex: str  # hex string of pickled state
    feedback: Optional[str] = ""


class ApprovalResponse(QueryResponse):
    state_hex: Optional[str] = None  # returned in step 1
    message: Optional[str] = None


class MemoryCommandRequest(BaseModel):
    username: str
    command: str

class MemoryResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    database_connected: bool
    supabase_connected: bool