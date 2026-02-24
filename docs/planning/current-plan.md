# Soliplex Workspace -- Milestone Plan

> 9 slices. Each slice is a stacked PR. Codex and Gemini review at gates
> where external integration, security, or architecture decisions are involved.

## Stacked PR Strategy

```text
main
 └── feat/workspace-provider
      └── feat/workspace-provider/slice-0   PR #? -> main
           └── feat/workspace-provider/slice-1   PR #? -> slice-0
                └── feat/workspace-provider/slice-2   PR #? -> slice-1
                     └── feat/workspace-provider/slice-3   PR #? -> slice-2
                          └── feat/workspace-provider/slice-4   PR #? -> slice-3
                               └── feat/workspace-provider/slice-5   PR #? -> slice-4
                                    └── feat/workspace-provider/slice-6   PR #? -> slice-5
                                         └── feat/workspace-provider/slice-7   PR #? -> slice-6
                                              └── feat/workspace-provider/slice-8   PR #? -> slice-7
```

Each PR shows only the diff for its slice. Merges happen bottom-up.

---

## Milestones

### Slice 0: Project Setup + Provider Interface

- **Spec:** [slice-0-project-setup.md](slice-0-project-setup.md)
- **Branch:** `feat/workspace-provider/slice-0`
- **PR target:** `main`

#### Gates

**Implementation:**

- [ ] Project scaffolding complete (pyproject.toml, pre-commit, CI skeleton)
- [ ] `WorkspaceProvider` Protocol defined with all operations
- [ ] `MockWorkspaceProvider` -- in-memory implementation for tests
- [ ] `DisabledWorkspaceProvider` -- no-op for backward compat
- [ ] ADR-0001 committed
- [ ] Type stubs: `WorkspaceInfo`, `FileInfo`, `WorkspaceConfig`

**Code quality (autonomous):**

- [ ] `ruff check` -- 0 issues
- [ ] `ruff format --check` -- no changes
- [ ] No `# noqa` directives added
- [ ] Pre-commit hooks pass (`pre-commit run --all-files`)

**Tests (autonomous):**

- [ ] `pytest` -- all pass
- [ ] Coverage >= 95% on `src/soliplex_workspace/`
- [ ] `MockWorkspaceProvider` tested: create, list, upload, download, delete
- [ ] `DisabledWorkspaceProvider` tested: all methods raise or return empty

**AI review (gate -- must pass before next slice):**

- [ ] **Gemini `read_files`** (`gemini-3.1-pro-preview`) of provider protocol
      -- interface completeness, Python typing best practices
- [ ] All review feedback addressed

#### Autonomous test commands

```bash
ruff check
ruff format --check
pytest
pre-commit run --all-files
```

---

### Slice 1: dufs Backend + Auth Proxy

- **Spec:** [slice-1-dufs-backend.md](slice-1-dufs-backend.md)
- **Branch:** `feat/workspace-provider/slice-1`
- **PR target:** `feat/workspace-provider/slice-0`
- **Depends on:** Slice 0

#### Gates

**Implementation:**

- [ ] `DufsWorkspaceProvider` implements `WorkspaceProvider`
- [ ] WebDAV client for file operations (httpx-based)
- [ ] JWT validation middleware for auth proxy
- [ ] Path-based room isolation (each room = subdirectory)
- [ ] Docker Compose: dufs service configured

**Code quality (autonomous):**

- [ ] `ruff check` -- 0 issues
- [ ] `ruff format --check` -- no changes
- [ ] Pre-commit hooks pass

**Tests (autonomous):**

- [ ] `pytest tests/unit/` -- all pass, >= 100% coverage
- [ ] `pytest tests/integration/ -m dufs` -- all pass (requires dufs running)
- [ ] Integration: upload file, list files, download file, delete file
- [ ] Integration: cross-room isolation verified
- [ ] Integration: unauthorized access rejected

**AI review (gate -- security-critical):**

- [ ] **Codex review** of auth proxy -- JWT validation, path traversal prevention
- [ ] **Gemini `read_files`** (`gemini-3.1-pro-preview`) of dufs provider
      -- WebDAV client correctness, error handling
- [ ] All review feedback addressed

#### Autonomous test commands

```bash
ruff check && ruff format --check
pytest tests/unit/
# Integration (requires: docker compose up dufs)
pytest tests/integration/ -m dufs -v
```

---

### Slice 2: REST API Endpoints

- **Spec:** [slice-2-rest-api.md](slice-2-rest-api.md)
- **Branch:** `feat/workspace-provider/slice-2`
- **PR target:** `feat/workspace-provider/slice-1`
- **Depends on:** Slice 1

#### Gates

**Implementation:**

- [ ] FastAPI router: `/api/v1/rooms/{room_id}/files/`
- [ ] Endpoints: list, upload, download, delete, create folder, move
- [ ] Provider selection via configuration
- [ ] OpenAPI schema generated and reviewed

**Code quality (autonomous):**

- [ ] `ruff check` -- 0 issues
- [ ] `ruff format --check` -- no changes
- [ ] Pre-commit hooks pass

**Tests (autonomous):**

- [ ] `pytest tests/unit/` -- all pass, >= 100% coverage
- [ ] Unit tests use `MockWorkspaceProvider` (no external deps)
- [ ] All endpoints tested: happy path + error cases
- [ ] Auth enforcement tested (unauthorized, wrong room)

#### Autonomous test commands

```bash
ruff check && ruff format --check
pytest tests/unit/ -v
```

---

### Slice 3: OpenCloud Backend -- Space Management

- **Spec:** [slice-3-opencloud-spaces.md](slice-3-opencloud-spaces.md)
- **Branch:** `feat/workspace-provider/slice-3`
- **PR target:** `feat/workspace-provider/slice-2`
- **Depends on:** Slice 2

#### Gates

**Implementation:**

- [ ] `OpenCloudWorkspaceProvider` -- Space CRUD via Graph API
- [ ] Keycloak `client_credentials` token acquisition
- [ ] Token caching with TTL-based refresh
- [ ] Create Space, delete Space, get Space, list files
- [ ] Member management: invite user, remove user

**Code quality (autonomous):**

- [ ] `ruff check` -- 0 issues
- [ ] `ruff format --check` -- no changes
- [ ] Pre-commit hooks pass

**Tests (autonomous):**

- [ ] `pytest tests/unit/` -- all pass, >= 100% coverage
- [ ] Unit tests mock HTTP calls (respx)
- [ ] `pytest tests/integration/ -m opencloud` -- all pass (requires OpenCloud)
- [ ] Integration: create space, upload file, list, download, delete, remove space

**AI review (gate -- architecture + security critical):**

- [ ] **Codex review** of Graph API client -- token handling, error recovery
- [ ] **Gemini `read_files`** (`gemini-3.1-pro-preview`) of OpenCloud provider
      -- API surface completeness, auth flow correctness
- [ ] All review feedback addressed

#### Autonomous test commands

```bash
ruff check && ruff format --check
pytest tests/unit/ -v
# Integration (requires: docker compose up opencloud keycloak)
pytest tests/integration/ -m opencloud -v
```

---

### Slice 4: OpenCloud Lifecycle Hooks + Embed Mode

- **Spec:** [slice-4-opencloud-lifecycle.md](slice-4-opencloud-lifecycle.md)
- **Branch:** `feat/workspace-provider/slice-4`
- **PR target:** `feat/workspace-provider/slice-3`
- **Depends on:** Slice 3

#### Gates

**Implementation:**

- [ ] Room create -> auto-create OpenCloud Space
- [ ] Room delete -> soft-delete OpenCloud Space (trash)
- [ ] User join room -> add to Space with role
- [ ] User leave room -> remove from Space
- [ ] Embed URL generation with delegated auth params
- [ ] WebDAV URL generation per room

**Code quality (autonomous):**

- [ ] `ruff check` -- 0 issues
- [ ] `ruff format --check` -- no changes
- [ ] Pre-commit hooks pass

**Tests (autonomous):**

- [ ] `pytest tests/unit/` -- all pass, >= 100% coverage
- [ ] `pytest tests/integration/ -m opencloud` -- lifecycle tests pass
- [ ] Integration: full lifecycle (create room -> add user -> upload -> remove
      user -> verify access denied -> delete room)

**AI review (gate -- security critical):**

- [ ] **Codex review** of lifecycle hooks -- race conditions, cleanup on failure
- [ ] **Gemini `read_files`** (`gemini-3.1-pro-preview`) of embed URL generation
      -- CSP, origin validation, token delegation security
- [ ] All review feedback addressed

#### Autonomous test commands

```bash
ruff check && ruff format --check
pytest tests/unit/ -v
pytest tests/integration/ -m opencloud -v
```

---

### Slice 5: Ephemeral Per-Chat Workspaces

- **Spec:** [slice-5-ephemeral-workspaces.md](slice-5-ephemeral-workspaces.md)
- **Branch:** `feat/workspace-provider/slice-5`
- **PR target:** `feat/workspace-provider/slice-4`
- **Depends on:** Slice 4

#### Gates

**Implementation:**

- [ ] `EphemeralWorkspace` model (chat_id, room_id, created_at, expires_at,
      last_accessed_at)
- [ ] `EphemeralWorkspaceMixin` -- wraps any `WorkspaceProvider` with
      session-scoped namespacing (prefix `/ephemeral/{chat_id}/`)
- [ ] TTL-based expiry: configurable `ephemeral_ttl_days` (default: 7)
- [ ] `last_accessed_at` touch on every file operation (extends TTL window)
- [ ] Reaper: async background task that purges expired ephemeral workspaces
- [ ] Reaper config: `reaper_interval_minutes` (default: 60)
- [ ] Per-workspace size cap: `ephemeral_max_size_bytes` (default: 50MB)
- [ ] Promotion: copy files from ephemeral workspace to room's persistent
      workspace via `promote_to_persistent(chat_id, room_id, paths)`
- [ ] Manual teardown: `delete_ephemeral_workspace(room_id, chat_id)`

**Code quality (autonomous):**

- [ ] `ruff check` -- 0 issues
- [ ] `ruff format --check` -- no changes
- [ ] Pre-commit hooks pass

**Tests (autonomous):**

- [ ] `pytest tests/unit/` -- all pass, >= 100% coverage
- [ ] Unit: ephemeral workspace CRUD (create, list, upload, download, delete)
- [ ] Unit: TTL expiry -- workspace with past `expires_at` is reaped
- [ ] Unit: `last_accessed_at` extends on file ops
- [ ] Unit: size cap enforcement -- upload beyond limit raises error
- [ ] Unit: promotion copies files to persistent workspace
- [ ] Unit: cross-chat isolation within same room
- [ ] Integration: reaper task purges expired workspaces

**AI review (gate -- architecture decision):**

- [ ] **Gemini `read_files`** (`gemini-3.1-pro-preview`) of ephemeral mixin
      -- namespace isolation, TTL correctness, race conditions in reaper
- [ ] All review feedback addressed

#### Autonomous test commands

```bash
ruff check && ruff format --check
pytest tests/unit/ -v
pytest tests/integration/ -v
```

---

### Slice 6: RAG Integration Pipeline

- **Spec:** [slice-6-rag-integration.md](slice-6-rag-integration.md)
- **Branch:** `feat/workspace-provider/slice-6`
- **PR target:** `feat/workspace-provider/slice-5`
- **Depends on:** Slice 5

#### Gates

**Implementation:**

- [ ] File change detection (poll-based via WebDAV PROPFIND)
- [ ] Configurable ingest rules (file types, size limits)
- [ ] Trigger haiku.rag pipeline for new/updated files
- [ ] Remove vectors on file deletion
- [ ] Per-room ingest enable/disable
- [ ] Ephemeral workspace files excluded from RAG by default (configurable)

**Code quality (autonomous):**

- [ ] `ruff check` -- 0 issues
- [ ] `ruff format --check` -- no changes
- [ ] Pre-commit hooks pass

**Tests (autonomous):**

- [ ] `pytest tests/unit/` -- all pass, >= 100% coverage
- [ ] Unit tests: change detection logic, ingest rule matching
- [ ] Integration: upload PDF -> verify vectors created in LanceDB

#### Autonomous test commands

```bash
ruff check && ruff format --check
pytest tests/unit/ -v
pytest tests/integration/ -m rag -v
```

---

### Slice 7: Security Audit + Production Hardening

- **Spec:** [slice-7-security-hardening.md](slice-7-security-hardening.md)
- **Branch:** `feat/workspace-provider/slice-7`
- **PR target:** `feat/workspace-provider/slice-6`
- **Depends on:** Slices 0-6

#### Gates

**Implementation:**

- [ ] Path traversal prevention (all providers)
- [ ] Token scope minimization (Keycloak client config)
- [ ] Rate limiting on file endpoints
- [ ] CSP headers for embed mode
- [ ] File size limits enforced
- [ ] Antivirus integration documented (OpenCloud antivirus service)
- [ ] Backup strategy documented and tested
- [ ] Ephemeral reaper: verify no data leaks after purge

