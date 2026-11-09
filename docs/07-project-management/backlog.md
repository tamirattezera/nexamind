# NexaMind — Project Backlog

**Document:** Project Backlog
**Project:** NexaMind AI Chat
**Status:** Planning
**Version:** 1.0
**Last Updated:** 2026-11-07

---

## 1. Purpose

This document defines the actionable work required to build NexaMind.

It organizes project work into:

- **Epics:** Large areas of project work.
- **Features:** Major capabilities within an epic.
- **Tasks:** Specific pieces of work that can be implemented and verified.

The backlog supports implementation planning, progress tracking, prioritization, and engineering accountability.

## 2. Relationship to Other Planning Documents

| Document      | Responsibility                                                  |
| ------------- | --------------------------------------------------------------- |
| Roadmap       | Defines the overall development sequence.                       |
| Milestones    | Defines completion gates and required evidence.                 |
| Backlog       | Defines the actionable work required to reach those milestones. |
| Risk register | Tracks uncertainties and threats that could affect delivery.    |

The roadmap answers _where are we going?_ The milestones answer _what must be achieved?_ The backlog answers _what work must be done?_

## 3. Backlog Conventions

### 3.1 Work item hierarchy

```text
Epic
 ├── Feature
 │    ├── Task
 │    └── Task
 └── Feature
      └── Task
```

### 3.2 ID conventions

| Work item | ID format    | Example      |
| --------- | ------------ | ------------ |
| Epic      | `NM-EPIC-XX` | `NM-EPIC-01` |
| Task      | `NM-XXX`     | `NM-001`     |

IDs should remain stable even when task descriptions change.

### 3.3 Priority levels

| Priority | Meaning                                                   |
| -------- | --------------------------------------------------------- |
| P0       | Essential for the MVP or a critical security requirement. |
| P1       | Important for a complete and reliable MVP.                |
| P2       | Useful improvement that can follow the core MVP.          |

Priority does not automatically determine implementation order. Dependencies and milestone sequencing also matter.

### 3.4 Status definitions

| Status      | Meaning                                                                     |
| ----------- | --------------------------------------------------------------------------- |
| Not started | Work has not begun.                                                         |
| In progress | Work is actively being implemented.                                         |
| Blocked     | Work cannot proceed because of an unresolved dependency or issue.           |
| In review   | Work is awaiting verification or review.                                    |
| Done        | Acceptance criteria have been verified and evidence exists.                 |
| Deferred    | Work has intentionally been moved outside the current implementation scope. |

Do not mark an item Done merely because its documentation has been drafted.

---

# 4. Product and Engineering Backlog

## EPIC 01 — Project Foundation and Documentation

**ID:** `NM-EPIC-01`
**Priority:** P0
**Roadmap phase:** M0–M1
**Objective:** Establish a clear product definition, repository structure, engineering standards, and documentation baseline.

### Features and tasks

| ID     | Task                                                           | Priority | Dependencies  |
| ------ | -------------------------------------------------------------- | -------- | ------------- |
| NM-001 | Create the NexaMind repository structure.                      | P0       | None          |
| NM-002 | Add root README and project overview.                          | P0       | NM-001        |
| NM-003 | Add project foundation documents.                              | P0       | NM-001        |
| NM-004 | Document functional and non-functional requirements.           | P0       | NM-003        |
| NM-005 | Document system and component architecture.                    | P0       | NM-004        |
| NM-006 | Document database and security architecture.                   | P0       | NM-005        |
| NM-007 | Document API contracts and endpoint reference.                 | P0       | NM-005        |
| NM-008 | Document development and testing standards.                    | P0       | NM-001        |
| NM-009 | Document Gemini integration and AI safety.                     | P0       | NM-005        |
| NM-010 | Document deployment and environment strategy.                  | P1       | NM-005        |
| NM-011 | Review documentation for consistency and unresolved decisions. | P0       | NM-002–NM-010 |

**Acceptance criteria:**

- The repository structure matches the agreed architecture.
- Documentation is saved in the correct locations.
- No major contradictions exist between requirements, architecture, and API documentation.
- Unresolved decisions are clearly identified.
- The documentation baseline is reviewed before implementation begins.

