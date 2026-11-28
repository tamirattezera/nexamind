# Environment Configuration

**Project:** NexaMind
**Document:** Environment Configuration
**Status:** Draft
**Version:** 1.0
**Last Updated:** November 2026

---

## 1. Purpose

This document defines how NexaMind manages environment-specific configuration and sensitive credentials.

The objectives are to:

- Separate development, testing, and production configurations.
- Protect API keys, database credentials, and authentication secrets.
- Ensure consistent configuration across frontend and backend.
- Prevent accidental exposure of sensitive information.
- Make application configuration predictable and maintainable.

## 2. Environment Strategy

NexaMind uses three primary environments.

| Environment | Purpose                                 | Data                |
| ----------- | --------------------------------------- | ------------------- |
| Development | Local feature development and debugging | Development data    |
| Testing     | Automated and integration testing       | Temporary test data |
| Production  | Application serving real users          | Real user data      |

Each environment must have its own configuration and credentials.

### 2.1 Development Environment

Used during local development.

Characteristics:

- Local frontend and backend servers.
- Development PostgreSQL database.
- Development Gemini credentials.
- Debugging enabled.
- Development logging.
- Test accounts and sample data.

### 2.2 Testing Environment

Used for automated and integration testing.

Characteristics:

- Isolated test database.
- Controlled environment variables.
- Mocked Gemini responses for ordinary automated tests.
- No production credentials.
- Predictable test behavior.
- Temporary test data.

Tests that verify actual provider connectivity should be explicitly separated from ordinary automated tests because they depend on external services and may consume API quota.

### 2.3 Production Environment

Used by real users.

Characteristics:

- Secure production credentials.
- Production database.
- Debugging disabled.
- Restricted host and origin configuration.
- Production logging.
- Secure external API communication.
- Operational monitoring.

Production secrets must never be copied into local development or testing environments unnecessarily.

## 3. Configuration Architecture

NexaMind separates configuration from application source code.

```text
                  ENVIRONMENT
                       |
                       v
              CONFIGURATION INPUTS
                       |
          +------------+------------+
          |            |            |
          v            v            v
      Development    Testing    Production
          |            |            |
          v            v            v
       Settings     Settings     Settings
          |            |            |
          +------------+------------+
                       |
                       v
                 APPLICATION
                       |
          +------------+------------+
          |            |            |
          v            v            v
       Database      Gemini       Security
```

Application behavior should depend on explicitly defined configuration, not assumptions about the machine or deployment platform.

## 4. Backend Configuration

The Django backend owns the sensitive application configuration.

The current backend configuration is implemented in
`backend/config/settings.py`.

| Category | Implemented configuration |
| -------- | ------------------------- |
| Django security | `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` |
| Host configuration | `DJANGO_ALLOWED_HOSTS` |
| Cross-origin access | `DJANGO_CORS_ALLOWED_ORIGINS` |
| Database | `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` |
| Database connection timeout | `DB_CONNECT_TIMEOUT` |
| Readiness SQL timeout | `HEALTH_CHECK_DB_STATEMENT_TIMEOUT_MS` |
| Shared production cache | `REDIS_URL` |
| Redis connection and socket timeouts | `REDIS_SOCKET_CONNECT_TIMEOUT`, `REDIS_SOCKET_TIMEOUT` |
| AI provider | `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_THINKING_LEVEL`, `GEMINI_MAX_OUTPUT_TOKENS`, `GEMINI_TIMEOUT_MS` |
| Conversation policy | `CHAT_CONTEXT_MAX_INPUT_TOKENS`, `CHAT_MAX_MESSAGE_LENGTH` |
| Generation rate limiting | `CHAT_GENERATION_RATE_LIMIT`, `CHAT_GENERATION_RATE_WINDOW_SECONDS` |
| Deployment security | `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SESSION_COOKIE_SECURE`, `DJANGO_CSRF_COOKIE_SECURE`, `DJANGO_SECURE_HSTS_SECONDS` |

This inventory describes the current implementation, not proposed settings.

