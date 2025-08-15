from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, JSON, Integer, ForeignKey, Table
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Message(BaseModel):
    id: str
    context_id: str
    content: str
    role: str  # 'user' or 'assistant'
    timestamp: datetime
    metadata: Optional[dict] = Field(default_factory=dict)


class Conversation(BaseModel):
    id: str
    context_id: str
    transcript_id: str
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = Field(default_factory=list)
    metadata: Optional[dict] = Field(default_factory=dict)


class TranscriptionJob(BaseModel):
    id: str
    s3_key: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    transcript_text: Optional[str] = None


class QuestionnaireResponse(BaseModel):
    id: str
    conversation_id: str
    question_id: str
    answer: str
    confidence: float
    created_at: datetime
    metadata: Optional[dict] = Field(default_factory=dict)


# SQLAlchemy models for PostgreSQL
class ConversationDB(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True)
    context_id = Column(String, nullable=False, index=True)
    transcript_id = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    metadata = Column(JSON)
    
    responses = relationship("QuestionnaireResponseDB", back_populates="conversation")


class QuestionnaireResponseDB(Base):
    __tablename__ = "questionnaire_responses"
    
    id = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.id"))
    question_id = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    confidence = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)
    metadata = Column(JSON)
    
    conversation = relationship("ConversationDB", back_populates="responses")