## EPIC 02 — Backend Foundation

**ID:** `NM-EPIC-02`
**Priority:** P0
**Roadmap phase:** M2
**Objective:** Establish a maintainable Django REST Framework backend.

| ID     | Task                                             | Priority | Dependencies |
| ------ | ------------------------------------------------ | -------- | ------------ |
| NM-012 | Set up the Python virtual environment.           | P0       | NM-011       |
| NM-013 | Initialize the Django project.                   | P0       | NM-012       |
| NM-014 | Install and configure Django REST Framework.     | P0       | NM-013       |
| NM-015 | Configure environment-variable management.       | P0       | NM-013       |
| NM-016 | Establish backend application structure.         | P0       | NM-014       |
| NM-017 | Configure development and test settings.         | P0       | NM-015       |
| NM-018 | Add initial backend health-check endpoint.       | P1       | NM-016       |
| NM-019 | Verify backend startup and basic test execution. | P0       | NM-017       |

**Acceptance criteria:**

- The backend starts successfully.
- Dependencies are recorded and reproducible.
- Secrets are loaded from environment variables.
- Development and test configuration are separated.
- Initial automated tests execute successfully.

## EPIC 03 — Database and Authentication

**ID:** `NM-EPIC-03`
**Priority:** P0
**Roadmap phase:** M3
**Objective:** Establish PostgreSQL persistence and secure multi-user authentication.

| ID     | Task                                                       | Priority | Dependencies |
| ------ | ---------------------------------------------------------- | -------- | ------------ |
| NM-020 | Configure PostgreSQL connection.                           | P0       | NM-019       |
| NM-021 | Design the custom Django user model.                       | P0       | NM-020       |
| NM-022 | Configure the custom user model before initial migrations. | P0       | NM-021       |
| NM-023 | Implement database migrations.                             | P0       | NM-022       |
| NM-024 | Implement user registration.                               | P0       | NM-023       |
| NM-025 | Implement login and token issuance.                        | P0       | NM-024       |
| NM-026 | Implement token refresh and authentication validation.     | P0       | NM-025       |
| NM-027 | Test authentication success and failure cases.             | P0       | NM-026       |

**Acceptance criteria:**

- PostgreSQL connection works.
- The custom user model is configured before initial migrations.
- Registration and authentication work.
- Passwords are never stored in plaintext.
- Invalid and expired credentials are handled correctly.
- Authentication tests pass.

## EPIC 04 — Backend Architecture and Business Logic

**ID:** `NM-EPIC-04`
**Priority:** P0
**Roadmap phase:** M4
**Objective:** Build clear backend responsibilities and enforce data ownership.

| ID     | Task                                                            | Priority | Dependencies   |
| ------ | --------------------------------------------------------------- | -------- | -------------- |
| NM-028 | Establish API, serializer, service, and model responsibilities. | P0       | NM-027         |
| NM-029 | Implement conversation data model.                              | P0       | NM-028         |
| NM-030 | Implement message data model.                                   | P0       | NM-029         |
| NM-031 | Implement conversation ownership rules.                         | P0       | NM-029         |
| NM-032 | Implement message ownership and access rules.                   | P0       | NM-030         |
| NM-033 | Implement conversation and message validation.                  | P0       | NM-030         |
| NM-034 | Test cross-user data isolation.                                 | P0       | NM-031, NM-032 |

**Acceptance criteria:**

- Conversations belong to authenticated users.
- Messages belong to conversations.
- Users cannot access another user's conversations or messages.
- Business rules are enforced on the backend.
- Ownership and validation tests pass.

## EPIC 05 — Gemini Integration

**ID:** `NM-EPIC-05`
**Priority:** P0
**Roadmap phase:** M5
**Objective:** Integrate Gemini through a backend-controlled service.