### 4.1 Django Settings Structure

The current project uses a single Django settings module:

```text
backend/
└── config/
    └── settings.py
```

The settings module loads environment variables from the
repository-root `.env` file using `django-environ`.

Cache selection depends on `DJANGO_DEBUG`:

- `True`: process-local `LocMemCache` for development and tests.
- `False`: shared Redis cache configured by `REDIS_URL`.
- Production cache checks verify Redis access. Production must not
  silently fall back to process-local memory.

The project captures the original deployment mode in `IS_PRODUCTION`
because Django's test runner can change `DEBUG` during test execution.

### 4.2 Configuration Validation

Required configuration must be validated during application startup.

Examples:

- Missing production `DJANGO_SECRET_KEY` must prevent startup.
- Missing production database configuration must be reported clearly.
- Missing Gemini credentials must produce an appropriate configuration error when AI functionality is initialized or requested.
- Invalid production host configuration must not silently fall back to permissive settings.

Do not use real production secrets as default fallback values.

## 5. Frontend Configuration

The React frontend requires public configuration, primarily the backend API URL.

Example:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Production example:

```env
VITE_API_BASE_URL=https://api.example.com/api/v1
```

These are illustrative values.

Vite environment variables prefixed with `VITE_` are exposed to browser-side application code.

Therefore:

**Frontend environment variables must contain public configuration only.**

Never place the following in frontend configuration:

- Gemini API key.
- Django secret key.
- Database credentials.
- Private JWT signing secrets.
- Internal service credentials.

The frontend must not be trusted to protect secrets.

## 6. Environment Variable Inventory

The following inventory defines the expected configuration categories.

### 6.1 Backend Variables

| Variable | Required | Sensitive | Purpose |
| -------- | -------- | --------- | ------- |
| `DJANGO_SECRET_KEY` | Yes | Yes | Django cryptographic signing |
| `DJANGO_DEBUG` | Has a default; set explicitly | No | Development or production mode |
| `DJANGO_ALLOWED_HOSTS` | Configure for deployment | No | Accepted hostnames |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Configure when frontend origin is known | No | Comma-separated allowed browser origins |
| `DB_NAME` | Yes | No | PostgreSQL database name |
| `DB_USER` | Yes | Depends on deployment | PostgreSQL username |
| `DB_PASSWORD` | Yes | Yes | PostgreSQL password |
| `DB_HOST` | Yes | No | PostgreSQL hostname |
| `DB_PORT` | Yes | No | PostgreSQL port |
| `DB_CONNECT_TIMEOUT` | Has a default | No | PostgreSQL connection-establishment timeout in seconds; affects application database connections |
| `HEALTH_CHECK_DB_STATEMENT_TIMEOUT_MS` | Has a default | No | Maximum duration of each readiness-check SQL statement in milliseconds; must be greater than zero |
| `REDIS_URL` | Production only | Yes if credentials are embedded | Shared Redis cache connection |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | Has a default in production | No | Redis connection-establishment timeout in seconds |
| `REDIS_SOCKET_TIMEOUT` | Has a default in production | No | Redis socket-operation timeout in seconds |
| `GEMINI_API_KEY` | Required for AI generation | Yes | Gemini authentication |
| `GEMINI_MODEL` | Has a default | No | Default Gemini model |
| `GEMINI_THINKING_LEVEL` | Has a default | No | Default thinking level |
| `GEMINI_MAX_OUTPUT_TOKENS` | Has a default | No | Default output-token limit |
| `GEMINI_TIMEOUT_MS` | Has a default | No | Provider request timeout |
| `CHAT_CONTEXT_MAX_INPUT_TOKENS` | Has a default | No | Context input-token limit |
| `CHAT_MAX_MESSAGE_LENGTH` | Has a default | No | Maximum user-message length |
| `CHAT_GENERATION_RATE_LIMIT` | Has a default | No | Generation submissions per window |
| `CHAT_GENERATION_RATE_WINDOW_SECONDS` | Has a default | No | Generation rate-limit window |
| `DJANGO_SECURE_SSL_REDIRECT` | Has a default | No | HTTPS redirect behavior |
| `DJANGO_SESSION_COOKIE_SECURE` | Has a default | No | Secure session-cookie setting |
| `DJANGO_CSRF_COOKIE_SECURE` | Has a default | No | Secure CSRF-cookie setting |
| `DJANGO_SECURE_HSTS_SECONDS` | Has a default | No | HSTS duration |

