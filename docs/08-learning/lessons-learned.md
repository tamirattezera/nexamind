# Lessons Learned

This document captures reusable technical knowledge, engineering principles, and practical insights gained while designing and developing NexaMind.

Unlike the engineering journal, which records project history, and the problem-solving log, which documents individual investigations, this document focuses on what was learned and how that knowledge should influence future engineering decisions.

---

## 1. Development Environment Management

### 1.1 Installing a Runtime Is Not the Same as Selecting It

Installing a Python version does not automatically make it the active runtime.

Tools such as `pyenv` manage version selection independently of installation.

**Lesson:** Always verify the active runtime before creating a project virtual environment.

### 1.2 Virtual Environments Should Be Reproducible

A project should have an isolated Python environment with explicitly declared dependencies.

**Lesson:**

- Use a dedicated virtual environment for each project.
- Pin dependency versions where reproducibility matters.
- Keep virtual environment directories out of Git.
- Maintain dependency files as the source of truth for project setup.

### 1.3 Environment Variables Must Be Separated from Source Code

Application secrets and environment-specific configuration should not be committed to the repository.

**Lesson:**

- Keep actual secrets in `.env`.
- Commit `.env.example` with placeholder values.
- Add `.env` to `.gitignore`.
- Never expose database credentials, Django secret keys, or AI provider API keys in frontend code or Git history.

### 1.4 Understand How Application Configuration Is Loaded

Application configuration can be stored outside source code and loaded when the application initializes.

NexaMind uses `django-environ` to read environment variables from the root `.env` file and make them available to Django settings.

The configuration flow is:

1. The `.env` file stores environment-specific values, such as database name, username, password, host, and port.
2. `django-environ` reads those values into the process environment.
3. Django's `settings.py` retrieves the values through calls such as `env("DB_NAME")`.
4. Django uses the resulting configuration to establish its database connection.

**Lesson:** Understand the responsibility of each component:

- `.env`: stores environment-specific configuration values.
- `django-environ`: reads and converts configuration values.
- `settings.py`: uses those values to configure Django.
- `psycopg`: provides communication between Django and PostgreSQL.
- PostgreSQL: manages and stores application data.

Changing a value in `.env` does not require changing `settings.py` when the setting already reads that value dynamically.

However, editing `.env` does not automatically update the configuration of an already-running Django process. The process must reload its configuration, typically through a restart.

Also, environment variables already present in the process may take precedence over values loaded from `.env`, depending on the configuration.

**Practical principle:** Keep configuration values outside application logic, understand when they are loaded, and verify the effective configuration without exposing secrets.

---

## 2. Django Backend Architecture

### 2.1 A Custom User Model Should Be Established Early

Django allows projects to define a custom user model by extending `AbstractUser`.

NexaMind uses an email-based authentication identity instead of Django's default username-based identity.

**Lesson:** Define `AUTH_USER_MODEL` before creating the first database migration. Changing the user model after dependent migrations and application data exist can be complex.

### 2.2 Authentication and Authorization Are Different Responsibilities

Authentication establishes who is making a request.

Authorization determines whether that authenticated user is allowed to perform the requested operation.

**Lesson:** A successful login does not automatically grant access to every resource. NexaMind must enforce ownership checks for conversations and messages on the backend.

### 2.3 Passwords Must Never Be Stored as Plain Text

Django provides password hashing through its authentication framework.

The custom user manager uses `set_password()` rather than assigning the raw password directly.

**Lesson:** Use Django's password-management APIs and verify passwords with `check_password()`. Never implement custom plain-text password storage.

### 2.4 Custom User Managers Need Explicit Validation

A custom manager centralizes user creation logic.

NexaMind's manager handles email normalization, password requirements, and superuser flag validation.

**Lesson:** Put reusable account-creation rules in the manager, and test both valid and invalid inputs.

---

## 3. Database Engineering

### 3.1 Database Connectivity and Database Privileges Are Different

An application may successfully connect to PostgreSQL while still lacking permission to perform a particular operation.

