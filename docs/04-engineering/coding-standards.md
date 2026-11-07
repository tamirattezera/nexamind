# NexaMind — Coding Standards

## 1. Purpose

This document defines coding conventions and engineering practices for the NexaMind codebase.

It applies to:

- Python and Django.
- Django REST Framework.
- JavaScript and React.
- API development.
- Database interactions.
- Testing.
- Git commits and code reviews.

The goal is to produce code that is readable, maintainable, testable, secure, and consistent.

## 2. General Engineering Principles

All NexaMind code should follow these principles:

### 2.1 Readability over cleverness

Write code that another developer can understand without excessive explanation.

Prefer:

- Clear variable names.
- Small, focused functions.
- Explicit control flow.
- Consistent formatting.
- Simple solutions.

Avoid unnecessarily complex abstractions.

### 2.2 Separation of concerns

Each module should have a clear responsibility.

For example:

- React components handle presentation and user interaction.
- API services handle HTTP communication.
- Django views handle HTTP requests and responses.
- Serializers validate and transform API data.
- Service functions coordinate business operations.
- Models represent persistent application data.
- AI services manage communication with Gemini.

### 2.3 Avoid premature abstraction

Do not introduce additional layers, factories, or generic frameworks without a demonstrated need.

Start with understandable implementations. Refactor when complexity or repeated behavior justifies it.

### 2.4 Explicit over implicit

Prefer code whose behavior is easy to trace.

Avoid hidden side effects and unnecessary global state.

### 2.5 Security by default

Never trust client-submitted ownership, roles, permissions, or provider credentials.

Validate data and enforce authorization on the backend.

---

## 3. Python Coding Standards

### 3.1 Style guide

Follow PEP 8 as the baseline Python style guide.

Recommended conventions:

| Element   | Convention       | Example                   |
| --------- | ---------------- | ------------------------- |
| Variables | snake_case       | `conversation_id`         |
| Functions | snake_case       | `create_conversation()`   |
| Classes   | PascalCase       | `ConversationService`     |
| Constants | UPPER_SNAKE_CASE | `MAX_MESSAGE_LENGTH`      |
| Modules   | lowercase        | `conversation_service.py` |

Use meaningful names rather than abbreviations that obscure intent.

### 3.2 Formatting

Use consistent indentation:

- Four spaces per indentation level.
- No tabs.
- Reasonable line lengths.
- Blank lines between logical sections.

A formatter and linter may be configured when backend implementation begins.

### 3.3 Functions

Functions should have focused responsibilities.

Prefer:

```python
def get_user_conversations(user):
    return Conversation.objects.filter(user=user)
```

Avoid functions that combine unrelated responsibilities such as authentication, database queries, AI generation, and response formatting.

### 3.4 Type hints

Use type hints where they improve clarity.

Example:

```python
def normalize_message(content: str) -> str:
    return content.strip()
```

Do not add annotations that are inaccurate or create unnecessary complexity.

### 3.5 Exceptions

Handle expected failures explicitly.

Example:

```python
try:
    response = generate_ai_response(prompt)
except ProviderTimeoutError:
    # Translate the provider failure into an appropriate application error.
    raise
```

Do not silently swallow exceptions.

Avoid exposing internal stack traces or sensitive details to API clients.

### 3.6 Django conventions

Follow Django conventions for:

- Models.
- Migrations.
- URL configuration.
- Settings.
- Authentication.
- Admin configuration.

Use descriptive model and field names.

Keep database constraints and indexes intentional.

Configure the custom user model before the first project migrations.

### 3.7 Django REST Framework conventions

Use serializers for input validation and output representation.

Use permissions and ownership-scoped querysets to protect resources.

Avoid placing the complete business workflow inside large API views.

Example responsibility separation:

```text
Request
  |
  v
API View
  |
  v
Serializer
  |
  v
Business Service
  |
  v
Database / Gemini Service
  |
  v
Response
```

This is a conceptual responsibility flow, not a requirement to create a separate class for every step.

---

## 4. JavaScript Coding Standards

### 4.1 Language

Use modern JavaScript (ES6+) for the React frontend.

The initial NexaMind frontend uses JavaScript and JSX, not TypeScript.

### 4.2 Naming conventions

| Element              | Convention                        | Example           |
| -------------------- | --------------------------------- | ----------------- |
| Variables            | camelCase                         | `conversationId`  |
| Functions            | camelCase                         | `sendMessage()`   |
| Components           | PascalCase                        | `ChatMessage`     |
| Constants            | UPPER_SNAKE_CASE when appropriate | `API_BASE_URL`    |
| Files for components | PascalCase                        | `ChatMessage.jsx` |
| Utility files        | camelCase                         | `formatDate.js`   |

### 4.3 Variables

Prefer `const` by default.

Use `let` when reassignment is necessary.

Avoid `var` in new application code.

### 4.4 Functions

Prefer small functions with one clear responsibility.

Use descriptive names that communicate intent.

