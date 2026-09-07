from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path

from app.database import Base, engine
from app.models import Session, Message
from app.routes.sessions import router as sessions_router
from app.routes.messages import router as messages_router
from app.routes.chat import router as chat_router

Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Optimus Prime AI",
    version="1.0.0"
)

# Configure max request body size (50MB)
class LimitUploadSize(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int):
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request, call_next):
        if request.method == 'POST':
            if 'content-length' in request.headers:
                content_length = int(request.headers['content-length'])
                if content_length > self.max_upload_size:
                    return JSONResponse(status_code=413, content={'detail': 'Request body too large'})
        return await call_next(request)

app.add_middleware(LimitUploadSize, max_upload_size=52428800)  # 50MB

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(sessions_router)
app.include_router(messages_router)
app.include_router(chat_router)

@app.get("/")
async def root():
    return FileResponse("app/templates/index.html", media_type="text/html")


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }