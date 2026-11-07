# Git Workflow

## 1. Purpose

This document defines the Git and GitHub workflow for developing NexaMind.

Its goals are to:

- Maintain a reliable project history.
- Organize development into small, understandable changes.
- Make progress traceable and verifiable.
- Reduce accidental commits of secrets or generated files.
- Establish consistent commit messages.
- Keep the main branch stable.

This workflow is designed for an individual developer and can evolve when the project gains collaborators.

---

## 2. Source Control Principles

NexaMind follows these principles:

1. **Commit meaningful changes:** Each commit should represent one logical unit of work.
2. **Verify before committing:** Run relevant tests or validation before creating a commit.
3. **Keep history understandable:** Use descriptive commit messages.
4. **Protect sensitive information:** Never commit credentials, API keys, or private configuration.
5. **Keep the main branch stable:** Avoid leaving incomplete or broken work on the main branch.
6. **Document important decisions:** Update relevant documentation when implementation decisions change.

Git history should communicate how the application evolved, not merely record that files changed.

---

## 3. Branch Strategy

NexaMind uses a lightweight branch strategy.

### 3.1 Main branch

The `main` branch represents the primary, stable development line.

It should contain changes that have passed their relevant verification.

### 3.2 Supporting branches

Create a separate branch when working on a meaningful feature, bug fix, refactoring task, or documentation change.

| Branch prefix | Purpose                        | Example                      |
| ------------- | ------------------------------ | ---------------------------- |
| `feat/`       | New functionality              | `feat/user-registration`     |
| `fix/`        | Bug fixes                      | `fix/conversation-ownership` |
| `docs/`       | Documentation                  | `docs/api-overview`          |
| `test/`       | Test additions or improvements | `test/message-endpoint`      |
| `refactor/`   | Internal code improvements     | `refactor/gemini-service`    |
| `chore/`      | Maintenance and configuration  | `chore/backend-dependencies` |

### 3.3 Branch naming rules

- Use lowercase names.
- Separate words with hyphens.
- Keep names short and descriptive.
- Use a prefix that communicates the purpose.
- Avoid vague names such as `updates`, `work`, or `new-branch`.

For small, low-risk documentation changes, committing directly to `main` can be acceptable. Use supporting branches for substantial changes.

---

## 4. Commit Message Convention

NexaMind follows the Conventional Commits style.

### 4.1 Format

```text
<type>: <short description>
```

Optional scope:

```text
<type>(<scope>): <short description>
```

### 4.2 Commit types

| Type       | Meaning                    | Example                                   |
| ---------- | -------------------------- | ----------------------------------------- |
| `feat`     | Add functionality          | `feat: add user registration endpoint`    |
| `fix`      | Correct a defect           | `fix: enforce conversation ownership`     |
| `docs`     | Documentation changes      | `docs: document backend architecture`     |
| `test`     | Add or update tests        | `test: cover message creation`            |
| `refactor` | Improve internal structure | `refactor: separate Gemini service logic` |
| `chore`    | Maintenance/configuration  | `chore: configure backend dependencies`   |
| `style`    | Formatting-only changes    | `style: format React components`          |
| `perf`     | Performance improvements   | `perf: optimize conversation queries`     |

### 4.3 Commit message guidelines

- Use the imperative mood: `add`, `fix`, `document`, `configure`.
- Keep the subject concise and meaningful.
- Avoid vague messages such as `changes`, `update`, or `final`.
- Do not claim functionality that has not been implemented.

Examples:

```bash
git commit -m "docs: add project architecture overview"

git commit -m "feat: implement conversation creation"

git commit -m "test: add authentication endpoint tests"

git commit -m "fix: prevent access to another user's messages"
```

---

## 5. Standard Development Workflow

Use this workflow for each meaningful task.

### Step 1: Inspect the repository

```bash
git status
git branch --show-current
git log -5 --oneline
```

Understand the current state before changing anything.

### Step 2: Create or switch to a branch

For example:

```bash
git switch -c feat/user-registration
```

If the branch already exists:

```bash
git switch feat/user-registration
```

### Step 3: Implement one logical task

Keep changes focused.

For example, when implementing user registration:

- Add the required backend logic.
- Add input validation.
- Add relevant tests.
- Update the API documentation if the contract changes.

Avoid combining unrelated work into one commit.

### Step 4: Verify the changes

Run the relevant checks.

Examples:

```bash
# Backend
python manage.py check
python manage.py test

# Frontend
npm run lint
npm run test
npm run build
```

These commands are examples; use the actual scripts and test configuration available in each project component.

Do not report a test as passing unless it has actually been executed successfully.

### Step 5: Inspect the changes

```bash
git status
git diff
```

Review the changes for:

- Accidental files.
- Debugging statements.
- Unnecessary modifications.
- Exposed credentials.
- Incomplete implementation.
- Documentation that no longer matches the code.

### Step 6: Stage intentional changes

Prefer staging specific files:

```bash
git add docs/04-engineering/git-workflow.md
```

For multiple files, specify their paths.

Avoid blindly running `git add .`, especially when environment files, generated files, or local experiments may exist.

