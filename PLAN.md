# PLAN: finishing the PDF Chat Platform

Source of truth: `docs/Project.pdf` + `CLAUDE.md`. Each phase ends with tests, fixes, and a commit (no push).

## Decisions made from the official docs (checked 2026-09-30)

| Topic | Decision | Why |
|---|---|---|
| Chat model | `gemini-3.8-flash` (env `GEMINI_CHAT_MODEL`) | Google's models page recommends 3.8 Flash / 3.5 Flash-Lite for new projects; 2.5 models are access-limited. |
| Temperature | `0.2` (env `GEMINI_TEMPERATURE`) | You asked for low temperature. Note: Google recommends 1.0 for Gemini 3 (low values can cause looping in heavy reasoning). Short grounded answers are low risk, and it's configurable if we see problems. |
| Embeddings | `gemini-embedding-001`, `output_dimensionality=768`, `task_type` RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY, normalised manually | Stable; returns one vector per input string (batching works). `gemini-embedding-2` merges multiple inputs into ONE vector and drops task_type. 768 dims stays under pgvector's 2000-dim HNSW limit. |
| SDK | `google-genai`, `client.models.generate_content` with manual function calling (`automatic_function_calling.disable=True`) | Makes the MCP loop explicit so you can explain it. Appending the model's full `content` back preserves Gemini 3 thought signatures. |
| MCP SDK | Pin `mcp` **1.28.x** and use `mcp.server.fastmcp.FastMCP` | You asked for FastMCP. MCP SDK v2 (2026-09-07) renamed FastMCP to `MCPServer` with no alias. v1.28 is the last v1 and is still maintained. Say if you'd prefer v2. |
| Upload processing | Validate synchronously → save file + `Document(status=processing)` → extract/chunk/embed in a background task → `ready` / `failed` + `error_message` | Upload returns fast; the frontend polls while anything is `processing`. |
| Docker frontend port | `http://localhost:8080` (nginx) | 3000 is taken on this machine by another container; 5173 stays free for `npm run dev`. |

## Housekeeping found while reading the code
- `backend/requirements.txt` and `mcp_server/requirements.txt` are UTF-16 encoded → convert to UTF-8.
- `.env.example` has stale/duplicate vars (`JWT_SECRET_KEY` twice, `JWT_EXPIRE_MINUTES`, `GMAIL_*`, `LLM_*`) → clean up, add `GEMINI_API_KEY` etc.
- `README.md` and `git.ignore` are empty **directories** → replace with a real README.md file / remove.
- `.gitignore` lacks `uploads/`, `.venv/`, `node_modules/`, `dist/` → add.
- Axios sets JSON Content-Type globally and a 15 s timeout → uploads and chat need multipart and longer timeouts.
- No automated tests exist → add a pytest suite (separate test DB, email + Gemini + MCP mocked).
- `GEMINI_API_KEY` is not set in `.env` → **you** need to add it before Phase 3 embeddings can be tested for real.

## Phase 1: Day 1 frontend
Signup (→ `/verify-email` with email in router state), Verify Email (6-digit input, resend with 60 s countdown), Login (AuthProvider notice, 403 → verify page). Check: lint + build.

## Phase 2: Day 2 (backend + frontend)
Backend: `get_current_user` (HTTPBearer, tv check), `GET/PATCH /api/users/me`, `POST /api/users/me/change-password` (new token), `POST /api/auth/logout`, `POST /api/auth/forgot-password`, `POST /api/auth/reset-password` (identical responses; sets is_verified, bumps token_version).
Frontend: Profile page, Forgot/Reset pages, backend logout, AuthProvider loads `/users/me`.
Check: pytest (auth + users), lint + build.

## Phase 3: Day 3 (documents)
Models `Document`, `DocumentChunk` (Vector(768), HNSW `vector_cosine_ops`), cascades, migration. Modules: `documents/` (router, service, storage, pdf processing), `embeddings/`. Validation: extension, content type, `%PDF` magic, size limit (`MAX_UPLOAD_MB`). pypdf page-by-page, chunk ~1000/150 with page numbers, batch embeddings. List/get/delete (delete removes file). Dashboard: upload section with progress, list with status, select for chat, delete with confirmation.

## Phase 4: Day 4 (chat + MCP)
`vector_search/` (user_id AND document_id filter, top 5, cosine), `llm/` (system prompt, exact not-found sentence, low temperature), `mcp_client/`, `chat/` (ChatMessage with used_tool, history endpoint). MCP server: FastMCP, streamable HTTP, `get_word_definition(word)` via dictionaryapi.dev, graceful not-found, logs each call. Chat page: messages, input, loading, history on open, "used dictionary tool" badge.

## Phase 5: Docker
Backend (runs `alembic upgrade head` then uvicorn), frontend (multi-stage → nginx with SPA fallback, `VITE_API_URL` build arg), MCP server; compose with db healthcheck, `depends_on` conditions, named volumes `postgres_data` + `uploads`, CORS incl. `http://localhost:8080`. Must work from a fresh clone with `cp .env.example .env` + filled secrets.

## Phase 6: End-to-end testing (Docker stack)
All 10 demo requirements (I'll ask you for OTP codes), 2 answerable + 1 unanswerable question, 1 MCP call, second user gets 404 for first user's document/chat.

## Phase 7: Deliverables
README.md, `docs/ER-diagram.md` (Mermaid), gitignore/secret audit (incl. git history), remove obsolete `backend/scripts/`.

## Finally
`docs/EXPLAINED.md`: plain-language walkthrough + likely demo questions with short answers.
