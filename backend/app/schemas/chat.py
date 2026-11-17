from typing import Optional
from pydantic import BaseModel, Field


class CitationItem(BaseModel):
    doc_id: str
    filename: str
    page_number: Optional[int] = None
    snippet: str


class WebCitation(BaseModel):
    title: str
    url: str
    snippet: str = ""


class ChatMessageOut(BaseModel):
    id: str
    session_id: str
    role: str = Field(description="'user' or 'assistant'")
    content: str
    citations: list[CitationItem] = Field(default_factory=list)
    web_citations: list[WebCitation] = Field(default_factory=list)
    agent_trace: Optional[dict] = None
    created_at: str


class ChatSessionSummary(BaseModel):
    id: str
    title: str
    doc_ids: list[str] = Field(default_factory=list)
    message_count: int = 0
    updated_at: str
    created_at: str


class ChatSessionDetail(BaseModel):
    id: str
    title: str
    doc_ids: list[str] = Field(default_factory=list)
    messages: list[ChatMessageOut] = Field(default_factory=list)
    updated_at: str
    created_at: str


class CreateChatRequest(BaseModel):
    title: Optional[str] = "New Research Chat"
    doc_ids: list[str] = Field(default_factory=list)


class UpdateChatDocsRequest(BaseModel):
    doc_ids: list[str] = Field(default_factory=list)


class SendMessageRequest(BaseModel):
    content: str
    doc_ids: Optional[list[str]] = None
    allow_web_search: bool = True


class SendMessageResponse(BaseModel):
    session: ChatSessionSummary
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut
