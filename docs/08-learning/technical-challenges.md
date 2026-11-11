# Technical Challenges

This document records significant technical challenges encountered during NexaMind development, their impact on the project, and their resolution status.

It focuses on technical constraints and engineering difficulties rather than chronological development history or detailed debugging procedures.

---

## Challenge Register

| ID     | Challenge                            | Area                    | Status   |
| ------ | ------------------------------------ | ----------------------- | -------- |
| TC-001 | Python and OpenSSL compatibility     | Development Environment | Resolved |
| TC-002 | PostgreSQL test database permissions | Database and Testing    | Resolved |

---

## TC-001 — Python and OpenSSL Compatibility

### Problem

The original Python virtual environment had an OpenSSL compatibility issue that affected Python cryptographic functionality.

### Impact

The environment could not reliably support the backend development workflow.

### Resolution

A separate Python virtual environment, `.venv-openssl3`, was established using Python 3.12.12 with a working OpenSSL 3 runtime.

### Status

Resolved.

---

## TC-002 — PostgreSQL Test Database Permissions

### Problem

The PostgreSQL role used by Django could connect to the application database but initially lacked permission to create a temporary database for automated tests.

### Impact

Django's test runner could not initialize its test database, preventing the account test suite from running.

### Resolution

The `CREATEDB` attribute was granted to the development database role `nexamind_user`.

The role permission was verified, and the account test suite subsequently completed successfully.

### Status

Resolved.

---
