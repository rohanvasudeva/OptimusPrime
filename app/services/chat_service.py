from uuid import UUID

from sqlalchemy.orm import Session

from app.models.session import Session as SessionModel
from app.models.message import Message
from app.services.llm_service import LLMService, LLMServiceError


def process_chat(
    db: Session,
    session_id: UUID,
    user_message: str
):
    # Check session
    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_id)
        .first()
    )

    if not session:
        return None

    # Save user message
    user_msg = Message(
        session_id=session_id,
        role="user",
        content=user_message
    )

    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Get conversation history (limit to last 20 messages to avoid entity too large)
    history = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .limit(20)
        .all()
    )

    # Convert history to Groq format
    messages = [
        {
            "role": message.role,
            "content": message.content
        }
        for message in history
    ]

    # Generate response
    llm_service = LLMService()

    assistant_text = llm_service.generate_response(messages)

    # Save assistant response
    assistant_msg = Message(
        session_id=session_id,
        role="assistant",
        content=assistant_text
    )

    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return {
        "session_id": session_id,
        "user_message": user_msg,
        "assistant_message": assistant_msg,
        "history": history
    }


def stream_chat(
    db: Session,
    session_id: UUID,
    user_message: str
):
    """Save the user message, then yield assistant text as it is generated."""
    user_msg = Message(session_id=session_id, role="user", content=user_message)
    db.add(user_msg)
    db.commit()

    history = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .limit(20)
        .all()
    )
    messages = [{"role": message.role, "content": message.content} for message in history]

    chunks = []
    for chunk in LLMService().stream_response(messages):
        chunks.append(chunk)
        yield chunk

    assistant_text = "".join(chunks).strip()
    if not assistant_text:
        raise LLMServiceError("The AI returned an empty response. Please try again.", 502)

    assistant_msg = Message(session_id=session_id, role="assistant", content=assistant_text)
    db.add(assistant_msg)
    db.commit()
