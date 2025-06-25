from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class InteractionModel(BaseModel):
    timestamp: str
    question: str
    query: str
    result: str
    answer: str

class ConversationMemoryModel(BaseModel):
    username: str
    conversation_history: List[InteractionModel] = []
    question_patterns: Dict[str, Any] = {}
    entity_memory: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

class MemoryCreateModel(BaseModel):
    username: str
    interaction: InteractionModel

class MemoryUpdateModel(BaseModel):
    username: str
    conversation_history: List[InteractionModel]
    question_patterns: Dict[str, Any]
    entity_memory: Dict[str, Any]