These names and defaults reflect the current `backend/config/settings.py`.

### 6.2 Frontend Variables

| Variable            | Required | Sensitive | Purpose              |
| ------------------- | -------- | --------- | -------------------- |
| `VITE_API_BASE_URL` | Yes      | No        | Backend API base URL |

Avoid introducing frontend environment variables without a real requirement.

## 7. Environment Files

### 7.1 Development Files

The current backend environment files are located at the repository root:

```text
nexamind/
├── .env
├── .env.example
└── backend/
    └── config/
        └── settings.py
```

Django loads the repository-root `.env` through `django-environ`.
The real `.env` file must remain excluded from version control.

Example frontend development configuration:

```text
frontend/
├── .env.local
├── .env.example
└── src/
```

The current backend explicitly loads the repository-root `.env` file
with `django-environ`. Production deployments should supply configuration
through the hosting platform's protected environment-variable mechanism.

### 7.2 Example Environment Files

The repository should contain example files that document required variable names and safe placeholder values.

Example backend `.env.example` (repository root):

```env
DJANGO_SECRET_KEY=replace-with-a-secure-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:5173
DJANGO_SECURE_SSL_REDIRECT=False
DJANGO_SESSION_COOKIE_SECURE=False
DJANGO_CSRF_COOKIE_SECURE=False
DJANGO_SECURE_HSTS_SECONDS=0
DB_NAME=nexamind_db
DB_USER=nexamind_user
DB_PASSWORD=replace-with-your-database-password
DB_HOST=127.0.0.1
DB_PORT=5432
REDIS_URL=redis://127.0.0.1:6379/1
GEMINI_API_KEY=replace-with-your-api-key
GEMINI_MODEL=gemini-3.8-flash
GEMINI_THINKING_LEVEL=LOW
GEMINI_MAX_OUTPUT_TOKENS=8192
GEMINI_TIMEOUT_MS=60000
CHAT_CONTEXT_MAX_INPUT_TOKENS=32768
CHAT_MAX_MESSAGE_LENGTH=10000
CHAT_GENERATION_RATE_LIMIT=10
CHAT_GENERATION_RATE_WINDOW_SECONDS=60
```

When `DJANGO_DEBUG=False`, the backend requires a shared Redis cache.
Configure `REDIS_URL` with the production Redis connection supplied by
the hosting platform. Do not use the local development Redis URL in production.

Example frontend `.env.example`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

These examples must never contain real credentials.

## 8. Secret Management

### 8.1 What Is a Secret?

A secret is sensitive information that grants access to a protected resource or capability.

Examples:

