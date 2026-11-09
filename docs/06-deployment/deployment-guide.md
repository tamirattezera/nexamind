# Deployment Guide

**Project:** NexaMind
**Document:** Deployment Guide
**Status:** Draft
**Version:** 1.0
**Last Updated:** November 2026

---

## 1. Purpose

This document defines the deployment strategy for NexaMind.

The objective is to deploy the application in a production-like environment where users can:

- Access the React frontend through a public URL.
- Authenticate securely.
- Create and manage conversations.
- Send messages to the Django REST API.
- Receive AI-generated responses through Gemini.
- Retrieve previously stored conversations.
- Access their data securely across sessions.

Deployment must preserve the application's architecture and security boundaries.

## 2. Deployment Architecture

NexaMind uses a separated frontend and backend deployment model.

### 2.1 High-Level Architecture

```text
                 USERS
                   |
                   v
             HTTPS CONNECTION
                   |
          +--------+--------+
          |                 |
          v                 v
     FRONTEND           BACKEND API
     React + Vite       Django + DRF
     Vercel             Render (candidate)
                            |
               +------------+------------+
               |            |            |
               v            v            v
           PostgreSQL    Gemini API   Application
           Neon          Google       Monitoring
```

This architecture separates the user interface, application logic, persistent data, and AI provider integration.

### 2.2 Deployment Components

| Component      | Technology   | Candidate platform |
| -------------- | ------------ | ------------------ |
| Frontend       | React + Vite | Vercel             |
| Backend        | Django + DRF | Render             |
| Database       | PostgreSQL   | Neon               |
| AI provider    | Gemini API   | Google             |
| Source control | Git          | GitHub             |

**Important:** These hosting platforms are initial candidates, not irreversible architecture decisions. Their current availability, pricing, resource limits, regional support, and production suitability must be verified before deployment.

## 3. Deployment Environments

NexaMind should distinguish between development and production environments.

### 3.1 Development

Purpose:

- Build features.
- Run automated tests.
- Debug application behavior.
- Test database changes.
- Integrate with Gemini using development credentials.

Characteristics:

- Local React development server.
- Local Django development server.
- Local or development PostgreSQL database.
- Development-only environment variables.
- Debugging enabled.
- Test data allowed.

### 3.2 Production

Purpose:

- Serve real users.
- Store real conversation history.
- Process authenticated AI requests.
- Operate reliably and securely.

Characteristics:

- Public HTTPS frontend and backend.
- Production PostgreSQL database.
- Debugging disabled.
- Secure secrets configuration.
- Restricted database access.
- Explicit allowed frontend origins.
- Production logging and monitoring.
- Database backup strategy.

Development and production credentials and databases must remain separate.

## 4. Frontend Deployment

### 4.1 Technology

The frontend is built using:

- React.
- Vite.
- JavaScript.
- Axios.
- React Router, if required by the final implementation.

### 4.2 Build Process

The frontend production build should be verified locally before deployment.

Expected command:

```bash
cd frontend
npm ci
npm run build
```

The build must complete without errors.

The generated production assets are normally placed in:

```text
frontend/dist/
```

The deployment platform serves these static assets.

### 4.3 Environment Configuration

The frontend needs the public backend API base URL.

Example:

```env
VITE_API_BASE_URL=https://api.example.com/api/v1
```

This is a placeholder, not a real deployment URL.

Vite exposes variables prefixed with `VITE_` to browser-side code. Therefore:

**Never place the Gemini API key, database password, JWT signing secret, or other private credentials in frontend environment variables.**

### 4.4 Frontend Deployment Verification

Verify:

- [ ] Production build succeeds.
- [ ] Public frontend URL loads.
- [ ] Browser console contains no critical errors.
- [ ] API requests target the production backend.
- [ ] Authentication works.
- [ ] Page navigation works after refresh.
- [ ] Responsive layouts work on mobile and desktop.
- [ ] No private credentials appear in bundled assets.

## 5. Backend Deployment

### 5.1 Technology

The backend uses:

- Python.
- Django.
- Django REST Framework.
- PostgreSQL.
- Gemini integration through the official Google SDK.
- JWT authentication.

### 5.2 Production Configuration

Production Django settings must be explicitly configured.

Important settings include:

| Setting              | Production requirement         |
| -------------------- | ------------------------------ |
| `DEBUG`              | `False`                        |
| `SECRET_KEY`         | Secure environment variable    |
| `ALLOWED_HOSTS`      | Explicit production hostnames  |
| `DATABASE_URL`       | Production database connection |
| CORS origins         | Explicit frontend origin       |
| CSRF trusted origins | Configured when required       |
| Gemini API key       | Backend secret                 |
| HTTPS                | Enabled                        |
| Logging              | Production configuration       |

Do not copy development settings blindly into production.

### 5.3 Dependencies

Install production dependencies using the project's established dependency-management approach.

Example:

```bash
pip install -r requirements/production.txt
```

The exact dependency installation command must match the final backend structure.

### 5.4 Static Files

Django static-file handling must be configured for production.

A production static-file strategy, such as WhiteNoise or platform-supported static hosting, should be selected and tested during implementation.

### 5.5 Database Migrations

Apply migrations as part of a controlled deployment process.

```bash
python manage.py migrate
```

Do not assume that deploying new backend code automatically updates the database schema.

Review migration files and verify backup and rollback options before applying potentially destructive changes.

### 5.6 Backend Health Check

The backend should expose a health endpoint.

Example:

```http
GET /api/v1/health/
```

Expected response:

```json
{
  "status": "ok"
}
```

The endpoint should report application health without exposing secrets, database credentials, or internal infrastructure details.

A basic health response does not necessarily prove that Gemini generation is operational. External provider availability should be monitored separately.

## 6. PostgreSQL Deployment

### 6.1 Database Requirements

The production database must support:

- Persistent storage.
- Secure connections.
- Django ORM compatibility.
- Database migrations.
- Backup and recovery.
- Appropriate connection limits.

Neon PostgreSQL is the initial candidate.

### 6.2 Connection Configuration

The backend should receive its database connection information through a protected environment variable.

Example:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
```

This is an illustrative format. Use the connection string supplied by the selected database provider.

Never commit a real database connection string.

### 6.3 Database Security

- Use a dedicated application database user.
- Grant only necessary permissions.
- Require encrypted connections when supported and appropriate.
- Restrict database access according to provider capabilities.
- Keep production data separate from development data.
- Avoid exposing the database publicly without a justified requirement.

### 6.4 Backup and Recovery

Before production use, define:

- Backup frequency.
- Backup retention.
- Recovery procedure.
- Recovery objectives.
- Responsibility for restoring data.

A backup strategy is incomplete until restoration has been tested.

## 7. Gemini API Deployment Configuration

The Gemini API key is configured on the backend deployment platform.

Example:

```env
GEMINI_API_KEY=your_private_api_key
```

Additional model configuration may include:

```env
GEMINI_MODEL=verified_model_identifier
```

The model identifier must match the model selected and verified during the Gemini integration phase.

Deployment requirements:

- Keep the API key out of Git.
- Configure it using backend secrets.
- Never return it in API responses.
- Never expose it in frontend bundles.
- Monitor provider errors and usage.
- Configure timeouts and resource limits.
- Verify the production key and model configuration before enabling generation.

Do not assume a development API key will remain appropriate for production use.

## 8. CORS and Cross-Origin Configuration

Because the frontend and backend may use different domains, cross-origin requests must be configured correctly.

The backend should allow only the intended frontend origins.

Example conceptual configuration:

```text
Development:
http://localhost:5173

