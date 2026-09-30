# Database schema (ER diagram)

PostgreSQL 16 with the `pgvector` extension. Every table is created by Alembic
migrations in `backend/alembic/versions/`.

```mermaid
erDiagram
    users ||--o{ email_otps : "has"
    users ||--o{ password_reset_otps : "has"
    users ||--o{ documents : "uploads"
    users ||--o{ document_chunks : "owns"
    users ||--o{ chat_messages : "asks"
    documents ||--o{ document_chunks : "is split into"
    documents ||--o{ chat_messages : "is discussed in"

    users {
        int id PK
        varchar(100) name
        varchar(255) email UK "lowercased, unique index"
        varchar(255) hashed_password "Argon2 hash, never plain text"
        boolean is_verified "false until email OTP is verified"
        int token_version "increased on logout / password change / reset"
        timestamptz created_at
        timestamptz updated_at
    }

    email_otps {
        int id PK
        int user_id FK "ON DELETE CASCADE"
        varchar(255) otp_hash "HMAC-SHA256, never the plain code"
        timestamptz expires_at
        boolean is_used "single use"
        int attempts "wrong guesses so far"
        timestamptz created_at
    }

    password_reset_otps {
        int id PK
        int user_id FK "ON DELETE CASCADE"
        varchar(255) otp_hash "HMAC-SHA256, never the plain code"
        timestamptz expires_at
        boolean is_used "single use"
        int attempts "wrong guesses so far"
        timestamptz created_at
    }

    documents {
        int id PK
        int user_id FK "ON DELETE CASCADE"
        varchar(255) original_filename "shown in the UI"
        varchar(255) stored_filename UK "random name on disk"
        int file_size "bytes"
        int page_count "nullable until processed"
        int chunk_count
        varchar(20) status "processing | ready | failed (CHECK)"
        text error_message "nullable"
        timestamptz created_at
        timestamptz updated_at
    }

    document_chunks {
        int id PK
        int document_id FK "ON DELETE CASCADE"
        int user_id FK "ON DELETE CASCADE"
        int chunk_index "unique per document"
        int page_number "1-based page of the text"
        text content "about 1000 characters"
        vector(768) embedding "HNSW index, vector_cosine_ops"
        timestamptz created_at
    }

    chat_messages {
        int id PK
        int user_id FK "ON DELETE CASCADE"
        int document_id FK "ON DELETE CASCADE"
        text question
        text answer
        boolean used_tool "true if the MCP tool was used"
        timestamptz created_at
    }
```

## Relationships

| Relationship | Type | On delete |
|---|---|---|
| users → email_otps | one-to-many | deleting a user deletes their codes |
| users → password_reset_otps | one-to-many | deleting a user deletes their codes |
| users → documents | one-to-many | deleting a user deletes their documents |
| documents → document_chunks | one-to-many | deleting a document deletes its chunks |
| documents → chat_messages | one-to-many | deleting a document deletes its chat history |
| users → document_chunks, chat_messages | one-to-many | also stored directly, so every query can filter by owner |

## Indexes

| Table | Index | Purpose |
|---|---|---|
| users | `ix_users_email` (unique) | fast login lookup; one account per email |
| email_otps / password_reset_otps | `user_id` | find a user's newest code |
| documents | `user_id`, unique `stored_filename` | list a user's documents |
| document_chunks | `ix_document_chunks_embedding_hnsw` (HNSW, cosine) | fast nearest-neighbour vector search |
| document_chunks | `document_id`, `user_id`, unique `(document_id, chunk_index)` | filter search to one user's document |
| chat_messages | `(document_id, created_at)`, `user_id` | load a document's history in order |