- `DJANGO_SECRET_KEY` environment variable (Django's secret key).
- Gemini API key.
- PostgreSQL password.
- JWT signing secret, if separately configured.
- Third-party service credentials.

### 8.2 Secret Storage

Development:

- Store credentials in local environment files excluded from Git.
- Restrict access to local secret files.
- Avoid sharing credentials in screenshots or public documentation.

Production:

- Use the deployment platform's protected environment-variable or secrets interface.
- Restrict secret access to authorized operators and services.
- Rotate compromised credentials.
- Never embed credentials in frontend assets.

### 8.3 Git Protection

The root `.gitignore` should exclude sensitive files.

Example:

```gitignore
# Environment files
.env
.env.*
!.env.example

# Python
__pycache__/
*.py[cod]
.venv/

# Frontend
node_modules/
dist/

# Local development
*.log
```

Review the final ignore rules carefully. They must not accidentally exclude required example files or source configuration.

A `.gitignore` rule does not remove a secret that has already been committed.

If a real credential is committed:

1. Revoke or rotate the credential immediately.
2. Remove the secret from the active codebase.
3. Review Git history and repository exposure.
4. Clean history when appropriate.
5. Investigate possible unauthorized use.

## 9. Configuration Validation and Type Safety

Environment variables are commonly supplied as strings.

The backend must parse and validate values before using them.

For example:

```text
DJANGO_DEBUG="False"
```

must be interpreted as the Boolean value `False`, not as a non-empty string that evaluates to `True`.

Configuration parsing should validate:

- Boolean values.
- Integer limits.
- URLs.
- Hostnames.
- Required values.
- Allowed choices.
- Secret presence.

Invalid configuration should produce a clear startup error rather than unpredictable application behavior.

## 10. Configuration Precedence

NexaMind should define an explicit configuration precedence policy.

A recommended approach:

1. Environment variables supplied by the runtime.
2. Environment-specific configuration defaults where appropriate.
3. Shared non-sensitive application defaults.

Sensitive configuration must never silently fall back to hardcoded credentials.

Production configuration must not inherit unsafe development defaults.

## 11. Database Configuration

Each environment must use an appropriate database.

| Environment | Database                      |
| ----------- | ----------------------------- |
| Development | Local development PostgreSQL  |
| Testing     | Isolated test database        |
| Production  | Managed production PostgreSQL |

Important requirements:

- Never point automated tests at the production database.
- Do not reuse production credentials locally.
- Use appropriate connection settings.
- Protect database URLs.
- Keep migration behavior consistent across environments.

## 12. Gemini Configuration

Gemini configuration belongs to the backend.

Expected values:

- API key.
- Verified model identifier.
- Request timeout.
- Generation limits.
- Optional generation parameters.

Only the API key is a secret.

Model identifiers and generation parameters must be verified against current official provider documentation during implementation.

The backend should be able to change its selected model without requiring private credentials or model-specific configuration to be exposed to the frontend.

## 13. Configuration Troubleshooting

| Problem                         | Possible cause                      | Investigation                      |
| ------------------------------- | ----------------------------------- | ---------------------------------- |
| Backend cannot start            | Missing required setting            | Inspect environment configuration  |
| Database connection fails       | Invalid URL or unavailable database | Verify database connectivity       |
| Gemini request fails            | Missing or invalid API key          | Check backend secret configuration |
| Frontend cannot reach API       | Incorrect API URL                   | Verify `VITE_API_BASE_URL`         |
| Browser blocks requests         | Incorrect CORS configuration        | Inspect allowed origins            |
| Debug mode unexpectedly enabled | Incorrect Boolean parsing           | Review configuration parser        |
| Production host rejected        | Missing allowed hostname            | Review `DJANGO_ALLOWED_HOSTS`             |

Never solve configuration problems by exposing secrets in logs or error responses.

## 14. Configuration Security Checklist

### General

- [ ] Development, testing, and production configurations are separated.
- [ ] Configuration names are documented.
- [ ] Required settings are validated.
- [ ] Boolean and numeric values are parsed correctly.
- [ ] Unsafe defaults are not used in production.

### Backend

- [ ] Django secret is externalized.
- [ ] Database URL is protected.
- [ ] Gemini API key is protected.
- [ ] Production debug mode is disabled.
- [ ] Allowed hosts are explicit.
- [ ] CORS origins are restricted.

### Frontend

- [ ] API base URL is configured.
- [ ] Only public values use the `VITE_` prefix.
- [ ] No private credentials are bundled.
- [ ] Production API URL is verified.

### Git and Deployment

- [ ] Real environment files are excluded from Git.
- [ ] Example environment files are committed.
- [ ] No real secrets exist in the repository history.
- [ ] Deployment secrets are configured securely.
- [ ] Secret rotation procedures are documented.

## 15. Final Principle

Configuration determines how an application behaves in each environment.

**NexaMind must keep application code portable, environment-specific behavior explicit, and sensitive credentials outside the source code.**
