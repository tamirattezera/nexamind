# NexaMind — Architecture Diagrams

## 1. Purpose

The `diagrams/` directory contains visual representations of the NexaMind system architecture, application workflows, data relationships, and infrastructure.

Diagrams complement written technical documentation by making system components, responsibilities, interactions, and dependencies easier to understand.

They should represent the intended architecture during planning and be updated as implementation decisions evolve.

## 2. Diagram Principles

All NexaMind architecture diagrams should follow these principles:

1. **Accuracy:** A diagram must reflect documented architectural decisions.
2. **Clarity:** Show only the components and relationships necessary to explain the subject.
3. **Consistency:** Use consistent names for components, services, entities, and API boundaries.
4. **Maintainability:** Keep diagram source files version-controlled.
5. **Security awareness:** Never expose API keys, credentials, tokens, or sensitive infrastructure details.
6. **Traceability:** Link diagrams to the relevant architecture documents.
7. **Implementation alignment:** Clearly distinguish proposed architecture from implemented and verified architecture.

## 3. Diagram Technology

NexaMind will initially use **Mermaid** for architecture diagrams.

Mermaid is appropriate because:

- It uses text-based diagram definitions.
- Diagram source can be reviewed through Git.
- It integrates with Markdown documentation.
- It supports flowcharts, sequence diagrams, and entity relationship diagrams.
- It is easy to update during iterative development.

Diagrams should use fenced Mermaid code blocks in Markdown documents where practical.

Separate `.mmd` source files may be introduced when a diagram becomes large or needs to be reused across multiple documents.

Rendered SVG or PNG files should only be added when a specific presentation or documentation requirement needs them.

## 4. Architecture Diagram Inventory

The following diagrams are planned for NexaMind.

| ID   | Diagram                               | Purpose                                                      | Related document                                |
| ---- | ------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------- |
| D-01 | System Context Diagram                | Shows NexaMind and its external actors and systems           | `system-context.md`                             |
| D-02 | High-Level Architecture Diagram       | Shows frontend, backend, database, and Gemini integration    | `architecture-overview.md`                      |
| D-03 | Frontend Component Architecture       | Shows the organization of frontend responsibilities          | `frontend-architecture.md`                      |
| D-04 | Backend Application Architecture      | Shows Django applications and backend responsibilities       | `backend-architecture.md`                       |
| D-05 | AI Generation Workflow                | Shows how messages and conversation context reach Gemini     | `ai-architecture.md`                            |
| D-06 | Database ER Diagram                   | Shows entities, relationships, and constraints               | `database-design.md`                            |
| D-07 | Authentication and Authorization Flow | Shows authentication and resource ownership checks           | `security-architecture.md`                      |
| D-08 | Message Request Sequence              | Shows the lifecycle of a user message and AI response        | `backend-architecture.md`, `ai-architecture.md` |
| D-09 | Deployment Architecture               | Shows production infrastructure and deployment relationships | `deployment-guide.md`                           |

## 5. Diagram Index

### 5.1 System Context Diagram

**ID:** D-01

**Objective:** Explain the boundary of NexaMind and how users and external services interact with it.

Expected elements:

- End user.
- NexaMind frontend.
- NexaMind backend.
- PostgreSQL database.
- Google Gemini API.

The diagram should distinguish external systems from NexaMind-owned components.

### 5.2 High-Level Architecture Diagram

**ID:** D-02

**Objective:** Show the main application components and their communication boundaries.

Expected elements:

- React frontend.
- HTTP API communication.
- Django REST Framework backend.
- Authentication and authorization.
- Conversation and message management.
- Gemini integration service.
- PostgreSQL.
- Google Gemini API.

The diagram should make clear that the frontend communicates with Gemini through the backend rather than calling Gemini directly.

### 5.3 Frontend Component Architecture

**ID:** D-03

**Objective:** Explain how the React frontend is organized.

Expected elements:

- Application entry point.
- Application providers and routing.
- Shared UI components.
- Authentication feature.
- Chat feature.
- Conversation feature.
- Settings feature.
- API client and shared utilities.

The diagram should reflect the actual frontend structure as it develops.

### 5.4 Backend Application Architecture

**ID:** D-04

**Objective:** Explain the responsibility boundaries inside the Django backend.

Expected elements:

- Django configuration.
- API layer.
- Accounts application.
- Conversations application.
- Messages application.
- AI integration.
- Database access.