**Code quality (autonomous):**

- [ ] `ruff check` -- 0 issues
- [ ] `ruff format --check` -- no changes
- [ ] Pre-commit hooks pass
- [ ] `bandit` security scan -- 0 high/critical findings

**Tests (autonomous):**

- [ ] `pytest` -- all pass, >= 100% coverage
- [ ] Security test: path traversal attempts rejected
- [ ] Security test: expired/invalid tokens rejected
- [ ] Security test: cross-room access denied
- [ ] Security test: oversized upload rejected
- [ ] Security test: ephemeral namespace cannot escape to persistent workspace

**AI review (gate -- MANDATORY security review):**

- [ ] **Codex review** of ALL security-relevant code -- auth, path validation,
      token handling, CSP
- [ ] **Gemini `read_files`** (`gemini-3.1-pro-preview`) of entire `src/` --
      OWASP Top 10 check, injection vectors, auth bypass
- [ ] All review feedback addressed
- [ ] No unresolved security findings

#### Autonomous test commands

```bash
ruff check && ruff format --check
pytest -v
# Security scan
pip install bandit && bandit -r src/ -ll
```

---

### Slice 8: Documentation + Release

- **Spec:** [slice-8-docs-release.md](slice-8-docs-release.md)
- **Branch:** `feat/workspace-provider/slice-8`
- **PR target:** `feat/workspace-provider/slice-7`
- **Depends on:** Slices 0-7

#### Gates

**Implementation:**

- [ ] README with quickstart, configuration, architecture diagram
- [ ] Developer guide: adding new providers
- [ ] Configuration reference (YAML schema)
- [ ] Docker Compose examples (dufs, OpenCloud, full stack)
- [ ] CHANGELOG.md

**Code quality (autonomous):**

- [ ] `ruff check` -- 0 issues
- [ ] `ruff format --check` -- no changes
- [ ] Pre-commit hooks pass
- [ ] Markdown lint -- 0 issues

**Tests (autonomous):**

- [ ] `pytest` -- all pass, >= 100% coverage
- [ ] All code examples in docs are tested or extracted from tests

#### Autonomous test commands

```bash
ruff check && ruff format --check
pytest -v
pre-commit run --all-files
```

---

## Workflow

```text
For each slice:
  1. Branch from previous slice
  2. Implement (code + tests)
  3. Run autonomous tests (commands listed per slice)
  4. Run ruff check + ruff format
  5. Run pre-commit run --all-files
  6. Commit + push + create PR
  7. AI reviews (where marked as gate)
  8. Address feedback, re-run tests
  9. Merge only after all gates pass
  10. Next slice branches from merged result
```

## Testing Philosophy

**Integration-first.** Workspaces connect to external systems (dufs, OpenCloud,
Keycloak). Integration tests are the primary confidence mechanism.

| Level | Location | Runner | What it proves |
|-------|----------|--------|---------------|
| Unit | `tests/unit/` | `pytest` | Protocol compliance, mock provider, data models |
| Integration (dufs) | `tests/integration/` | `pytest -m dufs` | Real WebDAV ops against dufs |
| Integration (OpenCloud) | `tests/integration/` | `pytest -m opencloud` | Real Graph API + WebDAV against OpenCloud |
| Integration (RAG) | `tests/integration/` | `pytest -m rag` | File upload -> vector ingestion pipeline |
| Security | `tests/integration/` | `pytest -m security` | Auth bypass, path traversal, injection |

**Coverage target:** 100% on `src/soliplex_workspace/`.

**Markers:** Integration tests requiring external services use pytest markers.
Unit tests run without any external dependencies.

## Dependencies

- **Soliplex** (`~/dev/soliplex`) -- final integration PR targets this repo
- **Keycloak** -- shared OIDC provider for OpenCloud + Soliplex
- **dufs** -- MVP backend (Docker image: `sigoden/dufs`)
- **OpenCloud** -- production backend (Docker image: `opencloudeu/opencloud`)

## Reference

- [ADR-0001: Facade Architecture](../adr/0001-workspace-provider-facade.md)
- [Roadmap](roadmap.md)
- [Full Analysis](/Users/runyaga/dev/soliplex-owncloud/ANALYSIS.md)