For example, Django's test runner needs permission to create a temporary test database.

**Lesson:** When a database operation fails, distinguish connection problems from authorization and privilege problems.

### 3.2 Database Roles Should Follow the Principle of Least Privilege

PostgreSQL roles should receive only the permissions required for their responsibilities.

Development and testing may require additional privileges that production does not need.

**Lesson:** Review database role permissions before deployment and avoid using superuser credentials for normal application operations.

### 3.3 Migrations Are Part of the Application's Database Contract

Django migrations describe how the database schema evolves alongside application models.

**Lesson:**

- Review generated migrations.
- Keep migrations under version control.
- Apply migrations deliberately.
- Test schema changes before integrating them into the main development branch.

---

## 4. Testing and Quality Assurance

### 4.1 Tests Should Validate Behavior, Not Just Implementation

A test should establish whether the application behaves correctly under specific conditions.

For the custom user manager, tests cover successful user creation, email normalization, password hashing, invalid input, and superuser validation.

**Lesson:** Design tests around observable behavior and important edge cases.

### 4.2 Infrastructure Failures Should Be Distinguished from Application Failures

A failing test suite does not always indicate a defect in application code.

The PostgreSQL test database permission issue demonstrated that infrastructure configuration can prevent tests from running.

**Lesson:** Read the complete error, identify the failing layer, investigate the root cause, and rerun the tests after fixing it.

### 4.3 Verification Should Follow Every Meaningful Change

A successful code edit is not proof that the application still works.

**Lesson:** Use relevant verification commands after changes, such as:

```bash
python manage.py check
python -m pip check
python manage.py test apps.accounts
```

Record the actual results rather than assuming success.

---

## 5. Security Engineering

### 5.1 The Backend Must Enforce Resource Ownership

Frontend restrictions are not security boundaries.

A user can manipulate requests independently of the React interface.

**Lesson:** Every protected conversation or message operation must verify ownership on the backend.

### 5.2 Sensitive Provider Credentials Belong on the Backend

NexaMind integrates with Google's Gemini API.

The provider API key must remain server-side and must never be exposed to the React application.

**Lesson:** The backend should control provider credentials, API communication, and the construction of model context.

### 5.3 Client Input Must Not Control Privileged Account Fields

Account creation endpoints must not blindly accept every field submitted by a client.

Fields such as `is_staff` and `is_superuser` must be controlled by trusted backend logic.

**Lesson:** Use explicit serializer fields and validate client input. Never allow ordinary registration requests to grant administrative privileges.

---

## 6. Engineering Workflow and Documentation

### 6.1 Inspect Before Changing

Understanding the current state of a file, configuration, or application is essential before making modifications.

**Lesson:** Inspect existing code, understand its responsibility, identify the required change, and then implement it.

### 6.2 Work in Small, Verifiable Steps

Large unverified changes make it difficult to identify the source of errors.

**Lesson:** Implement one meaningful unit of work, verify it, inspect the result, and then proceed.

### 6.3 Documentation Should Have Clear Responsibilities

Project documentation becomes difficult to maintain when multiple documents repeat the same information.

**Lesson:** Keep separate responsibilities:

- Engineering journal: chronological project history.
- Technical challenges: significant technical difficulties and their status.
- Problem-solving log: detailed debugging investigations.
- Lessons learned: reusable engineering knowledge.
- Future improvements: deferred work and opportunities.

### 6.4 Git Should Preserve Meaningful Engineering Milestones

Git history should communicate what changed and why.

**Lesson:** Review changes before staging, use meaningful commit messages, and commit verified milestones rather than unrelated unfinished work.

---

## 7. Continuous Improvement

These lessons should evolve as NexaMind develops.

Future entries should capture knowledge gained from:

- Django REST Framework and API design.
- JWT authentication and authorization.
- React frontend architecture.
- PostgreSQL data modeling and query optimization.
- Gemini API integration and context management.
- Automated testing and integration testing.
- Deployment, monitoring, and production security.

The goal is not simply to record mistakes, but to turn engineering experience into better technical judgment.
