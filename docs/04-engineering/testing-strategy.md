# Testing Strategy

## Related Documents

- [Development Setup](https://github.com/tamirattezera/nexamind/blob/main/docs/04-engineering/development-setup.md)
- [Coding Standards](https://github.com/tamirattezera/nexamind/blob/main/docs/04-engineering/coding-standards.md)
- [Git Workflow](https://github.com/tamirattezera/nexamind/blob/main/docs/04-engineering/git-workflow.md)
- [Dependency Management](https://github.com/tamirattezera/nexamind/blob/main/docs/04-engineering/dependency-management.md)
- [Functional Requirements](https://github.com/tamirattezera/nexamind/blob/main/docs/01-requirements/functional-requirements.md)
- [Acceptance Criteria](https://github.com/tamirattezera/nexamind/blob/main/docs/01-requirements/acceptance-criteria.md)
- [Backend Architecture](https://github.com/tamirattezera/nexamind/blob/main/docs/02-system-design/backend-architecture.md)
- [Frontend Architecture](https://github.com/tamirattezera/nexamind/blob/main/docs/02-system-design/frontend-architecture.md)
- [Database Design](https://github.com/tamirattezera/nexamind/blob/main/docs/02-system-design/database-design.md)
- [Security Architecture](https://github.com/tamirattezera/nexamind/blob/main/docs/02-system-design/security-architecture.md)
- [API Overview](https://github.com/tamirattezera/nexamind/blob/main/docs/03-api/api-overview.md)
- [OpenAPI Specification](https://github.com/tamirattezera/nexamind/blob/main/docs/03-api/openapi.yaml)
- [Gemini Integration](https://github.com/tamirattezera/nexamind/blob/main/docs/05-ai-engineering/gemini-integration.md)
- [Deployment Guide](https://github.com/tamirattezera/nexamind/blob/main/docs/06-deployment/deployment-guide.md)

## 1. Purpose

This document defines the testing approach for NexaMind.

The objective is to build confidence that the application behaves correctly, protects user data, handles failures, and remains maintainable as new features are introduced.

Testing will cover:

- Backend business logic.
- Django models and database operations.
- Django REST Framework API endpoints.
- Authentication and authorization.
- Gemini integration.
- React components and user interactions.
- Frontend-backend integration.
- End-to-end user workflows.
- Security and reliability requirements.

Testing is part of implementation, not a final activity performed only before deployment.

---

## 2. Testing Principles

NexaMind follows these principles:

1. **Test behavior, not implementation details.** Tests should verify observable outcomes rather than depend unnecessarily on internal code structure.
2. **Test critical paths first.** Authentication, conversation ownership, message persistence, and AI response handling deserve high priority.
3. **Isolate external dependencies.** Automated tests should not require a live Gemini API call.
4. **Use realistic test data.** Test users, conversations, messages, and API requests should reflect actual application behavior.
5. **Test failure scenarios.** Successful responses alone do not demonstrate reliability.
6. **Keep tests repeatable.** The same test should produce consistent results under the same conditions.
7. **Avoid testing only for coverage.** Coverage is useful, but passing meaningful behavior tests matters more than achieving a percentage.
8. **Run relevant checks before committing.**

---

## 3. Testing Levels

NexaMind uses several complementary testing levels.

| Testing level       | What it verifies                                        | Example                                      |
| ------------------- | ------------------------------------------------------- | -------------------------------------------- |
| Unit testing        | Individual functions and isolated logic                 | Validate conversation title generation       |
| Integration testing | Interaction between application components              | API endpoint saves a message to PostgreSQL   |
| API testing         | HTTP contracts and endpoint behavior                    | POST a message and verify its response       |
| Component testing   | Individual React components                             | Chat input handles submission                |
| End-to-end testing  | Complete user workflows                                 | Register, log in, and send a message         |
| Security testing    | Protection against unauthorized access and unsafe input | User A cannot retrieve User B's conversation |

Each level addresses a different type of risk. Passing one level does not guarantee that the others will pass.

---

## 4. Backend Testing Strategy

### 4.1 Backend testing tools

The planned backend testing tools are:

| Tool                                 | Purpose                                       |
| ------------------------------------ | --------------------------------------------- |
| Django test framework                | Django application and database testing       |
| Django REST Framework test utilities | API endpoint testing                          |
| `unittest.mock`                      | Mocking external dependencies                 |
| pytest                               | Optional test runner and fixtures, if adopted |
| Coverage.py                          | Measuring test coverage                       |

We will begin with Django's built-in testing capabilities and introduce additional tools when they provide practical value.

### 4.2 Model tests

Model tests verify database structure, constraints, relationships, and model behavior.

Examples:

- A conversation belongs to exactly one user.
- A message belongs to a conversation.
- A conversation receives appropriate default values.
- Message roles accept only supported values.
- UUID identifiers are generated correctly.
- Timestamps are populated correctly.

Example test scenarios:

```text
Given an authenticated user,
When the user creates a conversation,
Then the conversation is associated with that user.

Given a conversation,
When a message is created,
Then the message is associated with that conversation.
```

### 4.3 Business logic tests

Business logic tests verify application rules independently of HTTP request handling where practical.

Examples:

- Conversation title generation.
- Conversation ownership checks.
- Message ordering.
- Context construction from conversation history.
- Custom instruction handling.
- Provider error translation.

### 4.4 API tests

API tests verify the actual HTTP interface.

They should cover:

- HTTP methods.
- Request validation.
- Authentication requirements.
- Authorization and ownership.
- Response status codes.
- Response JSON structure.
- Database changes.
- Error responses.
- Pagination behavior where implemented.

Example:

```text
POST /api/v1/conversations/
```

Expected behavior:

1. An authenticated user submits a valid conversation request.
2. The backend validates the request.
3. A conversation is created for the authenticated user.
4. The response contains the created conversation.
5. The conversation is stored in the database.

The test should also verify that an unauthenticated request is rejected.

---

## 5. Authentication and Authorization Testing

Authentication and authorization are critical because NexaMind is a multi-user application.

Tests must verify both identity and resource ownership.

### Required scenarios

| Scenario                                         | Expected result                                                   |
| ------------------------------------------------ | ----------------------------------------------------------------- |
| Register with valid information                  | Account is created                                                |
| Register with invalid information                | Validation error                                                  |
| Register with an existing email                  | Duplicate account rejected according to the chosen account policy |
| Log in with valid credentials                    | Authentication succeeds                                           |
| Log in with incorrect credentials                | Authentication fails                                              |
| Access protected endpoint without credentials    | Request rejected                                                  |
| Access protected endpoint with valid credentials | Request permitted                                                 |
| User A accesses User B's conversation            | Access denied                                                     |
| User A requests User B's messages                | Access denied                                                     |
| User accesses their own conversation             | Access permitted                                                  |

### Ownership security rule

The backend must derive the current user from the authenticated request.

It must not trust a client-provided user ID to decide ownership.

Tests should verify ownership enforcement on every relevant conversation and message endpoint.

---

## 6. Gemini Integration Testing

Gemini is an external service. Tests must distinguish between application logic and actual provider communication.

### 6.1 Mocked provider tests

Most automated tests should mock the Gemini service or its SDK boundary.

A mock allows the application to simulate:

- Successful text generation.
- Empty or unusable provider output.
- Provider errors.
- Authentication failures.
- Rate-limit responses.
- Timeouts.
- Unexpected response structures.

Example conceptual test:

```python
def test_generate_response_returns_text():
    # Arrange
    # Configure a mocked Gemini response.

    # Act
    # Call the application service.

    # Assert
    # Verify the returned text.
```

This is an illustrative structure, not an implemented test.

### 6.2 Integration tests with a real provider

A small number of controlled integration tests may call the real Gemini API.

These tests should:

- Require an explicitly configured API key.
- Be excluded from the normal test suite by default.
- Avoid hardcoding credentials.
- Use a deliberately selected model and minimal test input.
- Handle provider availability and quota limitations.
- Avoid depending on exact generated wording.

A real model response can vary. Therefore, tests should verify broad response properties rather than exact prose.

### 6.3 Provider boundary

Application tests should depend on the NexaMind Gemini service interface, not spread direct SDK calls throughout the codebase.

This makes it possible to mock provider behavior without mocking every application component separately.

---

## 7. Database Testing

NexaMind will use PostgreSQL as its target database.

Database tests should verify:

- Model creation and relationships.
- Database constraints.
- Migrations.
- Query behavior.
- Ordering and pagination.
- Transaction behavior.
- Data isolation between users.
- Correct deletion behavior.

### Database environment

Automated tests should use a dedicated test database managed by the test framework.

Never run destructive tests against production data.

SQLite may be useful for isolated experiments, but it should not be treated as a substitute for PostgreSQL verification. PostgreSQL-specific behavior must be tested against PostgreSQL.

---

## 8. Frontend Testing Strategy

### 8.1 Planned tools

| Tool                          | Purpose                                   |
| ----------------------------- | ----------------------------------------- |
| Vitest                        | JavaScript unit and component test runner |
| React Testing Library         | React component behavior                  |
| `@testing-library/user-event` | Simulating user interactions              |
| MSW (Mock Service Worker)     | Mocking HTTP API responses                |
| Playwright                    | Browser-based end-to-end testing          |

These tools will be introduced progressively rather than all at once.

### 8.2 Component tests

Test components based on their responsibilities.

Examples:

**ChatInput**

- Renders the input field.
- Accepts user text.
- Submits valid messages.
- Prevents empty submissions.
- Handles disabled state while sending.

**MessageList**

- Displays user and assistant messages.
- Handles an empty conversation.
- Displays loading state.
- Displays an error state.

**ConversationSidebar**

- Displays available conversations.
- Allows selecting a conversation.
- Displays an appropriate empty state.
- Handles loading and error states.

**LoginForm**

- Accepts credentials.
- Validates required fields.
- Displays authentication errors.
- Submits valid credentials.

Tests should focus on what users can observe and do.

### 8.3 API interaction tests

Frontend API tests should mock HTTP responses.

Verify:

- Correct request method and URL.
- Expected request payload.
- Authorization header behavior.
- Successful response handling.
- Loading state.
- API error handling.
- Network failure handling.

Do not require a live backend or Gemini service for every component test.

---

## 9. End-to-End Testing

End-to-end tests verify that important workflows work across the application.

Playwright is the planned tool.

### Core user workflows

**Workflow 1: Account registration**

1. Open the application.
2. Navigate to registration.
3. Submit valid account information.
4. Verify successful registration behavior.

**Workflow 2: Authentication**

1. Open the login page.
2. Submit valid credentials.
3. Verify access to the authenticated application.

**Workflow 3: Conversation creation**

1. Log in.
2. Create a new conversation.
3. Verify it appears in the conversation sidebar.

**Workflow 4: Sending a message**

1. Open a conversation.
2. Enter a message.
3. Submit it.
4. Verify the user message appears.
5. Verify the assistant response appears.

**Workflow 5: Conversation persistence**

1. Send a message.
2. Reload the application.
3. Reopen the conversation.
4. Verify the conversation history remains available.

**Workflow 6: Conversation management**

1. Rename a conversation.
2. Verify the updated title.
3. Delete a conversation.
4. Verify it no longer appears in the user's conversation list.

**Workflow 7: User isolation**

1. Authenticate as User A.
2. Create a conversation.
3. Authenticate as User B in a separate browser context.
4. Attempt to access User A's conversation.
5. Verify access is denied.

End-to-end tests should use controlled test accounts and isolated test data.

---

## 10. Error and Failure Testing

NexaMind must be tested under failure conditions, not only ideal conditions.

| Failure scenario                 | Expected behavior                                  |
| -------------------------------- | -------------------------------------------------- |
| Invalid request payload          | Clear validation response                          |
| Expired or invalid token         | Authentication rejected                            |
| Missing conversation             | Appropriate not-found response                     |
| Unauthorized conversation access | Access denied without leaking data                 |
| Gemini timeout                   | Controlled provider error                          |
| Gemini rate limit                | Appropriate failure handling                       |
| Gemini unavailable               | User receives a useful error                       |
| Database failure                 | Request fails safely                               |
| Network interruption             | Frontend displays a recoverable error state        |
| Empty AI response                | Application handles it without fabricating content |

The exact HTTP status codes and persistence behavior must follow the final API contract and implementation.

For message generation, tests must specifically verify what happens when the user message is saved but Gemini fails. The application must not silently create a fabricated assistant response. The final persistence and retry strategy will be defined during implementation.

---

## 11. Security Testing

Security testing will focus on the most important application risks.

### Required checks

- Authentication is required for protected endpoints.
- Conversation ownership is enforced on the backend.
- User passwords are handled by Django's secure password mechanisms.
- Gemini credentials are not exposed in frontend code.
- Sensitive values are not returned in API responses.
- Input validation prevents malformed requests.
- Error responses do not expose stack traces or secrets in production.
- CORS configuration permits only intended frontend origins.
- JWT expiration and refresh behavior follow the configured authentication policy.
- Deletion and retrieval operations respect ownership.

Security checks should be added alongside the relevant feature tests, not postponed until deployment.

---

## 12. Test Data and Isolation

Tests should create their own data and clean it up reliably.

Use:

- Dedicated test users.
- Dedicated conversations.
- Controlled messages.
- Mocked provider responses.
- Isolated database state.

Avoid depending on records created manually during development.

Tests must not depend on execution order or on data left behind by previous tests.

Where practical, test setup should use reusable factories or fixtures rather than large amounts of duplicated setup code.

---

## 13. Test Organization

The repository may use the following organization as the application grows:

```text
backend/
├── apps/
│   ├── accounts/
│   │   └── tests/
│   ├── conversations/
│   │   └── tests/
│   ├── messages/
│   │   └── tests/
│   └── ai/
│       └── tests/
└── tests/
    ├── integration/
    └── factories/

frontend/
└── src/
    └── features/
        ├── auth/
        ├── chat/
        └── conversations/

tests/
└── e2e/
```

Frontend tests may live beside their components or feature modules. The final placement should follow the actual Vite and Vitest configuration.

---

## 14. Continuous Integration

Continuous integration can automatically run checks when code is pushed to GitHub.

Planned checks include:

**Backend**

- Dependency installation.
- Django system checks.
- Automated tests.
- Optional coverage reporting.

**Frontend**

- Dependency installation.
- Linting.
- Unit and component tests.
- Production build.

**Repository**

- Secret scanning where available.
- Configuration validation.
- Documentation checks where useful.

GitHub Actions will be introduced after the basic backend and frontend test commands are stable.

---

## 15. Test Execution Strategy

Run tests at different scopes depending on the task.

| Scope                  | When to run                                         |
| ---------------------- | --------------------------------------------------- |
| Focused unit tests     | While implementing a specific function or component |
| Relevant app tests     | After changing an application feature               |
| Backend test suite     | After meaningful backend changes                    |
| Frontend test suite    | After meaningful frontend changes                   |
| Full integration tests | Before completing major milestones                  |
| End-to-end tests       | Before important releases and deployment            |

Example commands will depend on the actual project configuration.

Backend:

```bash
python manage.py check
python manage.py test
```

Frontend:

```bash
npm run lint
npm run test
npm run build
```

End-to-end:

```bash
npx playwright test
```

Do not assume these commands are configured until the relevant scripts and dependencies exist.

---

## 16. Coverage and Quality Targets

Coverage can help identify untested code, but it is not a substitute for meaningful test cases.

Initial quality priorities:

1. Authentication and authorization.
2. Conversation ownership and isolation.
3. Message creation and persistence.
4. Gemini success and failure handling.
5. API request validation.
6. Critical React interactions.
7. Complete user workflows.

Coverage reports may be introduced after the initial testing setup.

A high coverage percentage does not prove that the application is secure, correct, or reliable.

---

## 17. Definition of Done

A feature is not considered complete merely because its code has been written.

A feature is ready to be marked complete when:

- [ ] The expected behavior is implemented.
- [ ] Relevant validation is present.
- [ ] Appropriate tests have been written.
- [ ] Relevant tests pass.
- [ ] Failure scenarios have been considered.
- [ ] Security and ownership requirements are respected.
- [ ] Documentation is updated where necessary.
- [ ] No unintended changes or secrets are included.
- [ ] The implementation has been reviewed.

Deployment readiness requires additional environment and production verification.

---

## 18. Final Principle

Testing is an engineering feedback system.

It helps NexaMind detect defects early, protect user data, isolate external provider failures, and make future changes safer.

The goal is not to test everything in the same way. The goal is to choose the right test at the right level and verify the behavior that matters most to users and the system.