Avoid deeply nested callbacks and unnecessarily complicated conditional expressions.

### 4.5 Asynchronous operations

Use `async` and `await` for asynchronous API operations when appropriate.

Handle loading, success, and failure states explicitly.

Do not leave rejected promises unhandled.

### 4.6 Error handling

Frontend error handling should distinguish between:

- Validation errors.
- Authentication errors.
- Authorization errors.
- Network failures.
- Server failures.
- AI generation failures.

Never display raw internal backend stack traces to users.

---

## 5. React Coding Standards

### 5.1 Component design

Build small, focused, reusable components.

Examples:

```text
ChatHeader
ConversationSidebar
ConversationItem
MessageList
MessageBubble
ChatInput
LoadingIndicator
ErrorMessage
```

Each component should have a clear purpose.

Do not split every HTML element into its own component without a practical reason.

### 5.2 Component conventions

Use functional components and React Hooks.

Example:

```jsx
function MessageBubble({ message }) {
  return (
    <div className={`message message--${message.role}`}>{message.content}</div>
  );
}

export default MessageBubble;
```

### 5.3 Props

Use descriptive prop names.

Pass only the information and callbacks a component needs.

Avoid unnecessarily large prop objects that couple unrelated components.

### 5.4 State management

Follow a local-first state strategy.

Use component state for local interactions.

Lift state when multiple components genuinely need the same information.

Introduce shared state management only when application complexity justifies it.

Do not introduce a state-management library simply because one is available.

### 5.5 Effects

Use `useEffect` for synchronizing components with external systems.

Avoid using effects for calculations that can be derived during rendering.

Keep effect dependencies accurate.

### 5.6 API communication

Keep HTTP communication outside presentation components where practical.

Use a shared Axios client for common configuration and feature-specific API modules for application operations.

Example structure:

```text
src/
├── services/
│   └── api/
│       ├── apiClient.js
│       └── authApi.js
└── features/
    └── chat/
        └── services/
            └── messageApi.js
```

This is an example of the intended organization; create files as implementation requires them.

### 5.7 User interface states

Every important asynchronous interaction should consider:

- Initial state.
- Loading state.
- Success state.
- Empty state.
- Error state.

The chat interface should also prevent accidental duplicate submissions and provide appropriate feedback while generation is in progress.

### 5.8 Accessibility

Use semantic HTML.

Provide:

- Accessible labels for inputs.
- Keyboard-accessible controls.
- Visible focus indicators.
- Appropriate button types.
- Meaningful alternative text for informative images.
- Sufficient color contrast.

Do not rely exclusively on color to communicate status.

---

## 6. API Coding Standards

### 6.1 Naming

Use consistent, resource-oriented endpoint names.

Examples:

```text
GET    /api/v1/conversations/
POST   /api/v1/conversations/
GET    /api/v1/conversations/{id}/
PATCH  /api/v1/conversations/{id}/
DELETE /api/v1/conversations/{id}/
```

### 6.2 Request validation

Validate all client input on the backend.

Never assume frontend validation guarantees valid data.

### 6.3 Response consistency

Use consistent response structures and meaningful HTTP status codes.

Do not return successful responses for failed AI generation operations.

### 6.4 Authentication and authorization

All protected operations must authenticate the user and verify resource ownership where applicable.

Never trust a client-provided user ID as proof of ownership.

### 6.5 API documentation

Update the endpoint reference and OpenAPI specification whenever an API contract changes.

---

## 7. Database Coding Standards

### 7.1 Model design

Use clear relationships and intentional constraints.

Prefer relational integrity enforced by PostgreSQL and Django rather than relying exclusively on application code.

### 7.2 Query efficiency

Avoid unnecessary database queries.

Watch for N+1 query problems.

Use appropriate Django ORM tools such as:

- `select_related()`
- `prefetch_related()`
- `only()`
- `values()`

Apply these when justified by query behavior and profiling.

### 7.3 Migrations

Create and review migrations whenever model structure changes.

Do not manually modify an already-applied migration to rewrite database history.

Test migrations against the intended database environment.

### 7.4 Data integrity

Preserve conversation ownership and message relationships.

Do not allow a message to be attached to a conversation owned by another user.

---

## 8. AI Integration Standards

### 8.1 Provider isolation

Keep Gemini communication inside backend AI integration modules.

Do not place provider-specific API calls inside React components or ordinary conversation views.

### 8.2 Context construction

Construct model context on the backend using authorized conversation data.

Do not trust the frontend to supply complete or authorized conversation history.

### 8.3 Custom instructions

Treat user-defined instructions as untrusted input.

They must never override application security rules or authorization checks.

### 8.4 Provider failures

Handle:

- Authentication failures.
- Rate limits.
- Provider errors.
- Timeouts.
- Invalid responses.
- Missing usage metadata.

Do not fabricate assistant messages or token usage.

### 8.5 Secret management

Keep Gemini API credentials in backend environment configuration or an appropriate secret manager.

Never commit real credentials.

