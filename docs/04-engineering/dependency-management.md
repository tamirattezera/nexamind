# Dependency Management

## 1. Purpose

This document defines how external libraries, frameworks, SDKs, and development tools are selected, installed, updated, and maintained in NexaMind.

Its objectives are to:

- Keep dependencies manageable and secure.
- Make development environments reproducible.
- Avoid unnecessary packages.
- Reduce compatibility problems.
- Track dependency changes.
- Support reliable development, testing, and deployment.

Dependency management is an ongoing engineering responsibility, not simply a matter of installing packages.

---

## 2. Dependency Management Principles

NexaMind follows these principles:

1. **Install intentionally:** Every dependency should solve an identifiable problem.
2. **Prefer established packages:** Favor actively maintained libraries with reliable documentation and community adoption.
3. **Avoid unnecessary dependencies:** Do not install a package when a small amount of understandable native code is sufficient.
4. **Pin reproducible versions:** Use lockfiles or pinned dependency versions to make installations predictable.
5. **Separate environments:** Keep development, testing, and production dependencies appropriately organized.
6. **Review updates:** Do not update every package blindly.
7. **Protect security:** Monitor known vulnerabilities and remove unnecessary or abandoned packages.
8. **Document important choices:** Explain significant dependencies and architectural reasons for selecting them.

---

## 3. Dependency Categories

NexaMind uses several categories of dependencies.

| Category                 | Purpose                            | Examples                    |
| ------------------------ | ---------------------------------- | --------------------------- |
| Runtime dependencies     | Required for application operation | Django, React               |
| Framework dependencies   | Provide application structure      | Django REST Framework, Vite |
| Integration dependencies | Connect external services          | Google GenAI SDK            |
| Development dependencies | Support local development          | ESLint, Ruff                |
| Testing dependencies     | Support automated testing          | Vitest, Playwright          |
| Build dependencies       | Support production builds          | Vite                        |

A dependency should belong to the appropriate category so that production installations do not unnecessarily include development-only tools.

---

## 4. Backend Dependency Management

### 4.1 Backend environment

The backend uses Python and a virtual environment.

Target Python version:

```text
Python 3.12
```

Create and activate the environment:

```bash
cd backend

python3.12 -m venv .venv
source .venv/bin/activate
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

The virtual environment must remain local and must not be committed to Git.

### 4.2 Backend dependency organization

The planned structure is:

```text
backend/
└── requirements/
    ├── base.txt
    ├── development.txt
    └── production.txt
```

**base.txt**

Contains packages required by the application in every environment.

Potential dependencies:

- Django
- Django REST Framework
- PostgreSQL database adapter
- Gemini SDK
- Environment configuration library

**development.txt**

Contains packages useful during development and testing.

Potential dependencies:

- Testing tools.
- Code formatting tools.
- Linting tools.
- Debugging utilities.

**production.txt**

Contains production-specific dependencies only when they are genuinely different from the base environment.

It should not duplicate packages unnecessarily.

### 4.3 Dependency installation

Example:

```bash
pip install django
pip install djangorestframework
```

After selecting and verifying package versions, record them in the appropriate requirements files.

Install the complete development environment using:

```bash
pip install -r requirements/development.txt
```

The development requirements file should include the base requirements through an explicit reference, for example:

```text
-r base.txt
```

### 4.4 Version recording

For a small Python project, pinned requirements are a reasonable starting point.

Example format:

```text
Django==<verified-version>
djangorestframework==<verified-version>
```

The version placeholders are illustrative. Actual versions must be selected from current, compatible package releases during setup.

Do not invent or copy version numbers without checking compatibility.

For more advanced dependency management, a tool such as `uv` may be considered later.

---

## 5. Frontend Dependency Management

### 5.1 Frontend environment

The frontend uses:

- Node.js 22.
- npm.
- React.
- Vite.
- JavaScript.

TypeScript is not part of the current project requirements.

### 5.2 Dependency categories

npm distinguishes between regular dependencies and development dependencies.

**Runtime dependencies**

Installed with:

```bash
npm install package-name
```

Examples:

- React.
- React DOM.
- Axios.
- React Router.

**Development dependencies**

Installed with:

```bash
npm install -D package-name
```

Examples:

- Vitest.
- ESLint.
- React Testing Library.
- Playwright.
- Prettier, if adopted.

Only install packages when the corresponding functionality is being implemented.

### 5.3 Package lockfile

The frontend must commit:

```text
frontend/package.json
frontend/package-lock.json
```

`package.json` records the declared dependencies and scripts.

`package-lock.json` records the resolved dependency tree.

Both files should be committed so other environments can reproduce the installation.

For clean installations, use:

```bash
npm ci
```

Unlike an ordinary installation, `npm ci` installs according to the lockfile and is suitable for CI environments.

Do not manually edit `package-lock.json`.

---

## 6. Initial Dependency Selection

The following table describes the planned technology choices. It is not a claim that every package has already been installed.

| Area              | Planned technology               | Reason                                  |
| ----------------- | -------------------------------- | --------------------------------------- |
| Backend framework | Django                           | Backend application foundation          |
| API               | Django REST Framework            | REST API development                    |
| Database          | PostgreSQL                       | Relational data persistence             |
| AI integration    | Official Google GenAI Python SDK | Gemini communication                    |
| Frontend          | React                            | User interface                          |
| Frontend build    | Vite                             | Development server and production build |
| HTTP client       | Axios                            | Backend API communication               |
| Routing           | React Router                     | Frontend navigation                     |
| Backend testing   | Django test framework            | Backend verification                    |
| Frontend testing  | Vitest                           | JavaScript and component testing        |
| Browser testing   | Playwright                       | End-to-end verification                 |

Additional libraries should be selected only when the implementation requires them.

For example, JWT authentication requires choosing a suitable Django REST Framework-compatible authentication implementation. That decision should be verified and documented when authentication is implemented.

---

## 7. Evaluating a New Dependency

Before installing a package, answer these questions:

1. What specific problem does it solve?
2. Can the existing framework or standard library solve the problem?
3. Is the package actively maintained?
4. Is its documentation reliable?
5. Does it support the project's Python or Node.js version?
6. Does it introduce additional dependencies?
7. Does it have known security vulnerabilities?
8. Is its license compatible with the project?
9. Will the package be used in production or only development?
10. Is the package worth its long-term maintenance cost?

Avoid installing packages simply because a tutorial uses them.

---

## 8. Updating Dependencies

Dependencies should be updated deliberately.

### Python

Inspect installed packages:

```bash
pip list
```

Inspect outdated packages:

```bash
pip list --outdated
```

Update a selected package only after reviewing its release notes and compatibility.

After updating:

1. Run dependency installation checks.
2. Run Django system checks.
3. Run backend tests.
4. Verify database and API behavior.
5. Update the requirements files.
6. Commit the dependency change separately when practical.

### JavaScript

Inspect installed packages:

```bash
npm list
```

Check outdated packages:

```bash
npm outdated
```

Review a proposed update before applying it:

```bash
npm update
```

For major version changes, inspect the package migration guide and breaking changes.

After updating:

```bash
npm ci
npm run lint
npm run test
npm run build
```

The commands above assume the corresponding scripts are configured.

---

## 9. Security and Vulnerability Management

Third-party dependencies can introduce security risks.

NexaMind should:

- Prefer trusted package registries.
- Avoid downloading packages from unknown sources.
- Monitor dependency advisories.
- Remove unused dependencies.
- Update vulnerable packages promptly.
- Review major dependency changes before merging.
- Avoid exposing credentials through package scripts or configuration.
- Keep secrets outside dependency manifests and lockfiles.

Useful checks include:

```bash
# Python
pip check

