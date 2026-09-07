# REST API Documentation

This document outlines the complete REST API specification for the **AI Book Summarizer & Agentic Q&A Engine**.

- **Base URL (Local):** `http://localhost:8000/api/v1`
- **Interactive Swagger Docs:** `http://localhost:8000/docs`
- **ReDoc Documentation:** `http://localhost:8000/redoc`

---

## Table of Contents
1. [Authentication Endpoints](#1-authentication-endpoints)
   - `POST /api/v1/auth/register`
   - `POST /api/v1/auth/login`
   - `GET /api/v1/auth/me`
2. [Book & RAG Endpoints](#2-book--rag-endpoints)
   - `POST /api/v1/books/upload`
   - `GET /api/v1/books/`
   - `GET /api/v1/books/{book_id}`
   - `DELETE /api/v1/books/{book_id}`
   - `POST /api/v1/books/{book_id}/ask`
   - `GET /api/v1/books/{book_id}/history`
3. [System Health Check](#3-system-health-check)
   - `GET /health`
4. [Standard HTTP Status Codes](#4-standard-http-status-codes)

---

## 1. Authentication Endpoints

All protected endpoints require a Bearer token in the request header:
`Authorization: Bearer <jwt_token>`

### 1.1 User Registration
Creates a new user profile with bcrypt-hashed credentials.

- **Endpoint:** `POST /api/v1/auth/register`
- **Access:** Public
- **Request Headers:** `Content-Type: application/json`
- **Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```
- **Responses:**
  - `201 Created`: User successfully registered.
    ```json
    {
      "id": "c71e2ef9-81a9-450a-bfd9-bc4c6a6ee009",
      "email": "user@example.com",
      "created_at": "2026-09-07T12:00:00Z"
    }
    ```
  - `400 Bad Request`: Email is already registered.

---

### 1.2 User Login
Authenticates user credentials and issues a signed JSON Web Token (JWT).

- **Endpoint:** `POST /api/v1/auth/login`
- **Access:** Public
- **Request Headers:** `Content-Type: application/json`
- **Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```
- **Responses:**
  - `200 OK`: Successful authentication.
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
      "token_type": "bearer"
    }
    ```
  - `401 Unauthorized`: Invalid email or password.

---

### 1.3 Current User Info
Fetches profile details of the authenticated token owner.

- **Endpoint:** `GET /api/v1/auth/me`
- **Access:** Protected (Requires JWT)
- **Responses:**
  - `200 OK`:
    ```json
    {
      "id": "c71e2ef9-81a9-450a-bfd9-bc4c6a6ee009",
      "email": "user@example.com",
      "created_at": "2026-09-07T12:00:00Z"
    }
    ```
  - `401 Unauthorized`: Token missing, expired, or invalid.

---

## 2. Book & RAG Endpoints

### 2.1 Upload Book Document
Parses a large PDF or DOCX file (500+ pages), extracts semantic chunks, generates a ~100-word executive summary via Gemini, and indexes vector embeddings (1024-dim) into PostgreSQL `pgvector`.

- **Endpoint:** `POST /api/v1/books/upload`
- **Access:** Protected (Requires JWT)
- **Request Headers:** `Content-Type: multipart/form-data`
- **Form Data:**
  - `file`: Binary file upload (`.pdf` or `.docx`)
- **Responses:**
  - `201 Created`:
    ```json
    {
      "id": "e8d91c78-655b-4392-a1f7-e7d32c0d8df8",
      "title": "science.pdf",
      "filename": "science.pdf",
      "file_type": "pdf",
      "total_pages": 260,
      "summary_100_words": "This textbook covers fundamental scientific disciplines including chemical reactions, acid-base interactions, and biological processes...",
      "created_at": "2026-09-07T12:05:00Z"
    }
    ```
  - `400 Bad Request`: Empty file or unsupported format.
  - `401 Unauthorized`: Invalid or missing session token.
  - `500 Internal Server Error`: Parsing or embedding failure.

---

### 2.2 List User Books
Lists all books previously uploaded by the authenticated user. Enforces strict multi-tenant isolation.

- **Endpoint:** `GET /api/v1/books/`
- **Access:** Protected (Requires JWT)
- **Responses:**
  - `200 OK`:
    ```json
    {
      "books": [
        {
          "id": "e8d91c78-655b-4392-a1f7-e7d32c0d8df8",
          "title": "science.pdf",
          "filename": "science.pdf",
          "file_type": "pdf",
          "total_pages": 260,
          "summary_100_words": "This textbook covers fundamental...",
          "created_at": "2026-09-07T12:05:00Z"
        }
      ],
      "total": 1
    }
    ```

---

### 2.3 Get Book Details
Retrieves details and summary of a specific book by ID.

- **Endpoint:** `GET /api/v1/books/{book_id}`
- **Access:** Protected (Requires JWT)
- **Path Parameters:**
  - `book_id` (UUID): Unique ID of the book.
- **Responses:**
  - `200 OK`: Book details object.
  - `404 Not Found`: Book does not exist or belongs to another user.

---

### 2.4 Delete Book
Removes a book, its vector chunks in `pgvector`, and associated chat histories.

- **Endpoint:** `DELETE /api/v1/books/{book_id}`
- **Access:** Protected (Requires JWT)
- **Path Parameters:**
  - `book_id` (UUID): Unique ID of the book.
- **Responses:**
  - `204 No Content`: Book successfully deleted.
  - `404 Not Found`: Book does not exist or unauthorized.

---

### 2.5 Ask Question (RAG with Citations)
Executes semantic retrieval over `pgvector` chunks using cosine distance (`<=>`), provides the top 5 excerpts with page numbers to the LLM agent, and returns a grounded response with exact page citations and LaTeX math formatting.

- **Endpoint:** `POST /api/v1/books/{book_id}/ask`
- **Access:** Protected (Requires JWT)
- **Path Parameters:**
  - `book_id` (UUID): Unique ID of the book.
- **Request Body:**
```json
{
  "question": "What is a decomposition reaction? Give examples."
}
```
- **Responses:**
  - `200 OK`:
    ```json
    {
      "answer": "A decomposition reaction occurs when a single substance decomposes to form two or more simpler substances [Page 26]...",
      "sources": [
        {
          "page_number": 21,
          "snippet": "2AgCl(s) -> 2Ag(s) + Cl2(g)..."
        },
        {
          "page_number": 26,
          "snippet": "Decomposition reactions are those in which..."
        }
      ]
    }
    ```
  - `404 Not Found`: Book not found or access denied.

---

### 2.6 Get Chat History
Fetches all historical Q&A exchanges for a specific book.

- **Endpoint:** `GET /api/v1/books/{book_id}/history`
- **Access:** Protected (Requires JWT)
- **Path Parameters:**
  - `book_id` (UUID): Unique ID of the book.
- **Responses:**
  - `200 OK`:
    ```json
    [
      {
        "id": "11b51052-a567-4e9e-8736-123456789abc",
        "question": "What is a decomposition reaction?",
        "answer": "A decomposition reaction occurs when...",
        "created_at": "2026-09-07T12:10:00Z"
      }
    ]
    ```

---

## 3. System Health Check

- **Endpoint:** `GET /health`
- **Access:** Public
- **Responses:**
  - `200 OK`:
    ```json
    {
      "status": "healthy",
      "project": "AI Book Summarizer & Agent",
      "llm_model": "gemini-2.5-flash",
      "embedding_model": "embed-english-v3.0"
    }
    ```

---

## 4. Standard HTTP Status Codes

| Code | Meaning | Usage in Application |
| :--- | :--- | :--- |
| **`200 OK`** | Success | Returned for successful queries, listings, and logins. |
| **`201 Created`** | Resource Created | Returned when a new user registers or a book is uploaded and indexed. |
| **`204 No Content`**| Successful Deletion | Returned upon deleting a book. |
| **`400 Bad Request`**| Client Error | Uploading empty files or invalid payload data. |
| **`401 Unauthorized`**| Auth Required | Missing, expired, or tampered JWT token. |
| **`404 Not Found`** | Resource Not Found | Querying or deleting a book that doesn't exist or isn't owned by user. |
| **`500 Internal Error`**| Server Exception | Unhandled runtime exception or 3rd party AI API outage. |
