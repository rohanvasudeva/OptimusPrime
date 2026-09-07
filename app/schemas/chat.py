from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: UUID
    message: str


class ChatResponse(BaseModel):
    session_id: UUID
    user_message: str
    assistant_message: str