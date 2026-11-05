# NexaMind — API Overview

## 1. Purpose

This document defines the API communication principles, conventions, and overall structure for the NexaMind application.

NexaMind uses a RESTful API to allow the React frontend to communicate with the Django REST Framework backend.

The API is responsible for authentication, conversation management, message processing, and access to AI-powered functionality.

This document establishes the API foundation. Detailed endpoint definitions and request/response examples will be documented separately.

## 2. API Architecture

NexaMind follows a client-server architecture.

- **Client:** React application.
- **API server:** Django REST Framework.
- **Database:** PostgreSQL.
- **AI provider:** Google Gemini API, accessed exclusively through the backend.

### Communication flow

```text
React Frontend
      |
      | HTTPS / JSON
      v
Django REST Framework
      |
      +------ Authentication
      |
      +------ Authorization
      |
      +------ Business Logic
      |
      +------ Conversation Management
      |
      +------ Gemini Integration
      |
      v
PostgreSQL Database

Django Backend
      |
      | Server-side API request
      v
Google Gemini API
```

The frontend must never communicate directly with Gemini using the application's private API key.

## 3. API Design Principles

NexaMind API development follows these principles:

### 3.1 RESTful resource design

Endpoints should represent application resources.

Examples:

- Users
- Conversations
- Messages

Use HTTP methods according to their intended meaning.

| Method | Purpose                                  |
| ------ | ---------------------------------------- |
| GET    | Retrieve resources                       |
| POST   | Create resources or trigger an operation |
| PATCH  | Partially update resources               |
| PUT    | Replace a resource when appropriate      |
| DELETE | Delete resources                         |

### 3.2 JSON communication

The API uses JSON for request and response bodies.

Example request:

```json
{
  "content": "Explain how REST APIs work."
}
```

Example response:

```json
{
  "id": "message-uuid",
  "role": "assistant",
  "content": "A REST API is an interface..."
}
```

The examples are illustrative. Final response schemas will be defined in the endpoint reference and OpenAPI specification.

### 3.3 API versioning

All application endpoints will initially use the `/api/v1/` prefix.

Example:

```text
/api/v1/conversations/
/api/v1/auth/login/
```

Versioning provides a path for future API changes without unnecessarily breaking existing clients.

### 3.4 Consistent responses

Responses should follow predictable structures.

Successful responses should return the appropriate HTTP status code and resource representation.

Error responses should provide a consistent error structure.

### 3.5 Security by default

Every protected endpoint must:

- Require valid authentication.
- Enforce resource ownership.
- Validate incoming data.
- Avoid exposing internal secrets.
- Return appropriate authorization errors.
- Avoid revealing another user's private information.

Authentication alone does not establish permission to access a resource.

## 4. Base URL and Endpoint Structure

### Development

The development backend is expected to run locally:

```text
http://localhost:8000
```

API base path:

```text
http://localhost:8000/api/v1/
```

### Production

The production API domain will be selected during deployment.

It must be configurable through frontend environment variables rather than hardcoded into application components.

Example frontend configuration:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

The production value must use HTTPS.

Do not place private credentials in Vite environment variables. Variables exposed to browser code are not secret.

## 5. API Resource Organization

The initial API will be organized around the following resources.

### 5.1 Authentication

Base path:

```text
/api/v1/auth/
```

Planned operations:

| Operation     | Method | Endpoint                      |
| ------------- | ------ | ----------------------------- |
| Register      | POST   | `/api/v1/auth/register/`      |
| Login         | POST   | `/api/v1/auth/login/`         |
| Refresh token | POST   | `/api/v1/auth/token/refresh/` |
| Current user  | GET    | `/api/v1/auth/me/`            |

The final authentication implementation will define token storage, expiration, refresh behavior, and logout semantics.

### 5.2 Conversations

Base path:

```text
/api/v1/conversations/
```

Planned operations:

| Operation             | Method | Endpoint                      |
| --------------------- | ------ | ----------------------------- |
| List conversations    | GET    | `/api/v1/conversations/`      |
| Create conversation   | POST   | `/api/v1/conversations/`      |
| Retrieve conversation | GET    | `/api/v1/conversations/{id}/` |
| Update conversation   | PATCH  | `/api/v1/conversations/{id}/` |
| Delete conversation   | DELETE | `/api/v1/conversations/{id}/` |

Conversation resources belong to authenticated users.

The backend must filter and authorize conversation access using the authenticated user.

### 5.3 Messages

Base path:

```text
/api/v1/conversations/{conversation_id}/messages/
```

Planned operations:

| Operation     | Method | Endpoint                                            |
| ------------- | ------ | --------------------------------------------------- |
| List messages | GET    | `/api/v1/conversations/{conversation_id}/messages/` |
| Send message  | POST   | `/api/v1/conversations/{conversation_id}/messages/` |

The message endpoint is responsible for coordinating the AI generation workflow.

The backend will:

1. Authenticate the user.
2. Verify conversation ownership.
3. Validate the submitted message.
4. Retrieve the relevant conversation context.
5. Apply conversation-specific instructions.
6. Request a response from Gemini.
7. Persist the messages according to the defined failure-handling strategy.
8. Return the resulting response.

The exact persistence and error-handling behavior will be specified during implementation.

## 6. Authentication and Authorization

Protected endpoints will use JWT-based authentication.

The frontend will attach the required authentication credential to protected API requests according to the final token-storage design.

Conceptual request:

```http
GET /api/v1/conversations/
Authorization: Bearer <access-token>
```