Production:
https://your-frontend-domain.example
```

These are examples, not actual NexaMind deployment domains.

Avoid unrestricted wildcard CORS policies for authenticated production APIs.

CORS is a browser access-control mechanism; it is not a substitute for authentication or authorization.

## 9. Production Environment Variables

The following table describes expected configuration categories.

| Variable               | Component | Secret? |
| ---------------------- | --------- | ------- |
| `DEBUG`                | Backend   | No      |
| `SECRET_KEY`           | Backend   | Yes     |
| `DATABASE_URL`         | Backend   | Yes     |
| `GEMINI_API_KEY`       | Backend   | Yes     |
| `GEMINI_MODEL`         | Backend   | No      |
| `ALLOWED_HOSTS`        | Backend   | No      |
| `CORS_ALLOWED_ORIGINS` | Backend   | No      |
| `VITE_API_BASE_URL`    | Frontend  | No      |

The final variable names must match the actual implementation.

Production secrets must be configured through the hosting platform's protected environment-variable or secret-management interface.

## 10. Deployment Workflow

NexaMind should use a controlled deployment process.

### Step 1: Verify Source Code

```bash
git status
git log -1 --oneline
```

Confirm the intended changes are committed and the working tree is in the expected state.

### Step 2: Run Backend Tests

Run the complete backend test suite using the command established during implementation.

### Step 3: Run Frontend Tests

Run the frontend test suite.

### Step 4: Build Frontend

```bash
cd frontend
npm ci
npm run build
```

### Step 5: Check Production Settings

Review:

- Django production settings.
- Environment variables.
- Database configuration.
- CORS and allowed hosts.
- Secret handling.
- Static files.
- Logging.

### Step 6: Deploy Database and Backend

- Provision the production PostgreSQL database.
- Configure the backend environment.
- Deploy the backend.
- Apply migrations.
- Verify the health endpoint.

### Step 7: Deploy Frontend

- Configure the production API base URL.
- Deploy the frontend.
- Verify the public frontend URL.

### Step 8: End-to-End Verification

Test the complete user journey:

1. Open NexaMind.
2. Register an account.
3. Log in.
4. Create a conversation.
5. Submit a message.
6. Receive a Gemini response.
7. Refresh the page.
8. Verify conversation persistence.
9. Create another conversation.
10. Rename and delete a conversation.
11. Log out and log back in.
12. Verify that another user's data is inaccessible.

### Step 9: Monitor

Review application logs, API errors, provider failures, and database health.

## 11. Deployment Rollback Strategy

Deployment changes may introduce unexpected failures.

A rollback strategy should consider:

- Reverting to a previously working application version.
- Restoring compatible environment configuration.
- Reverting frontend deployments.
- Reviewing database migration compatibility.
- Restoring database backups when necessary.

Database rollback requires special care. Reverting application code does not automatically reverse database changes safely.

Prefer backward-compatible migrations where practical.

## 12. Production Readiness Checklist

### Frontend

- [ ] Production build succeeds.
- [ ] API URL points to production.
- [ ] Frontend contains no private credentials.
- [ ] Client-side routing works after refresh.
- [ ] Responsive interface verified.

### Backend

- [ ] `DEBUG=False`.
- [ ] Production secret configured.
- [ ] Allowed hosts configured.
- [ ] CORS restricted.
- [ ] Authentication and authorization tested.
- [ ] Health endpoint verified.
- [ ] Provider errors handled safely.
- [ ] Static files configured.
- [ ] Logging configured.

### Database

- [ ] Production PostgreSQL provisioned.
- [ ] Connection secured.
- [ ] Migrations applied.
- [ ] Data persistence verified.
- [ ] Backup and restoration strategy defined.

### AI Integration

- [ ] Gemini API key configured on backend.
- [ ] Model identifier verified.
- [ ] Test generation succeeds.
- [ ] Usage and error handling verified.
- [ ] API key not exposed.

### Security

- [ ] HTTPS enabled.
- [ ] Secrets excluded from Git.
- [ ] Cross-user access tests pass.
- [ ] Rate limiting configured.
- [ ] Sensitive logging reviewed.

### Operations

- [ ] Deployment process documented.
- [ ] Application logs accessible.
- [ ] Failure monitoring available.
- [ ] Rollback procedure documented.
- [ ] Public URLs verified.

## 13. Deployment Success Criteria

Deployment is considered successful only when:

1. The frontend is publicly accessible.
2. The backend API responds correctly.
3. The production database persists application data.
4. Authentication works.
5. Users can access only their own conversations.
6. Gemini generation works through the backend.
7. Conversation history survives page refreshes and new sessions.
8. Critical security checks pass.
9. The application handles expected failures safely.
10. The deployed application has been tested through its public URLs.

A successful build or hosting-platform deployment message alone does not prove that NexaMind is working correctly.

## 14. Future Deployment Improvements

Potential improvements after the MVP:

- Automated CI/CD workflows.
- Docker-based deployment.
- Structured centralized logging.
- Error tracking.
- Performance monitoring.
- Database migration automation.
- Automated backup verification.
- Staging environment.
- Infrastructure as code.
- More advanced observability.

These should be introduced when the application and operational requirements justify them.

---

## 15. Final Principle

Deployment is not simply uploading frontend and backend code.

**A successful NexaMind deployment means the entire system works securely and reliably in its production environment: frontend, API, authentication, database, AI provider, and operational monitoring.**
