# NexaMind — API Endpoint Reference

## 1. Document Purpose

This document defines the planned REST API endpoints for NexaMind.

It describes:

- Endpoint paths and HTTP methods.
- Authentication requirements.
- Request parameters and payloads.
- Expected response structures.
- HTTP status codes.
- Validation and authorization rules.

The endpoint definitions represent the initial API contract. They must be reviewed and updated as implementation decisions become concrete.

## 2. API Conventions

### 2.1 Base path

```text
/api/v1/
```

Development base URL:

```text
http://localhost:8000/api/v1/
```

### 2.2 Content type

Requests and responses use:

```http
Content-Type: application/json
Accept: application/json
```

### 2.3 Authentication

Protected endpoints require a valid JWT access token.

```http
Authorization: Bearer <access-token>
```

Public endpoints are explicitly identified below.

### 2.4 Identifier format

Conversation and message identifiers use UUIDs.

Example:

```text
550e8400-e29b-41d4-a716-446655440000
```

### 2.5 Timestamp format

Timestamps use ISO 8601 with timezone information, preferably UTC.

Example:

```text
2026-11-04T15:30:00Z
```

### 2.6 General error structure

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The submitted data is invalid.",
    "details": {}
  }
}
```

The precise serializer error format will be standardized during implementation.

---

## 3. Authentication Endpoints

### 3.1 Register User

**Endpoint:** `POST /api/v1/auth/register/`

**Authentication:** Public

**Purpose:** Create a new NexaMind user account.

Request:

```json
{
  "username": "example_user",
  "email": "user@example.com",
  "password": "StrongPassword123!",
  "password_confirm": "StrongPassword123!"
}
```

Field requirements:

| Field            | Type   | Required | Description                                |
| ---------------- | ------ | -------- | ------------------------------------------ |
| username         | string | Yes      | Unique username                            |
| email            | string | Yes      | Valid email address                        |
| password         | string | Yes      | Password meeting configured security rules |
| password_confirm | string | Yes      | Must match password                        |

Expected response:

**201 Created**

```json
{
  "user": {
    "id": "user-uuid",
    "username": "example_user",
    "email": "user@example.com"
  },
  "message": "Account created successfully."
}
```

Possible errors:

- `400` — Invalid registration data.
- `409` — Account identifier conflict, if this status is adopted for duplicate accounts.

Security requirements:

- Passwords must be hashed using Django's password hashing framework.
- Passwords must never appear in API responses or logs.
- Registration validation must run on the backend.

### 3.2 Login

**Endpoint:** `POST /api/v1/auth/login/`

**Authentication:** Public

**Purpose:** Authenticate a user and issue JWT credentials.

Request:

```json
{
  "username": "example_user",
  "password": "StrongPassword123!"
}
```

Expected response:

**200 OK**

```json
{
  "access": "<access-token>",
  "refresh": "<refresh-token>"
}
```

The exact response may include user information if required by the selected authentication library.

Possible errors:

- `400` — Invalid request data.
- `401` — Invalid credentials.

Security requirements:

- Do not reveal whether the username or password was incorrect.
- Apply suitable login throttling.
- Do not log credentials or tokens.
- Final token storage and transport strategy must be documented before frontend authentication is implemented.

### 3.3 Refresh Access Token

**Endpoint:** `POST /api/v1/auth/token/refresh/`

**Authentication:** Refresh token

**Purpose:** Obtain a new access token using a valid refresh token.

Request:

```json
{
  "refresh": "<refresh-token>"
}
```

Expected response:

**200 OK**

```json
{
  "access": "<new-access-token>"
}
```

Possible errors:

- `400` — Missing or malformed refresh token.
- `401` — Invalid, expired, or revoked refresh token.

### 3.4 Current User

**Endpoint:** `GET /api/v1/auth/me/`

**Authentication:** Required

**Purpose:** Retrieve the currently authenticated user's profile.

Expected response:

**200 OK**

```json
{
  "id": "user-uuid",
  "username": "example_user",
  "email": "user@example.com"
}
```

Possible errors:

- `401` — Missing or invalid access token.

---

## 4. Conversation Endpoints

All conversation endpoints require authentication.

### 4.1 List Conversations

**Endpoint:** `GET /api/v1/conversations/`

**Purpose:** Retrieve conversations belonging to the authenticated user.

Query parameters:

| Parameter | Type    | Required | Description                |
| --------- | ------- | -------- | -------------------------- |
| page      | integer | No       | Requested page             |
| page_size | integer | No       | Number of records per page |

Expected response:

**200 OK**

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "conversation-uuid-1",
      "title": "Learning Django REST Framework",
      "created_at": "2026-11-04T10:00:00Z",
      "updated_at": "2026-11-04T10:30:00Z"
    },
    {
      "id": "conversation-uuid-2",
      "title": "Understanding Machine Learning",
      "created_at": "2026-11-04T11:00:00Z",
      "updated_at": "2026-11-04T11:15:00Z"
    }
  ]
}
```