The backend must validate the token and identify the authenticated user.

For conversation and message operations, ownership must also be checked.

For example, User A must never retrieve, modify, or delete User B's conversations or messages.

The detailed security requirements are defined in:

`docs/02-system-design/security-architecture.md`

## 7. HTTP Status Code Conventions

NexaMind will use standard HTTP status codes.

| Status | Meaning               | Example                                  |
| ------ | --------------------- | ---------------------------------------- |
| 200    | OK                    | Successful retrieval or update           |
| 201    | Created               | Conversation successfully created        |
| 204    | No Content            | Successful deletion                      |
| 400    | Bad Request           | Invalid request data                     |
| 401    | Unauthorized          | Missing or invalid authentication        |
| 403    | Forbidden             | Authenticated user lacks permission      |
| 404    | Not Found             | Requested resource does not exist        |
| 405    | Method Not Allowed    | Unsupported HTTP method                  |
| 409    | Conflict              | Conflicting operation                    |
| 429    | Too Many Requests     | Rate limit exceeded                      |
| 500    | Internal Server Error | Unexpected backend failure               |
| 502    | Bad Gateway           | Upstream AI provider failure             |
| 503    | Service Unavailable   | Required service temporarily unavailable |
| 504    | Gateway Timeout       | Upstream request timed out               |

The actual status code for a particular failure must reflect the implemented behavior. For example, an ownership-protected resource may return 404 rather than 403 to avoid disclosing its existence.

## 8. Error Response Convention

API errors should use a consistent JSON structure.

Illustrative example:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The submitted message is invalid.",
    "details": {
      "content": ["This field is required."]
    }
  }
}
```

Recommended error categories include:

- `VALIDATION_ERROR`
- `AUTHENTICATION_REQUIRED`
- `INVALID_CREDENTIALS`
- `PERMISSION_DENIED`
- `RESOURCE_NOT_FOUND`
- `RATE_LIMIT_EXCEEDED`
- `AI_PROVIDER_ERROR`
- `AI_PROVIDER_TIMEOUT`
- `INTERNAL_SERVER_ERROR`

Error responses must not expose API keys, access tokens, stack traces, database credentials, or sensitive internal implementation details.

## 9. Pagination

List endpoints may return multiple resources.

Pagination should be used for conversation and message history as datasets grow.

The initial implementation will use Django REST Framework pagination.

The final pagination strategy, page size, ordering, and response structure will be specified in the endpoint reference.

Message history should have a stable chronological ordering so the frontend can display the conversation correctly.

## 10. Data Validation

The backend is responsible for validating incoming data.

Examples include:

- Required fields.
- Data types.
- Maximum message length.
- Valid UUID identifiers.
- Allowed conversation update fields.
- Valid authentication credentials.
- Allowed message roles.
- Valid custom instruction length.

Never rely exclusively on frontend validation.

The backend must not accept arbitrary message roles from clients. The client submits user content; the backend determines the assistant role for generated responses.

## 11. AI Provider Boundary

The public NexaMind API should represent NexaMind application resources and operations rather than exposing Gemini-specific implementation details.

For example:

```text
POST /api/v1/conversations/{id}/messages/
```

The frontend sends a message to NexaMind. It does not need to know the Gemini SDK method, provider credentials, or internal provider implementation.

This separation allows the backend to change or extend AI providers without requiring the frontend API contract to change unnecessarily.

## 12. API Documentation

The API will use OpenAPI for machine-readable API documentation.

Planned documentation:

```text
docs/03-api/
├── api-overview.md
├── endpoint-reference.md
└── openapi.yaml
```

OpenAPI documentation should describe:

- Endpoint paths.
- HTTP methods.
- Authentication requirements.
- Request schemas.
- Response schemas.
- Status codes.
- Error structures.
- Example requests and responses.

The API documentation must be updated when endpoint contracts change.

## 13. Testing Requirements

API tests should verify:

1. Correct HTTP methods and status codes.
2. Request validation.
3. Response structure.
4. Authentication requirements.
5. Authorization and conversation ownership.
6. Conversation CRUD operations.
7. Message creation and retrieval.
8. Gemini integration failure handling.
9. Pagination and ordering.
10. Protection against cross-user data access.

Gemini API calls should be mocked in ordinary automated tests so that tests do not depend on external availability, incur unnecessary costs, or require a real API key.

## 14. Current API Design Status

| Area                    | Status                               |
| ----------------------- | ------------------------------------ |
| REST architecture       | Planned                              |
| API versioning          | Defined                              |
| Authentication strategy | JWT selected; implementation pending |
| Conversation endpoints  | Proposed                             |
| Message endpoints       | Proposed                             |
| Error conventions       | Proposed                             |
| Pagination              | Planned                              |
| OpenAPI documentation   | Planned                              |
| API implementation      | Not started                          |
| API tests               | Not started                          |

## 15. Related Documents

- [Functional Requirements](../01-requirements/functional-requirements.md)
- [Non-Functional Requirements](../01-requirements/non-functional-requirements.md)
- [Architecture Overview](../02-system-design/architecture-overview.md)
- [Backend Architecture](../02-system-design/backend-architecture.md)
- [AI Architecture](../02-system-design/ai-architecture.md)
- [Database Design](../02-system-design/database-design.md)
- [Security Architecture](../02-system-design/security-architecture.md)
- [API Endpoint Reference](endpoint-reference.md)

---

**Document status:** Initial API design
**Implementation status:** Not started
**API version:** v1
