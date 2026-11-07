# NexaMind — Development Setup Guide

## 1. Purpose

This document explains how to prepare a local development environment for NexaMind.

It covers:

- Required development tools.
- Repository setup.
- Python backend environment.
- React frontend environment.
- PostgreSQL configuration.
- Environment variables.
- Running the application locally.
- Basic troubleshooting.

The guide will evolve as the project moves from planning into implementation.

## 2. Technology Stack

NexaMind uses the following technologies.

| Layer              | Technology            | Responsibility                      |
| ------------------ | --------------------- | ----------------------------------- |
| Frontend           | React                 | User interface                      |
| Frontend tooling   | Vite                  | Development server and build        |
| Frontend language  | JavaScript            | Application logic                   |
| Styling            | Tailwind CSS          | UI styling                          |
| Routing            | React Router          | Client-side navigation              |
| HTTP client        | Axios                 | Backend communication               |
| Backend            | Django                | Application framework               |
| API                | Django REST Framework | REST API                            |
| Backend language   | Python                | Backend logic                       |
| Database           | PostgreSQL            | Persistent application data         |
| AI integration     | Google Gemini API     | AI-generated responses              |
| Authentication     | JWT                   | API authentication                  |
| Version control    | Git                   | Source control                      |
| Repository hosting | GitHub                | Remote repository and collaboration |

## 3. System Requirements

### 3.1 Operating system

Recommended development environment:

- Ubuntu Linux.
- Ubuntu through Windows Subsystem for Linux (WSL).
- macOS.
- Windows with an appropriate Linux or Python development environment.

The project should be developed and tested in a consistent environment.

### 3.2 Required tools

| Tool        | Purpose                       |
| ----------- | ----------------------------- |
| Python 3.12 | Backend development           |
| pip         | Python package installation   |
| Node.js 22  | Frontend development          |
| npm         | JavaScript package management |
| PostgreSQL  | Relational database           |
| Git         | Version control               |
| VS Code     | Code editor                   |
| Browser     | Frontend testing              |

Exact dependency versions should be pinned or constrained in project configuration files when implementation begins.

### 3.3 Optional tools

| Tool       | Purpose                     |
| ---------- | --------------------------- |
| Docker     | Containerized development   |
| Postman    | API testing                 |
| Insomnia   | API testing                 |
| pgAdmin    | PostgreSQL management       |
| DBeaver    | Database management         |
| Swagger UI | API documentation interface |

Docker is optional for the initial development workflow. We should first establish a working application before adding unnecessary infrastructure.

## 4. Repository Setup

Clone the NexaMind repository:

```bash
git clone git@github.com:tamirattezera/nexamind.git
```

Navigate into the project:

```bash
cd nexamind
```

Verify the repository:

```bash
git status
```

Expected result:

```text
On branch main
nothing to commit, working tree clean
```

If the GitHub repository has not yet been created, initialize the local repository and connect its remote when ready.

## 5. Backend Environment Setup

### 5.1 Navigate to the backend directory

```bash
cd backend
```

### 5.2 Create a Python virtual environment

```bash
python3.12 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Verify Python:

```bash
python --version
```

Expected major/minor version:

```text
Python 3.12.x
```

### 5.3 Upgrade pip

```bash
python -m pip install --upgrade pip
```

### 5.4 Install backend dependencies

Once the backend requirements files have been created, install development dependencies:

```bash
pip install -r requirements/development.txt
```

The requirements files will separate common dependencies, development tools, and production-specific dependencies.

Their exact contents will be established during backend implementation.

### 5.5 Verify Django

After installing Django:

```bash
python -m django --version
```

The command should return the installed Django version.

## 6. PostgreSQL Setup

NexaMind uses PostgreSQL as its primary relational database.

### 6.1 Install PostgreSQL

On Ubuntu, PostgreSQL can be installed through the package manager:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

Verify installation:

```bash
psql --version
```

### 6.2 Start PostgreSQL

On systems using systemd:

```bash
sudo service postgresql start
```

Check service status:

```bash
sudo service postgresql status
```

### 6.3 Create a development database

Open the PostgreSQL shell:

```bash
sudo -u postgres psql
```

Create a dedicated database:

```sql
CREATE DATABASE nexamind_dev;
```

Create a dedicated application user:

```sql
CREATE USER nexamind_user WITH PASSWORD 'replace_with_a_local_password';
```

Grant database privileges:

```sql
GRANT ALL PRIVILEGES ON DATABASE nexamind_dev TO nexamind_user;
```

Exit:

```sql
\q
```

Additional schema privileges or ownership configuration may be necessary depending on the PostgreSQL version and migration configuration. These will be verified when connecting Django.

### 6.4 Database separation

Use separate database configurations for different environments:

| Environment | Database                                                |
| ----------- | ------------------------------------------------------- |
| Development | `nexamind_dev`                                          |
| Testing     | Dedicated test database or Django-managed test database |
| Production  | Managed PostgreSQL database                             |

Never use production credentials in local development.

## 7. Frontend Environment Setup

### 7.1 Navigate to the frontend directory

From the repository root:

```bash
cd frontend
```

### 7.2 Verify Node.js

```bash
node --version
npm --version
```

The project targets Node.js 22.

### 7.3 Install frontend dependencies

After `package.json` is created:

```bash
npm install
```

For a clean installation from a committed lockfile:

```bash
npm ci
```

Use `npm ci` when reproducing an existing dependency installation from `package-lock.json`.

### 7.4 Start the development server

Once the Vite application is configured:

```bash
npm run dev
```

The development server will display its local URL, typically:

```text
http://localhost:5173
```

The actual port may differ if the default port is unavailable.

## 8. Environment Variables

NexaMind uses environment variables for configuration and secret management.

### 8.1 Backend environment

The backend environment file should be located at:

```text
backend/.env
```

Example:

```env
DEBUG=True
SECRET_KEY=replace_with_a_local_django_secret
ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_NAME=nexamind_dev
DATABASE_USER=nexamind_user
DATABASE_PASSWORD=replace_with_a_local_password
DATABASE_HOST=127.0.0.1
DATABASE_PORT=5432