The diagram should distinguish API handling, business operations, data access, and external AI communication.

### 5.5 AI Generation Workflow

**ID:** D-05

**Objective:** Explain how NexaMind constructs and submits requests to Gemini.

Expected workflow:

1. Receive a message from an authenticated user.
2. Verify conversation ownership.
3. Retrieve the relevant conversation history.
4. Apply conversation-specific custom instructions.
5. Construct the model request.
6. Call the Gemini API.
7. Process the response and available usage metadata.
8. Persist the messages.
9. Return the result to the frontend.

The diagram should also account for validation errors, provider failures, and persistence failures.

### 5.6 Database ER Diagram

**ID:** D-06

**Objective:** Show the relationships between the main database entities.

Initial entities:

- User
- Conversation
- Message

Expected relationships:

- One user can own multiple conversations.
- One conversation belongs to one user.
- One conversation can contain multiple messages.
- Each message belongs to one conversation.

The diagram must remain consistent with `database-design.md` and the actual Django models.

### 5.7 Authentication and Authorization Flow

**ID:** D-07

**Objective:** Explain how NexaMind identifies users and protects their resources.

Expected elements:

- Registration and login.
- JWT authentication.
- Authenticated API requests.
- Token validation.
- Conversation ownership checks.
- Authorization success and failure.

The diagram should distinguish authentication (who the user is) from authorization (what the user is allowed to access).

### 5.8 Message Request Sequence Diagram

**ID:** D-08

**Objective:** Show the interactions between the frontend, backend, database, and Gemini during a message request.

The sequence should cover both the successful request path and important failure paths.

### 5.9 Deployment Architecture

**ID:** D-09

**Objective:** Show how NexaMind components will be deployed in production.

Expected elements may include:

- Frontend hosting.
- Backend hosting.
- PostgreSQL hosting.
- Gemini API.
- Environment variables and secret management.
- HTTPS communication.

The final diagram must reflect the actual hosting providers and deployment configuration selected during the deployment phase.

## 6. Diagram Naming Convention

Use descriptive, lowercase filenames with hyphens.

Examples:

```text
system-context.mmd
high-level-architecture.mmd
frontend-component-architecture.mmd
backend-application-architecture.mmd
ai-generation-workflow.mmd
database-er-diagram.mmd
authentication-authorization-flow.mmd
message-request-sequence.mmd
deployment-architecture.mmd
```

These filenames apply if separate Mermaid source files become necessary. Otherwise, keep the Mermaid source inside the corresponding Markdown document.

## 7. Diagram Maintenance Workflow

Whenever an architectural decision changes:

1. Identify the affected architecture document.
2. Update the written documentation.
3. Identify diagrams affected by the change.
4. Update the relevant Mermaid source.
5. Review component names and relationships for consistency.
6. Check that the diagram renders correctly.
7. Commit the documentation and diagram changes together.

Diagrams must not describe a design that contradicts the written architecture.

## 8. Diagram Status

The following table tracks the planned diagrams.

| ID   | Diagram                               | Status   |
| ---- | ------------------------------------- | -------- |
| D-01 | System Context                        | Planned  |
| D-02 | High-Level Architecture               | Planned  |
| D-03 | Frontend Component Architecture       | Planned  |
| D-04 | Backend Application Architecture      | Planned  |
| D-05 | AI Generation Workflow                | Planned  |
| D-06 | Database ER Diagram                   | Planned  |
| D-07 | Authentication and Authorization Flow | Planned  |
| D-08 | Message Request Sequence              | Planned  |
| D-09 | Deployment Architecture               | Deferred |

**Status definitions:**

- **Planned:** Identified but not yet created or verified.
- **Draft:** Initial diagram created but not reviewed.
- **Reviewed:** Checked against the relevant documentation.
- **Verified:** Checked against the implemented system.
- **Deferred:** Intentionally postponed until a later phase.

## 9. Important Documentation Rule

During the planning phase, diagrams represent the proposed system architecture.

After implementation begins, update them based on actual application behavior and verified technical decisions.

Never label a planned component as implemented or a proposed workflow as tested.

## 10. Related Documents

- [Project README](../../README.md)
- [System Context](system-context.md)
- [Architecture Overview](architecture-overview.md)
- [Frontend Architecture](frontend-architecture.md)
- [Backend Architecture](backend-architecture.md)
- [AI Architecture](ai-architecture.md)
- [Database Design](database-design.md)
- [Security Architecture](security-architecture.md)
