# Engineering Journal

This journal maintains a chronological record of NexaMind development, engineering activities, technical decisions, project interruptions, and resumptions.

Its purpose is to preserve project history, maintain continuity, and capture the reasoning behind important engineering activities.

---

## 2026-11-10 — Development Environment Migration

### 1. Context

NexaMind development was temporarily paused to focus on improving and migrating the development environment.

The previous development environment used Ubuntu 20.04 through Windows Subsystem for Linux (WSL2).

Ubuntu 26.04 was selected as the new primary development environment to establish a modern, maintainable, and consistent foundation for future engineering work.

### 2. Objectives

- Establish Ubuntu 26.04 as the primary WSL2 distribution.
- Preserve existing source code and Git repositories.
- Migrate development tools and language runtimes.
- Preserve existing database environments and data.
- Restore VS Code and GitHub integration.
- Improve terminal configuration and developer productivity.
- Prepare a reliable environment for continuing NexaMind development.

### 3. Activities Completed

#### Operating System and Environment

- Installed and configured Ubuntu 26.04.1 LTS under WSL2.
- Configured Ubuntu 26.04 as the default WSL distribution.
- Configured Windows Terminal to open Ubuntu 26.04.
- Migrated existing home-directory files and development projects.
- Preserved the original Ubuntu 20.04 environment as a fallback.

#### Development Tools

- Installed and configured Git.
- Configured Git identity and verified GitHub SSH authentication.
- Installed pyenv and configured Python 3.12.12.
- Installed NVM and configured Node.js 22.22.3.
- Configured npm and essential command-line utilities.
- Restored VS Code WSL integration and development extensions.

#### Database Environment

- Restored Docker and Docker Compose functionality.
- Verified the PostgreSQL 17 container.
- Migrated and verified seven MySQL application databases.
- Preserved database backup files and existing PostgreSQL data.

#### Terminal Workflow

- Created Bash navigation and development aliases.
- Improved Bash history configuration.
- Configured command-history synchronization across terminal sessions.
- Created a backup of the original `.bashrc` before modifying it.

### 4. Verification Results

The following development runtimes were verified in Ubuntu 26.04:

| Component | Verified Version |
| --------- | ---------------- |
| Ubuntu    | 26.04.1 LTS      |
| Python    | 3.12.12          |
| pyenv     | 2.8.14           |
| Node.js   | 22.22.3          |
| npm       | 10.9.8           |
| NVM       | 0.40.3           |
| Git       | 2.53.0           |

Additional verification:

- VS Code successfully opened in the Ubuntu 26.04 WSL environment.
- GitHub SSH authentication succeeded.
- Docker was operational.
- PostgreSQL container reported healthy.
- MySQL application database access was verified.

### 5. NexaMind Repository Preservation

The NexaMind repository was preserved at:

`/home/zbooktamirat963/nexamind`

The repository contains:

- Existing README and project documentation.
- Django backend foundation.
- Accounts application.
- Python virtual environment.
- Architecture diagrams.
- Existing Git history.

The Git working tree was inspected after migration.

Current branch: `main`

Untracked items identified:

- `backend/`
- `docs/02-system-design/diagrams/high-level-architecture.png`
- `docs/02-system-design/diagrams/system_context_Diagram.png`

These items require review before staging and committing.

No destructive Git cleanup or automatic commit was performed.

### 6. Challenges and Observations

- Multiple Ubuntu distributions caused confusion when opening terminal profiles.
- A WSL service timeout occurred during migration troubleshooting.
- pyenv initially selected the system Python instead of Python 3.12.12.
- Runtime and database configurations required verification after migration.

The environment was progressively inspected and corrected without deleting the original Ubuntu distribution or existing project data.

### 7. Lessons Learned

- Always verify the active WSL distribution before running development commands.
- Preserve the original environment until migration verification is complete.
- Verify backups before relying on them.
- Check Git status before and after major environment changes.
- Configure language runtimes deliberately.
- Treat development environment maintenance as part of software engineering.

### 8. Status at the End of This Entry

The Ubuntu 26.04 development environment is operational, and the NexaMind repository is accessible.

However, the NexaMind backend and virtual environment still require post-migration verification.

The migration is therefore considered complete at the environment level, while project-level verification remains in progress.

### 9. Resumption Point

Resume NexaMind development from the existing repository state.

Next actions:

1. Inspect backend dependencies.
2. Verify the existing Python virtual environment.
3. Verify Django configuration and installed applications.
4. Review database configuration and PostgreSQL integration.
5. Inspect untracked files and architecture diagrams.
6. Continue from the last verified project development milestone.

Do not recreate the project or discard existing implementation work.

**Entry date:** 2026-11-10
**Activity:** Development environment migration
**Project:** NexaMind
**Status:** Environment operational; project verification pending

---

## 2026-11-11 — PostgreSQL Integration and Authentication Foundation

### 1. Context

Following the development environment migration, NexaMind backend development resumed.

The first priority was to verify the existing Django foundation, establish a reliable PostgreSQL connection, configure environment-based application settings, and implement the project's custom email-based user model.

