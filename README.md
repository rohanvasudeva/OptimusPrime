# Optimus Prime AI

A multi-turn AI chat application built with FastAPI, PostgreSQL, and Groq.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Open%20Application-brightgreen?style=flat-square&logo=render&logoColor=white)](http://13.127.116.192:8000/)

## Features

- Create, view, rename, and delete chat sessions
- Persist user and assistant messages in PostgreSQL
- Generate a chat title from the first user message
- Stream assistant text to the browser with Server-Sent Events (SSE)
- Handle provider rate limits, timeouts, unavailable services, and empty
  responses without leaving the client waiting
- Enforce a 50 MB maximum request body size

## Requirements

- Python 3.12+ for local development
- PostgreSQL 16 (or Docker Desktop)
- A Groq API key

## Configuration

Copy `.env.example` to `.env` and set the values for your environment:

```env
DATABASE_URL=postgresql+psycopg2://postgres:your-password@localhost:5432/optimus
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=openai/gpt-oss-20b
```

When running with Docker Compose, use `postgres` as the database host instead
of `localhost`:

```env
DATABASE_URL=postgresql+psycopg2://postgres:your-password@postgres:5432/optimus
```

## Run with Docker

```bash
docker compose up --build
```

Open the application at [http://localhost:8000/](http://localhost:8000/).
Although Uvicorn reports that it is listening on `0.0.0.0:8000`, that is a
bind address; use `localhost:8000` in a browser on the same machine.

## Run locally

Start PostgreSQL, configure `.env` with a local database URL, then run:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open [http://localhost:8000/](http://localhost:8000/). Interactive API docs
are available at [http://localhost:8000/docs](http://localhost:8000/docs).

## API overview

All request and response bodies are JSON unless stated otherwise.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `POST` | `/sessions` | Create a session with an optional `title` |
| `GET` | `/sessions` | List sessions |
| `GET` | `/sessions/{session_id}` | Get one session |
| `PATCH` | `/sessions/{session_id}` | Update a session title |
| `DELETE` | `/sessions/{session_id}` | Delete a session and its messages |
| `GET` | `/sessions/{session_id}/messages` | List session messages |
| `POST` | `/sessions/{session_id}/messages` | Add a message manually |
| `POST` | `/chat` | Send a message and wait for the complete answer |
| `POST` | `/chat/stream` | Send a message and receive an SSE response |

### Chat request

Both chat endpoints accept:

```json
{
  "session_id": "7c847368-94b4-4652-aea6-13c3167e4a09",
  "message": "Explain Server-Sent Events."
}
```

`POST /chat` returns the complete assistant reply. `POST /chat/stream` returns
`text/event-stream` and emits these events:

- `token` — `{ "content": "..." }` for each generated text chunk
- `done` — `{ "session_id": "..." }` after the completed reply is saved
- `error` — `{ "message": "...", "status_code": 429 }` when generation
  cannot complete

## Project structure

```text
app/
  routes/       FastAPI API endpoints
  services/     Chat persistence and Groq integration
  models/       SQLAlchemy database models
  schemas/      Pydantic request and response schemas
  templates/    Browser UI template
static/         Browser JavaScript and styles
tests/          Test package
```