| ID     | Task                                                      | Priority | Dependencies   |
| ------ | --------------------------------------------------------- | -------- | -------------- |
| NM-035 | Verify the official Google GenAI SDK and supported model. | P0       | NM-028         |
| NM-036 | Configure the Gemini API key securely.                    | P0       | NM-015         |
| NM-037 | Implement a focused Gemini service.                       | P0       | NM-035, NM-036 |
| NM-038 | Define the backend-to-provider request format.            | P0       | NM-037         |
| NM-039 | Implement conversation context construction.              | P0       | NM-030, NM-037 |
| NM-040 | Integrate custom conversation instructions.               | P1       | NM-039         |
| NM-041 | Handle provider errors and timeouts.                      | P0       | NM-037         |
| NM-042 | Test Gemini integration using mocked provider responses.  | P0       | NM-037–NM-041  |

**Acceptance criteria:**

- Gemini requests originate from the backend.
- The API key is never exposed to the frontend.
- Context is reconstructed from authorized conversation history.
- Custom instructions are treated as untrusted input.
- Provider failures do not corrupt conversation history.
- Automated tests do not depend on live Gemini calls.

## EPIC 06 — Conversation APIs

**ID:** `NM-EPIC-06`
**Priority:** P0
**Roadmap phase:** M6
**Objective:** Expose reliable APIs for managing conversations and exchanging messages.

| ID     | Task                                                      | Priority | Dependencies   |
| ------ | --------------------------------------------------------- | -------- | -------------- |
| NM-043 | Implement conversation creation endpoint.                 | P0       | NM-034         |
| NM-044 | Implement conversation listing endpoint.                  | P0       | NM-043         |
| NM-045 | Implement conversation detail endpoint.                   | P0       | NM-043         |
| NM-046 | Implement message submission endpoint.                    | P0       | NM-042, NM-043 |
| NM-047 | Persist user messages and successful assistant responses. | P0       | NM-046         |
| NM-048 | Implement conversation rename endpoint.                   | P1       | NM-043         |
| NM-049 | Implement conversation deletion endpoint.                 | P1       | NM-043         |
| NM-050 | Implement custom instruction update endpoint.             | P1       | NM-040         |
| NM-051 | Test API permissions, validation, and error responses.    | P0       | NM-043–NM-050  |

**Acceptance criteria:**

- Authenticated users can create and retrieve conversations.
- Users can send messages and receive Gemini responses.
- Messages persist in PostgreSQL.
- Conversation operations enforce ownership.
- API errors use predictable response structures.
- API tests cover success and failure scenarios.

## EPIC 07 — API Documentation and Contract Verification

**ID:** `NM-EPIC-07`
**Priority:** P1
**Roadmap phase:** M7
**Objective:** Keep API documentation aligned with actual backend behavior.

| ID     | Task                                              | Priority | Dependencies |
| ------ | ------------------------------------------------- | -------- | ------------ |
| NM-052 | Verify endpoint reference against implementation. | P1       | NM-051       |
| NM-053 | Generate or maintain OpenAPI documentation.       | P1       | NM-052       |
| NM-054 | Document authentication and error responses.      | P1       | NM-053       |
| NM-055 | Test documented request and response examples.    | P1       | NM-054       |

**Acceptance criteria:**

- API documentation matches implemented endpoints.
- Authentication requirements are clear.
- Request and response schemas are accurate.
- Documented examples are verified.

## EPIC 08 — Frontend Foundation

**ID:** `NM-EPIC-08`
**Priority:** P0
**Roadmap phase:** M8
**Objective:** Establish a maintainable React application that communicates with the backend.

| ID     | Task                                                      | Priority | Dependencies |
| ------ | --------------------------------------------------------- | -------- | ------------ |
| NM-056 | Initialize React with Vite and JavaScript.                | P0       | NM-051       |
| NM-057 | Configure frontend project structure.                     | P0       | NM-056       |
| NM-058 | Configure routing.                                        | P0       | NM-056       |
| NM-059 | Configure Axios and centralized API communication.        | P0       | NM-057       |
| NM-060 | Implement frontend environment configuration.             | P0       | NM-059       |
| NM-061 | Establish reusable UI components and styling conventions. | P1       | NM-057       |
| NM-062 | Configure frontend testing tools.                         | P1       | NM-056       |

**Acceptance criteria:**

- React application starts successfully.
- JavaScript is used without introducing TypeScript.
- API communication uses a centralized Axios configuration.
- Environment-specific API URLs are supported.
- Frontend tests can execute.

## EPIC 09 — Authentication and Chat Interface