GEMINI_API_KEY=replace_with_your_gemini_api_key
```

This is an initial configuration template. The actual variable names must match the backend settings implementation.

### 8.2 Frontend environment

The frontend environment file should be located at:

```text
frontend/.env.local
```

Example:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Important:

- Vite exposes variables prefixed with `VITE_` to browser code.
- Never put the Gemini API key in frontend environment variables.
- Never put database credentials or Django secret keys in frontend configuration.

### 8.3 Environment file protection

The following files must not be committed:

```text
backend/.env
frontend/.env.local
backend/.venv/
frontend/node_modules/
```

Commit sanitized examples instead:

```text
.env.example
backend/.env.example
frontend/.env.example
```

Environment examples must contain placeholders, never real credentials.

## 9. Running the Application Locally

After the frontend, backend, and database have been implemented, NexaMind will run using separate development processes.

### Terminal 1 — PostgreSQL

Start the database service:

```bash
sudo service postgresql start
```

### Terminal 2 — Django backend

```bash
cd nexamind/backend
source .venv/bin/activate
python manage.py runserver
```

Expected local backend address:

```text
http://localhost:8000
```

### Terminal 3 — React frontend

```bash
cd nexamind/frontend
npm run dev
```

Expected local frontend address:

```text
http://localhost:5173
```

These commands describe the intended development workflow. They will become executable after the relevant project configuration and application files exist.

## 10. Initial Health Verification

Once the backend health endpoint has been implemented, use:

```bash
curl http://localhost:8000/api/v1/health/
```

The endpoint should return a successful response.

The exact response schema will be defined during backend setup.

Database connectivity should also be tested independently.

Successful server startup alone does not prove that PostgreSQL, authentication, or Gemini integration is working.

## 11. Git Development Workflow

NexaMind uses Git for version control.

Before beginning work:

```bash
git status
git pull
```

After completing a verified change:

```bash
git add .
git commit -m "type: describe the change"
```

Suggested commit prefixes:

| Prefix     | Purpose                |
| ---------- | ---------------------- |
| `docs`     | Documentation          |
| `feat`     | New functionality      |
| `fix`      | Bug fixes              |
| `refactor` | Code restructuring     |
| `test`     | Tests                  |
| `chore`    | Maintenance            |
| `style`    | Formatting and styling |

Examples:

```bash
git commit -m "docs: add development setup guide"
git commit -m "feat: initialize Django backend"
git commit -m "test: add conversation API tests"
```

Commit after a meaningful, verified milestone rather than committing untested changes as completed work.

## 12. Troubleshooting

### Python virtual environment activation fails

Verify that the environment exists:

```bash
ls -la .venv
```

Recreate it if necessary:

```bash
python3.12 -m venv .venv
```

### Django command is unavailable

Verify that the virtual environment is active:

```bash
which python
```

Install the project dependencies after the requirements files exist.

### PostgreSQL connection fails

Check:

```bash
sudo service postgresql status
```

Verify:

- Database name.
- Database username.
- Password.
- Host.
- Port.
- Database permissions.

### Frontend cannot communicate with backend

Verify:

- Backend is running.
- Frontend API base URL is correct.
- Django CORS configuration allows the frontend origin.
- Requests use the correct API path.
- Authentication headers are included where required.

CORS configuration does not replace backend authorization.

### Gemini requests fail

Verify:

- Backend environment variables are loaded.
- The API key is configured securely.
- The selected model is available.
- The provider request and response handling are correct.
- Provider errors and timeouts are handled.

Never print the actual API key when debugging.

## 13. Development Environment Checklist

Before starting implementation, verify the following:

- [ ] Git repository is available.
- [ ] Python 3.12 is installed.
- [ ] Node.js 22 is installed.
- [ ] npm is available.
- [ ] PostgreSQL is installed and running.
- [ ] PostgreSQL development database exists.
- [ ] Python virtual environment can be activated.
- [ ] Backend dependencies can be installed.
- [ ] Frontend dependencies can be installed.
- [ ] Environment variable examples are documented.
- [ ] Secret files are excluded from Git.
- [ ] VS Code can open the repository.

## 14. Development Principles

NexaMind development should follow these principles:

1. Keep frontend and backend responsibilities separate.
2. Use environment-specific configuration.
3. Keep secrets outside source control.
4. Use PostgreSQL consistently across development and production.
5. Write tests alongside meaningful functionality.
6. Verify each milestone before committing.
7. Avoid unnecessary infrastructure before the application requires it.
8. Document important architectural decisions.
9. Prefer reproducible setup instructions.
10. Keep documentation aligned with actual implementation.

## 15. Related Documents

- [Project README](../../README.md)
- [Architecture Overview](../02-system-design/architecture-overview.md)
- [Backend Architecture](../02-system-design/backend-architecture.md)
- [Frontend Architecture](../02-system-design/frontend-architecture.md)
- [Database Design](../02-system-design/database-design.md)
- [Security Architecture](../02-system-design/security-architecture.md)
- [API Overview](../03-api/api-overview.md)
- [API Endpoint Reference](../03-api/endpoint-reference.md)

---

**Document status:** Initial development setup guide
**Implementation status:** Not started
**Target Python version:** 3.12
**Target Node.js version:** 22
**Database:** PostgreSQL