---

## 9. Testing Standards

### 9.1 Backend tests

Test:

- Model behavior.
- Serializer validation.
- API views.
- Authentication.
- Authorization.
- Ownership isolation.
- Business services.
- Gemini failure handling.

### 9.2 Frontend tests

Test:

- Component rendering.
- User interactions.
- Form validation.
- Loading states.
- Error states.
- API integration behavior.

### 9.3 Integration tests

Test interactions between application layers.

Examples:

- React API client and backend endpoint contracts.
- Conversation creation and persistence.
- Message submission and response handling.
- Cross-user access protection.

### 9.4 AI mocking

Ordinary automated tests should mock Gemini calls.

Tests must not depend on an external AI provider being available or consume API quota unnecessarily.

### 9.5 Test naming

Use descriptive names that communicate expected behavior.

Example:

```python
def test_user_cannot_access_another_users_conversation():
    ...
```

Tests should verify behavior, not merely that code executes.

---

## 10. Security Standards

All contributors must follow these requirements:

1. Never commit API keys, passwords, or private tokens.
2. Never expose Gemini credentials to the frontend.
3. Never trust client-submitted ownership information.
4. Validate all incoming data.
5. Enforce authorization on every protected resource.
6. Avoid logging passwords, access tokens, or sensitive conversation data.
7. Use parameterized ORM operations rather than unsafe SQL construction.
8. Render user-generated content safely.
9. Keep dependencies updated.
10. Use HTTPS in production.

Refer to `docs/02-system-design/security-architecture.md` for the detailed security design.

---

## 11. Code Organization

NexaMind uses feature-based organization on the frontend and responsibility-based organization on the backend.

### Frontend

```text
frontend/src/
├── app/
├── components/
├── features/
│   ├── auth/
│   ├── chat/
│   ├── conversations/
│   └── settings/
├── services/
├── hooks/
├── utils/
└── styles/
```

### Backend

```text
backend/apps/
├── core/
├── accounts/
├── conversations/
├── messages/
└── ai/
    ├── providers/
    ├── services/
    └── tests/
```

The exact organization may evolve when implementation reveals actual responsibilities.

---

## 12. Git Commit Standards

Use clear commit messages that describe the change.

Recommended format:

```text
type: short description
```

Examples:

```text
docs: define backend coding standards
feat: add user registration endpoint
feat: implement conversation creation
fix: prevent cross-user conversation access
test: add message generation failure tests
refactor: extract Gemini integration service
```

Avoid vague messages such as:

```text
update
changes
fix stuff
final code
```

Each commit should represent a meaningful and reviewable change.

---

## 13. Code Review Checklist

Before considering a change complete, verify:

### General

- [ ] Code has a clear responsibility.
- [ ] Names communicate intent.
- [ ] No unnecessary abstraction was introduced.
- [ ] Existing architecture conventions are followed.

### Backend

- [ ] Input validation is implemented.
- [ ] Authentication and authorization are correct.
- [ ] Database operations preserve integrity.
- [ ] Errors are handled appropriately.
- [ ] Sensitive information is protected.

### Frontend

- [ ] Components have focused responsibilities.
- [ ] Loading, success, empty, and error states are considered.
- [ ] API operations handle failures.
- [ ] Interface is accessible and responsive.

### Testing

- [ ] Relevant automated tests pass.
- [ ] Important failure cases are covered.
- [ ] No real credentials are required for ordinary tests.

### Documentation

- [ ] Relevant documentation is updated.
- [ ] API contract changes are reflected in OpenAPI.
- [ ] Commit message describes the change accurately.

---

## 14. Tooling Policy

Tooling will be introduced progressively.

Potential tools include:

| Tool       | Purpose            | Introduction           |
| ---------- | ------------------ | ---------------------- |
| Black      | Python formatting  | Backend setup          |
| Ruff       | Python linting     | Backend setup          |
| ESLint     | JavaScript linting | Frontend setup         |
| Prettier   | Formatting         | Frontend setup         |
| pytest     | Python testing     | Backend testing setup  |
| Vitest     | Frontend testing   | Frontend testing setup |
| Playwright | End-to-end testing | Integration phase      |

Tool versions and configurations should be recorded in project files when adopted.

Avoid introducing tools without understanding what problem they solve.

---

## 15. Related Documents

- [Frontend Architecture](../02-system-design/frontend-architecture.md)
- [Backend Architecture](../02-system-design/backend-architecture.md)
- [Security Architecture](../02-system-design/security-architecture.md)
- [API Overview](../03-api/api-overview.md)
- [API Endpoint Reference](../03-api/endpoint-reference.md)
- [OpenAPI Specification](../03-api/openapi.yaml)
- [Development Setup](../04-engineering/development-setup.md)
- [Testing Strategy](../04-engineering/testing-strategy.md)

---

**Document status:** Initial engineering standards
**Implementation status:** Not started
**Frontend language:** JavaScript / JSX
**Backend language:** Python