This work establishes the initial backend foundation for NexaMind's multi-user authentication system.

### 2. Objectives

- Verify the Python environment and backend dependencies.
- Establish a native PostgreSQL development database.
- Configure secure environment-based Django settings.
- Connect Django to PostgreSQL.
- Implement a custom email-based user model.
- Generate and apply the initial database migrations.
- Implement automated tests for account management.
- Verify that the backend foundation works correctly.
- Improve Git hygiene and project learning documentation.

### 3. Development Environment Verification

The existing backend environment was inspected rather than recreated.

The original virtual environment had an OpenSSL-related compatibility problem. A separate working environment, `.venv-openssl3`, was established using the correctly configured Python installation.

Verified components:

| Component      | Verified Version |
| -------------- | ---------------- |
| Python         | 3.12.12          |
| Django         | 6.1.3            |
| psycopg        | 3.3.8            |
| django-environ | 0.14.0           |
| OpenSSL        | 3.5.5            |

Additional activities:

- Verified the active Python interpreter.
- Verified the installed backend dependencies.
- Confirmed dependency consistency using `python -m pip check`.
- Selected the correct Python interpreter in VS Code.
- Investigated and corrected the pyenv interpreter selection issue.

The `.venv-openssl3` environment became the working backend environment.

### 4. PostgreSQL Integration

#### PostgreSQL Installation and Configuration

PostgreSQL 18.6 was installed and configured natively in Ubuntu 26.04.

The PostgreSQL cluster was inspected and verified as online.

Cluster details:

| Property           | Value                         |
| ------------------ | ----------------------------- |
| PostgreSQL version | 18.6                          |
| Cluster            | 18/main                       |
| Port               | 5432                          |
| Status             | Online                        |
| Data directory     | `/var/lib/postgresql/18/main` |

#### Database and Role Creation

A dedicated PostgreSQL role and database were created for NexaMind.

| Resource       | Name            |
| -------------- | --------------- |
| Database       | `nexamind_db`   |
| Database role  | `nexamind_user` |
| Database owner | `nexamind_user` |

The database connection was tested through PostgreSQL's command-line client.

The following properties were verified:

- Current database: `nexamind_db`
- Current user: `nexamind_user`
- Server port: `5432`

#### Django Database Connection

The Django backend was configured to use PostgreSQL instead of the default SQLite database.

The connection was tested through Django itself.

Verification confirmed:

- Django database engine: `django.db.backends.postgresql`
- Connected database: `nexamind_db`
- Connection status: Successful

The PostgreSQL connection was therefore verified at both the database-client and Django application levels.

### 5. Environment-Based Configuration and Secret Management

The `django-environ` package was installed to manage application configuration through environment variables.

A repository-root `.env` file was configured with the following settings:

- PostgreSQL database name.
- PostgreSQL database user.
- PostgreSQL database password.
- Database host and port.
- Django secret key.
- Django debug setting.
- Allowed hosts.

Django settings were updated to read these values from the environment.

The following configuration areas were updated:

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `DATABASES`

The `.env` file was added to Git ignore rules.

Private credentials and secret values were kept outside tracked source files.

### 6. Custom Email-Based User Model

The NexaMind accounts application was implemented using Django's authentication framework.

The custom `User` model extends Django's `AbstractUser`.

Key implementation decisions:

- Removed the default username field.
- Used email as the authentication identifier.
- Enforced email uniqueness.
- Set `USERNAME_FIELD = "email"`.
- Set `REQUIRED_FIELDS = []`.
- Implemented a custom `UserManager`.
- Normalized email addresses.
- Added validation for missing email addresses.
- Added validation for missing passwords.
- Used Django's `set_password()` method for password hashing.
- Implemented custom superuser creation and privilege-flag validation.

The custom user model was registered through:

`AUTH_USER_MODEL = "accounts.User"`

The application was added to Django's installed applications.

The model was inspected through Django's user-model discovery mechanism, confirming that Django resolved the custom accounts user model.

### 7. Database Migration

The initial accounts migration was generated:

`apps/accounts/migrations/0001_initial.py`

The migration was inspected before being applied.

The generated migration correctly included:

- The custom user model.
- The email field with uniqueness enabled.
- Django authentication fields.
- Group and permission relationships.
- The custom user manager.
- No username field.

The initial migration was then applied successfully.

Django successfully applied the required migrations for:

- `contenttypes`
- `auth`
- `accounts`
- `admin`
- `sessions`

The custom user model was therefore established in the PostgreSQL database.

### 8. Automated Account Tests

Automated tests were implemented for the custom user manager.

The test coverage includes:

1. Successful regular user creation.
2. Email normalization.
3. Rejection of missing email addresses.
4. Rejection of missing passwords.
5. Successful superuser creation.
6. Validation of the superuser staff flag.
7. Validation of the superuser privilege flag.

#### Testing Challenge: Test Database Permissions

The initial account test execution failed because the PostgreSQL role did not have permission to create a test database.

