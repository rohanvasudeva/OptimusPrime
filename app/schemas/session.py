from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: str | None = None


class SessionUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=100)


class SessionResponse(BaseModel):
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