Ordering:

- Most recently updated conversations first.

Authorization:

- Return only conversations owned by the authenticated user.

Possible errors:

- `401` — Authentication required.

### 4.2 Create Conversation

**Endpoint:** `POST /api/v1/conversations/`

**Purpose:** Create a new conversation.

Request:

```json
{
  "title": "New conversation",
  "custom_instructions": ""
}
```

Field requirements:

| Field               | Type   | Required | Description                        |
| ------------------- | ------ | -------- | ---------------------------------- |
| title               | string | No       | Conversation title                 |
| custom_instructions | string | No       | Conversation-specific instructions |

The backend determines the conversation owner from the authenticated user. The client must not submit an owner ID.

Expected response:

**201 Created**

```json
{
  "id": "conversation-uuid",
  "title": "New conversation",
  "custom_instructions": "",
  "created_at": "2026-11-04T12:00:00Z",
  "updated_at": "2026-11-04T12:00:00Z"
}
```

Possible errors:

- `400` — Invalid request data.
- `401` — Authentication required.

### 4.3 Retrieve Conversation

**Endpoint:** `GET /api/v1/conversations/{conversation_id}/`

**Purpose:** Retrieve a conversation's details.

Expected response:

**200 OK**

```json
{
  "id": "conversation-uuid",
  "title": "Learning Django REST Framework",
  "custom_instructions": "Explain concepts with practical examples.",
  "created_at": "2026-11-04T10:00:00Z",
  "updated_at": "2026-11-04T10:30:00Z"
}
```

Possible errors:

- `401` — Authentication required.
- `404` — Conversation does not exist or is not accessible to the authenticated user.

### 4.4 Update Conversation

**Endpoint:** `PATCH /api/v1/conversations/{conversation_id}/`

**Purpose:** Update conversation metadata or custom instructions.

Request:

```json
{
  "title": "Advanced Django REST Framework",
  "custom_instructions": "Use concise explanations and practical examples."
}
```

Only supported fields should be accepted.

Expected response:

**200 OK**

```json
{
  "id": "conversation-uuid",
  "title": "Advanced Django REST Framework",
  "custom_instructions": "Use concise explanations and practical examples.",
  "created_at": "2026-11-04T10:00:00Z",
  "updated_at": "2026-11-04T12:15:00Z"
}
```

Possible errors:

- `400` — Invalid update data.
- `401` — Authentication required.
- `404` — Conversation does not exist or is not accessible.

### 4.5 Delete Conversation

**Endpoint:** `DELETE /api/v1/conversations/{conversation_id}/`

**Purpose:** Delete a conversation.

Expected response:

**204 No Content**

No response body.

Possible errors:

- `401` — Authentication required.
- `404` — Conversation does not exist or is not accessible.

Database behavior:

- The initial design uses cascading deletion for related messages.
- Account deletion and long-term retention policies remain separate decisions.

---

## 5. Message Endpoints

All message endpoints require authentication and conversation ownership verification.

### 5.1 List Messages

**Endpoint:** `GET /api/v1/conversations/{conversation_id}/messages/`

**Purpose:** Retrieve messages belonging to a conversation.

Query parameters:

| Parameter | Type    | Required | Description                 |
| --------- | ------- | -------- | --------------------------- |
| page      | integer | No       | Requested page              |
| page_size | integer | No       | Number of messages per page |

Expected response:

**200 OK**

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "message-uuid-1",
      "role": "user",
      "content": "Explain REST APIs.",
      "created_at": "2026-11-04T10:00:00Z"
    },
    {
      "id": "message-uuid-2",
      "role": "assistant",
      "content": "A REST API is an interface...",
      "created_at": "2026-11-04T10:00:05Z"
    }
  ]
}
```

Ordering:

- Messages must be returned in chronological order.
- Pagination must preserve stable ordering.

Possible errors:

- `401` — Authentication required.
- `404` — Conversation does not exist or is not accessible.

### 5.2 Send Message and Generate AI Response

**Endpoint:** `POST /api/v1/conversations/{conversation_id}/messages/`

**Purpose:** Submit a user message and generate an assistant response using Gemini.

Request:

```json
{
  "content": "Explain how Django REST Framework serializers work."
}
```

The client submits only user content. The backend determines the message role, provider, model, and generation metadata.

Expected successful response:

**201 Created**

```json
{
  "user_message": {
    "id": "user-message-uuid",
    "role": "user",
    "content": "Explain how Django REST Framework serializers work.",
    "created_at": "2026-11-04T12:00:00Z"
  },
  "assistant_message": {
    "id": "assistant-message-uuid",
    "role": "assistant",
    "content": "Django REST Framework serializers...",
    "model": "configured-model-identifier",
    "usage": {
      "input_tokens": null,
      "output_tokens": null,
      "total_tokens": null
    },
    "created_at": "2026-11-04T12:00:05Z"
  }
}
```

The model identifier and usage metadata must come from the actual provider response or server configuration. They must not be fabricated.

Possible errors:

- `400` — Invalid or empty message.
- `401` — Authentication required.
- `404` — Conversation does not exist or is not accessible.
- `429` — Application or provider rate limit reached.
- `502` — Upstream AI provider failure.
- `504` — Upstream generation timeout.
- `500` — Unexpected internal failure.

Important processing requirements:

1. Authenticate the user.
2. Retrieve the conversation using an ownership-scoped query.
3. Validate message content.
4. Retrieve the appropriate conversation context.
5. Apply conversation-specific custom instructions.
6. Construct the Gemini request.
7. Call the configured Gemini model.
8. Validate and process the provider response.
9. Persist the user and assistant messages according to the documented failure policy.
10. Return the response to the client.

Failure handling must not create a successful assistant message containing fabricated content.

The exact persistence behavior when Gemini fails or the database write fails must be defined during backend implementation.

---

## 6. Request and Response Validation Rules

### 6.1 Message validation

The backend should validate:

- `content` is present.
- `content` is a string.
- Content is not empty or whitespace-only.
- Content does not exceed the configured maximum length.

The maximum message length is an implementation decision that must be documented and tested.

### 6.2 Conversation validation

The backend should validate:

- Title length.
- Custom instruction length.
- Supported update fields.
- UUID format.
- Conversation ownership.

### 6.3 Message role validation

Allowed stored roles:

- `user`
- `assistant`

The backend controls message role assignment.

Clients cannot submit assistant messages as if they were generated by Gemini.

---

## 7. Authorization Rules

The following rules apply across all protected resources.

| Resource              | Rule                                  |
| --------------------- | ------------------------------------- |
| User profile          | User can access their own profile     |
| Conversation list     | User sees only their conversations    |
| Conversation detail   | Owner only                            |
| Conversation update   | Owner only                            |
| Conversation deletion | Owner only                            |
| Message history       | Owner of the parent conversation only |
| Message creation      | Owner of the parent conversation only |

All ownership checks must be enforced by the backend.

Frontend route protection is not a security boundary.

---

## 8. API Implementation Notes

The endpoint definitions are intended to guide implementation using Django REST Framework.

Potential implementation responsibilities:

| API concern         | Backend responsibility                     |
| ------------------- | ------------------------------------------ |
| Request parsing     | DRF request handling                       |
| Validation          | Serializers                                |
| Authentication      | JWT authentication                         |
| Authorization       | Permissions and ownership-scoped querysets |
| Business logic      | Application services                       |
| Database operations | Django ORM                                 |
| AI generation       | Gemini integration service                 |
| Response formatting | Serializers and API views                  |
| Error handling      | Consistent API exception handling          |

Avoid putting the complete Gemini generation workflow inside a large API view. Keep provider communication and business operations in focused service modules.

---

## 9. Open API Design Decisions

The following decisions require validation before implementation:

| Decision                      | Current direction            | Finalization point            |
| ----------------------------- | ---------------------------- | ----------------------------- |
| JWT implementation            | JWT-based authentication     | Backend setup                 |
| Token storage                 | Not finalized                | Authentication implementation |
| Pagination                    | DRF pagination               | API implementation            |
| Maximum message length        | Not finalized                | Message validation            |
| Custom instruction limit      | Not finalized                | Conversation validation       |
| Message failure persistence   | Not finalized                | Message lifecycle design      |
| Streaming responses           | Not in initial MVP           | Future enhancement            |
| Message editing/regeneration  | Not in initial MVP           | Future enhancement            |
| Conversation title generation | Initial manual/default title | Conversation implementation   |

## 10. Scope Boundaries

The initial API does not include:

- File uploads.
- Image generation.
- Voice conversations.
- Real-time streaming.
- RAG document retrieval.
- Autonomous AI agents.
- Multi-provider selection by end users.
- Payment and subscription management.

These features may be considered in later development stages.

## 11. Related Documents

- [API Overview](./api-overview.md)
- [OpenAPI Specification](./openapi.yaml)
- [Backend Architecture](../02-system-design/backend-architecture.md)
- [AI Architecture](../02-system-design/ai-architecture.md)
- [Database Design](../02-system-design/database-design.md)
- [Security Architecture](../02-system-design/security-architecture.md)
- [Acceptance Criteria](../01-requirements/acceptance-criteria.md)

---

**Document status:** Initial endpoint contract
**API version:** v1
**Implementation status:** Not started