# npm
npm audit
```

An audit result should be reviewed rather than automatically applying every suggested fix.

Some updates may introduce breaking changes or incompatible dependency versions.

---

## 10. Dependency Reproducibility

A working application on one computer does not guarantee that it will work on another.

NexaMind should preserve enough information to recreate its development and deployment environments.

Important files include:

```text
backend/
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
└── .python-version

frontend/
├── package.json
└── package-lock.json
```

The `.python-version` file is optional and should be introduced if a Python version manager is adopted.

The project should document the expected versions of:

- Python.
- Node.js.
- npm.
- PostgreSQL.

Lockfiles and dependency manifests must be maintained whenever dependencies change.

---

## 11. Handling Dependency Conflicts

Dependency conflicts can happen when packages require incompatible versions of the same dependency.

When a conflict occurs:

1. Read the complete error message.
2. Identify the conflicting packages.
3. Inspect their version requirements.
4. Review the official package documentation.
5. Select compatible versions.
6. Reinstall from the intended dependency files.
7. Run the relevant tests.
8. Record the resolution if it affects architecture or maintenance.

Do not solve dependency problems by randomly upgrading or downgrading multiple packages.

Understand the conflict first.

---

## 12. Removing Dependencies

Unused dependencies increase maintenance and security costs.

Before removing a package:

1. Search the codebase for its imports and usage.
2. Check whether another package depends on it.
3. Remove it from the appropriate dependency manifest.
4. Regenerate the lockfile when necessary.
5. Reinstall dependencies.
6. Run relevant tests and builds.

Remove packages that no longer provide value.

---

## 13. Dependency Change Workflow

Every meaningful dependency change should follow this process:

```text
Identify a requirement
        ↓
Evaluate available packages
        ↓
Select a suitable dependency
        ↓
Install the package
        ↓
Update dependency records
        ↓
Implement the integration
        ↓
Run tests and validation
        ↓
Inspect the changes
        ↓
Commit the dependency change
```

For significant dependencies, document the reason for selection and any important trade-offs.

---

## 14. Definition of Done

A dependency-related task is complete when:

- [ ] The dependency solves a documented or understood requirement.
- [ ] Its compatibility has been checked.
- [ ] It is recorded in the correct dependency manifest.
- [ ] Lockfiles are updated where applicable.
- [ ] No unnecessary packages were introduced.
- [ ] Relevant tests pass.
- [ ] Security concerns have been reviewed.
- [ ] The development environment remains reproducible.
- [ ] Documentation is updated where necessary.

---

## 15. Final Principle

Dependencies are long-term maintenance responsibilities.

A strong engineering project does not measure quality by the number of libraries it uses.

NexaMind should use the smallest practical set of reliable dependencies, understand why each one exists, and maintain them with discipline.