### Step 7: Inspect staged changes

```bash
git diff --cached
git status
```

Verify exactly what will enter the commit.

### Step 8: Commit

```bash
git commit -m "docs: define Git workflow"
```

### Step 9: Push to GitHub

For a new branch:

```bash
git push -u origin docs/git-workflow
```

For an existing branch:

```bash
git push
```

### Step 10: Verify the result

```bash
git status
git log -1 --oneline
git branch -vv
```

Confirm that the commit exists and the expected branch is synchronized with its remote.

---

## 6. Pull Request Workflow

Pull requests are useful even in a solo project when a change is substantial.

A pull request provides an opportunity to review changes before merging them into `main`.

### 6.1 When to create a pull request

Consider a pull request for:

- Authentication implementation.
- Database schema changes.
- Gemini integration.
- Major API changes.
- Frontend feature implementation.
- Significant refactoring.

A pull request is not necessary for every small documentation correction.

### 6.2 Pull request checklist

Before merging, verify:

- [ ] The change solves the intended task.
- [ ] The code follows project conventions.
- [ ] Relevant tests pass.
- [ ] No secrets or sensitive files are included.
- [ ] Documentation has been updated where necessary.
- [ ] No unrelated changes are included.
- [ ] The application still builds or passes its relevant checks.

### 6.3 Merge strategy

For this project, a normal merge or squash merge is sufficient.

Choose the strategy that keeps the project history understandable. Avoid unnecessary merge complexity.

---

## 7. Files That Must Never Be Committed

NexaMind must not commit secrets, local environments, or unnecessary generated files.

Examples include:

```gitignore
# Environment variables and secrets
.env
.env.*
!.env.example

# Python
.venv/
venv/
__pycache__/
*.py[cod]
.pytest_cache/

# Django
staticfiles/
media/

# Node
node_modules/
dist/

# Build and test outputs
coverage/
*.log

# Editor and operating-system files
.vscode/
.idea/
.DS_Store
Thumbs.db
```

This is a starting point, not a complete `.gitignore` specification. Review the final rules against the actual project structure.

Important:

- `.env.example` may be committed only when it contains placeholder values and no real credentials.
- The Gemini API key must remain in backend environment configuration.
- Frontend variables exposed through Vite must never contain private credentials.
- If a secret is accidentally committed, removing it in a later commit does not make it safe. Revoke or rotate the exposed credential and address the repository history.

---

## 8. Handling Mistakes and Recovering Changes

Git provides recovery commands, but they have different consequences.

### 8.1 Discard unstaged changes

```bash
git restore path/to/file
```

This discards uncommitted modifications in the specified file. Use it only when those changes are no longer needed.

### 8.2 Unstage a file

```bash
git restore --staged path/to/file
```

This removes the file from the staging area without discarding its working-tree changes.

### 8.3 Undo a published commit safely

```bash
git revert <commit-hash>
```

This creates a new commit that reverses the selected commit. It is generally the safer approach for shared or published history.

### 8.4 Reset local history

```bash
git reset --soft HEAD~1
```

This moves the current branch back one commit while keeping the changes staged.

Be careful with `git reset --hard`: it can permanently discard uncommitted work. Avoid rewriting published history unless you understand the consequences and have coordinated with anyone sharing the branch.

---

## 9. Git Tags and Releases

Git tags can identify important project milestones.

Examples:

```bash
git tag -a v0.1.0 -m "Initial backend milestone"
git push origin v0.1.0
```

Use version tags when a milestone is sufficiently complete and verified.

Possible release progression:

- `v0.1.0` — Initial backend foundation.
- `v0.2.0` — Core Gemini integration.
- `v0.3.0` — Functional frontend.
- `v1.0.0` — Verified MVP release.

These are illustrative milestones, not claims about the current project status.

---

## 10. Documentation and Project Status

Git history and project documentation should agree.

When implementation changes affect a documented decision:

1. Identify the affected document.
2. Update it to reflect the actual implementation.
3. Record significant architectural changes as Architecture Decision Records (ADRs).
4. Include relevant documentation changes in the same logical commit when practical.

Maintain a clear distinction between:

- **Planned:** Designed but not implemented.
- **In progress:** Implementation has started.
- **Implemented:** Code exists.
- **Verified:** Relevant checks have passed.
- **Deployed:** Available in the target environment and verified there.

Do not describe planned features as completed features.

---

## 11. Recommended Daily Git Checklist

Before finishing a development session:

- [ ] Review `git status`.
- [ ] Check the current branch.
- [ ] Run relevant tests or validation.
- [ ] Inspect the final diff.
- [ ] Confirm no secrets are staged.
- [ ] Commit meaningful, verified changes.
- [ ] Push important completed work.
- [ ] Record unfinished tasks and known issues.

---

## 12. Final Principle

Git is not simply a backup tool. It is an engineering record.

A good NexaMind repository should make it possible to understand:

- What changed.
- Why it changed.
- When it changed.
- How the change was verified.
- Whether the change was completed or remains in progress.

The objective is not to produce a large number of commits. It is to produce a clear, reliable, and verifiable engineering history.