**ID:** `NM-EPIC-09`
**Priority:** P0
**Roadmap phase:** M9
**Objective:** Build the primary NexaMind user experience.

| ID     | Task                                           | Priority | Dependencies   |
| ------ | ---------------------------------------------- | -------- | -------------- |
| NM-063 | Implement registration interface.              | P0       | NM-060         |
| NM-064 | Implement login interface.                     | P0       | NM-063         |
| NM-065 | Implement frontend authentication state.       | P0       | NM-064         |
| NM-066 | Implement protected routes.                    | P0       | NM-065         |
| NM-067 | Build the main chat layout.                    | P0       | NM-061         |
| NM-068 | Build the message display component.           | P0       | NM-067         |
| NM-069 | Build the message input component.             | P0       | NM-067         |
| NM-070 | Connect the chat interface to the message API. | P0       | NM-069, NM-046 |
| NM-071 | Implement loading, error, and empty states.    | P0       | NM-070         |
| NM-072 | Implement responsive layouts.                  | P1       | NM-067         |

**Acceptance criteria:**

- Users can register and log in.
- Protected routes require authentication.
- Users can submit messages and see responses.
- Loading and failure states are understandable.
- The interface works on desktop and mobile layouts.

## EPIC 10 — Conversation Management

**ID:** `NM-EPIC-10`
**Priority:** P1
**Roadmap phase:** M10
**Objective:** Allow users to organize and manage their chat history.

| ID     | Task                                                    | Priority | Dependencies   |
| ------ | ------------------------------------------------------- | -------- | -------------- |
| NM-073 | Implement conversation sidebar.                         | P1       | NM-044, NM-067 |
| NM-074 | Implement conversation switching.                       | P1       | NM-073         |
| NM-075 | Implement conversation creation from the UI.            | P1       | NM-043         |
| NM-076 | Implement conversation renaming.                        | P1       | NM-048         |
| NM-077 | Implement conversation deletion with confirmation.      | P1       | NM-049         |
| NM-078 | Implement custom instruction settings.                  | P2       | NM-050         |
| NM-079 | Handle conversation loading and synchronization states. | P1       | NM-074         |

**Acceptance criteria:**

- Users can view and switch between their conversations.
- Users can create, rename, and delete conversations.
- The UI reflects persisted backend state.
- Users cannot manage conversations belonging to other accounts.

## EPIC 11 — Reliability, Security, and Quality

**ID:** `NM-EPIC-11`
**Priority:** P0
**Roadmap phase:** M11–M12
**Objective:** Improve application reliability, security, and test coverage.

| ID     | Task                                                    | Priority | Dependencies   |
| ------ | ------------------------------------------------------- | -------- | -------------- |
| NM-080 | Review authentication and authorization controls.       | P0       | NM-051         |
| NM-081 | Add request validation and message-size limits.         | P0       | NM-046         |
| NM-082 | Implement appropriate rate limiting and abuse controls. | P0       | NM-046         |
| NM-083 | Review secret handling and CORS configuration.          | P0       | NM-060         |
| NM-084 | Review safe rendering of AI-generated content.          | P0       | NM-068         |
| NM-085 | Add backend integration tests.                          | P0       | NM-051         |
| NM-086 | Add frontend component and integration tests.           | P1       | NM-072         |
| NM-087 | Add end-to-end tests for critical user journeys.        | P1       | NM-085, NM-086 |
| NM-088 | Test provider failures and recovery behavior.           | P1       | NM-042         |
| NM-089 | Perform a final security and reliability review.        | P0       | NM-080–NM-088  |

**Acceptance criteria:**

- Authentication and ownership controls are tested.
- Inputs are validated on the backend.
- AI-generated content is rendered safely.
- Sensitive information is not exposed in logs or frontend code.
- Critical user journeys have automated test coverage.
- Important failure scenarios are verified.

## EPIC 12 — Deployment and Operations

**ID:** `NM-EPIC-12`
**Priority:** P1
**Roadmap phase:** M13
**Objective:** Deploy NexaMind with production-appropriate configuration and operational visibility.