The failure was investigated by inspecting PostgreSQL role attributes.

The development database role was then granted the `CREATEDB` attribute so Django's test runner could create and destroy its temporary test database.

The permission was verified before rerunning the tests.

#### Final Test Results

The account test suite completed successfully.

| Test Result      | Count |
| ---------------- | ----- |
| Tests discovered | 7     |
| Passed           | 7     |
| Failed           | 0     |
| Errors           | 0     |

The test runner successfully created and destroyed its temporary test database.

**Final result: `OK`**

This verifies the tested user-manager behaviors against the configured PostgreSQL-backed Django test environment.

### 9. Git Hygiene and Repository Maintenance

The repository's Git ignore rules were reviewed and improved.

The following exclusions were added or verified:

- `.env` and environment-specific secret files.
- Python bytecode and cache directories.
- Virtual environments, including `.venv-openssl3/`.
- SQLite database files.
- Node.js dependencies and generated build output.
- Logs and IDE-specific files.

Git ignore behavior was verified for:

- The repository-root `.env` file.
- `backend/db.sqlite3`.
- Python bytecode files.

The backend directory was inspected with untracked files displayed individually.

Only legitimate backend source files and project assets remained visible for review; ignored environment and generated files were excluded.

No backend source files were staged or committed during this verification.

### 10. Learning Documentation

The `docs/08-learning/` directory was reviewed and organized around five complementary engineering records.

| Document                  | Responsibility                                                               |
| ------------------------- | ---------------------------------------------------------------------------- |
| `engineering-journal.md`  | Chronological development history and project progress                       |
| `technical-challenges.md` | Significant technical problems and their resolutions                         |
| `problem-solving-log.md`  | Detailed debugging investigations, hypotheses, root causes, and verification |
| `lessons-learned.md`      | Reusable engineering knowledge and insights                                  |
| `future-improvements.md`  | Potential improvements and future considerations                             |

A README was created or updated to explain the purpose of each document and provide navigation links.

The documentation links were checked against the actual files.

The existing November 10 environment migration entry in this journal was preserved as historical documentation.

### 11. Challenges and Engineering Observations

The following challenges were encountered and resolved during this development milestone:

- An OpenSSL compatibility issue affected the original Python virtual environment.
- The active Python interpreter initially did not match the intended pyenv version.
- PostgreSQL authentication and database connectivity required configuration.
- Django required environment-based settings for PostgreSQL and secret management.
- The initial test execution exposed insufficient database-creation privileges for the test runner.
- Git ignore rules needed to account for the newly created virtual environment and local database files.

Each issue was investigated through inspection and verification rather than bypassed without understanding its cause.

### 12. Lessons Learned

- Verify the actual Python executable before debugging dependency problems.
- A virtual environment is only reliable when its underlying Python installation and runtime dependencies work correctly.
- Test database permissions are separate from ordinary application database access.
- Django's custom user model should be established before creating application migrations that depend on it.
- Database migrations should be inspected before being applied.
- Passwords should be handled through Django's password-hashing mechanisms rather than stored directly.
- Environment-specific secrets must remain outside version control.
- Automated tests provide evidence of behavior, not proof that every possible edge case is covered.
- Git ignore rules should be verified rather than assumed to work.
- Engineering documentation should distinguish historical facts, current implementation state, and future work.

### 13. Current Status

The development environment migration has been followed by successful backend and database verification.

The following foundation is now operational:

- Ubuntu 26.04 development environment.
- Python 3.12.12 working virtual environment.
- Django 6.1.3 backend.
- Native PostgreSQL 18.6 database.
- Environment-based Django configuration.
- PostgreSQL database connection.
- Custom email-based user model.
- Initial accounts migration.
- Applied Django database migrations.
- Seven passing account-manager tests.
- Git ignore rules for local secrets and generated files.
- Five-document learning documentation structure.

The NexaMind accounts foundation is implemented and verified at the current development milestone.

However, the project is not yet a complete authentication system. Registration and login API endpoints, serializers, authentication flows, and their corresponding API tests remain future implementation work.

The backend source files and learning documentation have not yet completed the final Git staging and milestone commit review.

### 14. Resumption Point

Resume NexaMind development from the verified PostgreSQL-backed accounts foundation.

Recommended next actions:

1. Review the current accounts implementation and its tests.
2. Review the complete backend configuration and dependency files.
3. Review the final Git changes and untracked project files.
4. Confirm that no secrets, local databases, virtual environments, or generated files will be committed.
5. Stage the verified backend foundation, documentation, and architecture assets.
6. Inspect the staged changes before creating a milestone commit.
7. Continue with the next accounts-layer implementation milestone: registration API design and implementation.

Do not recreate the existing backend, custom user model, PostgreSQL database, or migrations.

Continue incrementally, verifying each implementation milestone before proceeding.

---

**Entry date:** 2026-11-11
**Activity:** PostgreSQL integration and authentication foundation
**Project:** NexaMind
**Status:** PostgreSQL-backed accounts foundation implemented; seven tests passing; Git milestone review pending
