from uuid import UUID

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.session import Session as SessionModel
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import process_chat, stream_chat
from app.services.llm_service import LLMServiceError


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    result = process_chat(
        db=db,
        session_id=request.session_id,
        user_message=request.message
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return ChatResponse(
        session_id=result["session_id"],
        user_message=result["user_message"].content,
        assistant_message=result["assistant_message"].content
    )


def _sse(event_type: str, payload: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"


@router.post("/stream")
def stream(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Stream model deltas as Server-Sent Events.

    Event types are `token`, `done`, and `error`. An error is emitted as an SSE
    event so a response already in progress can still finish cleanly.
    """
    session = db.query(SessionModel).filter(SessionModel.id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    def event_stream():
        try:
            for chunk in stream_chat(db, request.session_id, request.message):
                yield _sse("token", {"content": chunk})
            yield _sse("done", {"session_id": str(request.session_id)})
        except LLMServiceError as exc:
            db.rollback()
            yield _sse("error", {"message": str(exc), "status_code": exc.status_code})
        except Exception:
            db.rollback()
            yield _sse("error", {"message": "Unable to complete the chat request. Please try again.", "status_code": 500})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
