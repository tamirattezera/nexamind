
# Problem-Solving Log

This document records individual technical problem-solving investigations during NexaMind development.

Each record captures the problem, investigation, hypotheses, experiments, root cause, implemented solution, and verification results. The purpose is to preserve debugging knowledge and make future troubleshooting more systematic.

---

## PS-001 — pyenv Python Version Not Selected

**Date:** 2026-11-10
**Category:** Development Environment / Python
**Status:** Resolved

### 1. Problem

Python 3.12.12 was installed through `pyenv`, but the active Python environment was not using that version.

The `pyenv global` configuration was set to `system`, so the system-installed Python version was selected instead of the intended Python 3.12.12 runtime.

This created inconsistency between the installed Python version and the runtime required for NexaMind development.

### 2. Investigation

The following commands were used to inspect the Python environment and version configuration:

```bash
pyenv --version
pyenv versions
pyenv global
python --version
python3 --version
```

The investigation showed that Python 3.12.12 was installed, but it had not been selected as the global Python version.

### 3. Root Cause

The global `pyenv` version was configured as `system` instead of Python 3.12.12.

Consequently, the shell continued resolving Python commands to the system Python installation.

### 4. Solution

Python 3.12.12 was selected as the global version:

```bash
pyenv global 3.12.12
```

### 5. Verification

The active Python versions were checked again:

```bash
python --version
python3 --version
pyenv global
```

The environment reported Python 3.12.12 as the selected version.

Additional development tools were checked to confirm that the environment remained usable, including Node.js, npm, and NVM.

### 6. Lessons Learned

- Installing a Python version does not automatically make it the active version.
- `pyenv` controls Python version selection independently of Python installation.
- Environment configuration should be verified before creating virtual environments.
- Consistent runtime versions reduce environment-related debugging problems.

### 7. Prevention

Before starting Python development in a new environment:

1. Check the installed Python versions.
2. Confirm the active `pyenv` version.
3. Verify `python` and `python3` resolve to the expected runtime.
4. Create the project virtual environment only after confirming the runtime.

---

## PS-002 — PostgreSQL Test Database Permission Denied

**Date:** 2026-11-11
**Category:** Database / Django Testing / PostgreSQL
**Status:** Resolved

### 1. Problem

Django was successfully connecting to the PostgreSQL application database using the database role `nexamind_user`.

However, running the account test suite failed when Django attempted to create a temporary test database.

The PostgreSQL role did not have permission to create databases.

### 2. Investigation

The account test suite was executed:

```bash
python manage.py test apps.accounts
```

Django reported a database permission error while attempting to create its test database.

The PostgreSQL role attributes were inspected:

```bash
sudo -u postgres psql -c "\du nexamind_user"
```

The role did not have the `CREATEDB` attribute.

### 3. Root Cause

Django's test runner creates a separate temporary database to isolate automated tests from the development database.

The PostgreSQL role `nexamind_user` had permission to access the application database but lacked permission to create the temporary test database.

Database connectivity was working; the failure was caused by insufficient database-level privileges.

### 4. Solution

The `CREATEDB` attribute was granted to the development database role:

```bash
sudo -u postgres psql -c "ALTER ROLE nexamind_user CREATEDB;"
```

This allowed Django to create the temporary test database.

### 5. Verification

The role attributes were inspected again:

```bash
sudo -u postgres psql -c "\du nexamind_user"
```

The `Create DB` attribute was now enabled.

The account test suite was executed again:

```bash
python manage.py test apps.accounts
```

**Result:**

- 7 tests executed.
- All 7 tests passed.
- Django successfully created the test database.
- Django successfully destroyed the test database after testing.
- No test failures were reported.

### 6. Engineering Considerations

Granting `CREATEDB` is convenient for local development and Django testing.

However, database privileges should be reviewed before production deployment. Production database roles should follow the principle of least privilege.

A separate test database role or controlled test database provisioning process may be considered if the deployment architecture requires stricter privilege separation.

### 7. Lessons Learned

- Successful database connectivity does not guarantee sufficient database privileges.
- Django's test runner requires permission to create its test database.
- PostgreSQL role attributes directly affect application and testing workflows.
- Database permissions should be configured according to the environment's responsibilities.
- Automated tests should be rerun after resolving infrastructure-level failures.

### 8. Prevention

When configuring PostgreSQL for Django:

1. Create a dedicated application database role.
2. Grant the privileges required by the development workflow.
3. Verify role attributes before running database-dependent tests.
4. Confirm that Django can create and destroy its test database.
5. Review and restrict privileges before production deployment.

---

## Record Identification

Use sequential identifiers for future problem-solving investigations:

- PS-003
- PS-004
- PS-005

Each record should document one distinct technical problem and its investigation, resolution, or current status.