| ID     | Task                                                    | Priority | Dependencies   |
| ------ | ------------------------------------------------------- | -------- | -------------- |
| NM-090 | Select and verify hosting providers.                    | P1       | NM-089         |
| NM-091 | Provision production PostgreSQL.                        | P1       | NM-090         |
| NM-092 | Configure backend production environment.               | P1       | NM-090         |
| NM-093 | Configure frontend production environment.              | P1       | NM-090         |
| NM-094 | Configure HTTPS and production CORS.                    | P0       | NM-092, NM-093 |
| NM-095 | Configure production migrations and deployment process. | P0       | NM-091, NM-092 |
| NM-096 | Deploy backend and frontend.                            | P1       | NM-094, NM-095 |
| NM-097 | Verify production authentication and chat workflows.    | P0       | NM-096         |
| NM-098 | Verify logging, monitoring, and backup procedures.      | P1       | NM-096         |

**Acceptance criteria:**

- Frontend and backend are deployed.
- Production database connections work.
- Secrets remain outside source control and frontend bundles.
- HTTPS is enabled.
- Production migrations execute safely.
- Critical workflows are verified in the deployed environment.

## EPIC 13 — Final Review and Portfolio Evidence

**ID:** `NM-EPIC-13`
**Priority:** P1
**Roadmap phase:** M14
**Objective:** Complete the engineering review and prepare credible project evidence.

| ID     | Task                                                 | Priority | Dependencies   |
| ------ | ---------------------------------------------------- | -------- | -------------- |
| NM-099 | Review final architecture against implementation.    | P1       | NM-098         |
| NM-100 | Review documentation against the actual application. | P1       | NM-099         |
| NM-101 | Capture application screenshots.                     | P1       | NM-098         |
| NM-102 | Record a working application demonstration.          | P1       | NM-101         |
| NM-103 | Prepare an honest project case study.                | P1       | NM-100, NM-102 |
| NM-104 | Review repository quality and release readiness.     | P1       | NM-099–NM-103  |

**Acceptance criteria:**

- Documentation reflects the actual implementation.
- Screenshots and demonstration show working features.
- The case study explains architecture, trade-offs, challenges, and lessons.
- Known limitations are disclosed.
- The repository is ready for public review.

---

# 5. Deferred Work

The following capabilities are intentionally outside the initial MVP:

| Capability                           | Reason for deferral                                                         |
| ------------------------------------ | --------------------------------------------------------------------------- |
| Retrieval-Augmented Generation (RAG) | Requires document ingestion, retrieval, and additional security design.     |
| File uploads                         | Introduces storage, parsing, validation, and content-security requirements. |
| Web search                           | Requires external retrieval integration and source handling.                |
| Tool calling                         | Requires tool authorization and execution controls.                         |
| Autonomous agents                    | Adds orchestration, state, and safety complexity.                           |
| Multiple AI providers                | Not required to validate the initial Gemini-powered product.                |
| Advanced collaboration               | Not required for the initial individual-user experience.                    |

These items may become future backlog epics after the MVP has been validated.

# 6. Backlog Management Rules

## 6.1 Definition of Ready

A task is ready for implementation when:

- Its purpose is clear.
- Its expected outcome is defined.
- Acceptance criteria are testable.
- Required dependencies are identified.
- Relevant architecture or API decisions are available.
- The task is small enough to implement and verify independently.

## 6.2 Definition of Done

A task is Done only when:

- Implementation is complete.
- Acceptance criteria pass.
- Relevant automated tests pass.
- Code has been reviewed.
- Documentation is updated when necessary.
- Changes are committed to Git.
- Evidence of completion is available.

## 6.3 Work-in-progress control

Work on one primary task at a time whenever practical.

Avoid starting multiple dependent features before their foundations are verified.

When a task becomes blocked:

1. Record the blocker.
2. Identify the affected dependency.
3. Explain what is needed to unblock it.
4. Update the task status.
5. Resume only after the blocker is resolved.

## 6.4 Git and issue tracking

Use task IDs in commit messages and pull request descriptions where practical.

Example:

```text
feat(auth): implement user registration (NM-024)
test(auth): cover invalid login credentials (NM-027)
docs(api): update authentication reference (NM-054)
```

For larger tasks, create GitHub Issues
