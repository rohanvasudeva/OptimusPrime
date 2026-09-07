from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.session import Session as SessionModel
from app.models.message import Message
from app.schemas.message import MessageCreate, MessageResponse


router = APIRouter(
    prefix="/sessions/{session_id}/messages",
    tags=["Messages"]
)


@router.post("", response_model=MessageResponse)
def create_message(
    session_id: UUID,
    message_data: MessageCreate,
    db: Session = Depends(get_db)
):
    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_id)
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    message = Message(
        session_id=session_id,
        role=message_data.role,
        content=message_data.content
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


@router.get("", response_model=list[MessageResponse])
def get_messages(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_id)
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .all()
    )