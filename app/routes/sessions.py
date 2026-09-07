from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.session import Session as SessionModel
from app.schemas.session import SessionCreate, SessionResponse, SessionUpdate


router = APIRouter(
    prefix="/sessions",
    tags=["Sessions"]
)


@router.post(
    "",
    response_model=SessionResponse
)
def create_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db)
):
    new_session = SessionModel(
        title=session_data.title
    )

    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return new_session


@router.get(
    "",
    response_model=list[SessionResponse]
)
def get_sessions(
    db: Session = Depends(get_db)
):
    return (
        db.query(SessionModel)
        .order_by(SessionModel.created_at.desc())
        .all()
    )


@router.patch(
    "/{session_id}",
    response_model=SessionResponse
)
def update_session(
    session_id: UUID,
    session_data: SessionUpdate,
    db: Session = Depends(get_db)
):
    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_id)
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.title = session_data.title
    db.commit()
    db.refresh(session)
    return session


@router.get(
    "/{session_id}",
    response_model=SessionResponse
)
def get_session(
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

    return session


@router.delete(
    "/{session_id}"
)
def delete_session(
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

    db.delete(session)
    db.commit()

    return {
        "message": "Session deleted successfully"
    }
