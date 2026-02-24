# Soliplex Workspace -- Milestone Plan

> 9 slices. Each slice is a stacked PR. **Every slice has a mandatory AI
> review gate that must pass before proceeding to the next slice.**

## AI Review Gate Protocol

Every slice follows this review protocol. The orchestrating agent MUST
execute these steps and record results before merging.

### Tools

| Tool | Purpose | Model / Config |
|------|---------|----------------|
| `mcp__gemini__read_files` | Architectural review, typing, completeness | `gemini-3.1-pro-preview` |
| `mcp__codex__codex` | Security review, bug finding, edge cases | `sandbox: read-only`, `approval-policy: on-failure` |

### Process

1. Implementation complete, all autonomous checks pass
2. Run Gemini review (see slice-specific prompt)
3. Run Codex review (see slice-specific prompt)
4. Triage findings: Critical/High must be fixed, Medium is fix-or-justify
5. Fix code, re-run autonomous checks
6. Re-run both reviews on fixed code to confirm resolution
7. Mark all gate checkboxes, proceed to next slice

---

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

#### Implementation

- [ ] Project scaffolding complete (pyproject.toml, pre-commit, CI skeleton)
- [ ] `WorkspaceProvider` Protocol defined with all operations
- [ ] `MockWorkspaceProvider` -- in-memory implementation for tests
- [ ] `DisabledWorkspaceProvider` -- no-op for backward compat
- [ ] ADR-0001 committed
- [ ] Type stubs: `WorkspaceInfo`, `FileInfo`

#### Code Quality (autonomous)

- [ ] `uv run ruff check` -- 0 issues
- [ ] `uv run ruff format --check` -- no changes
- [ ] `uv run pyright` -- 0 errors, 0 warnings
- [ ] `uv run pre-commit run --all-files` -- all hooks pass

#### Tests (autonomous)

- [ ] `uv run pytest` -- all pass
- [ ] Coverage = 100% on `src/soliplex_workspace/`
- [ ] `MockWorkspaceProvider` tested: create, list, upload, download, delete
- [ ] `DisabledWorkspaceProvider` tested: all methods raise

#### AI Review Gate (MANDATORY)

- [ ] **Gemini review** -- execute:
      ```json
      mcp__gemini__read_files(
        file_paths=[
          "src/soliplex_workspace/protocol.py",
          "src/soliplex_workspace/models.py",
          "src/soliplex_workspace/exceptions.py"
        ],
        prompt="Review Slice 0 of a workspace provider library. Check:
          1. Interface completeness (missing ops: stat, copy, search,
             streaming, pagination?)
          2. Python typing (pyright strict correctness)
          3. Protocol design (method signatures, return types)
          4. Data model completeness (missing fields?)
          5. Exception hierarchy (missing error types?)
          6. Edge cases (path encoding, concurrency, large files)
          Be critical. Flag anything that breaks real backends.",
        model="gemini-3.1-pro-preview"
      )
      ```
- [ ] **Codex review** -- execute:
      ```json
      mcp__codex__codex(
        prompt="Review workspace provider library at CWD for Slice 0.
          Focus on: 1. WorkspaceProvider Protocol completeness
          2. Data models completeness 3. Exception hierarchy
          4. Typing issues for pyright strict 5. MockWorkspaceProvider
          correctness 6. Security (path traversal in _normalize).
          Be specific about what is missing or wrong.",
        sandbox="read-only",
        approval-policy="on-failure"
      )
      ```
- [ ] All Critical/High findings fixed in code
- [ ] All Medium findings fixed or justified in PR description
- [ ] Re-run both reviews after fixes -- no new Critical/High findings
- [ ] Autonomous checks re-pass after fixes

---

### Slice 1: dufs Backend + Auth Proxy

- **Spec:** [slice-1-dufs-backend.md](slice-1-dufs-backend.md)
- **Branch:** `feat/workspace-provider/slice-1`
- **PR target:** `feat/workspace-provider/slice-0`
- **Depends on:** Slice 0

#### Implementation

- [ ] `DufsWorkspaceProvider` implements `WorkspaceProvider`
- [ ] WebDAV client for file operations (httpx-based)
- [ ] JWT validation middleware for auth proxy
- [ ] Path-based room isolation (each room = subdirectory)
- [ ] Docker Compose: dufs service configured

#### Code Quality (autonomous)

- [ ] `uv run ruff check` -- 0 issues
- [ ] `uv run ruff format --check` -- no changes
- [ ] `uv run pyright` -- 0 errors, 0 warnings
- [ ] `uv run pre-commit run --all-files` -- all hooks pass

#### Tests (autonomous)

- [ ] `uv run pytest tests/unit/` -- all pass, 100% coverage
- [ ] `uv run pytest tests/integration/ -m dufs` -- all pass (requires dufs)
- [ ] Integration: upload file, list files, download file, delete file
- [ ] Integration: cross-room isolation verified
- [ ] Integration: unauthorized access rejected

#### AI Review Gate (MANDATORY -- security-critical)

- [ ] **Gemini review** -- execute:
      ```json
      mcp__gemini__read_files(
        file_paths=[
          "src/soliplex_workspace/providers/dufs.py",
          "src/soliplex_workspace/auth.py"
        ],
        prompt="Review dufs WebDAV provider and JWT auth proxy. Check:
          1. WebDAV client correctness (PUT/GET/DELETE/MKCOL/MOVE)
          2. Path traversal prevention (room isolation)
          3. JWT validation completeness (expiry, issuer, audience)
          4. Error handling (network failures, timeouts, 404/409/507)
          5. httpx client lifecycle (connection pooling, cleanup)
          6. Content-type detection, large file handling
          Security is paramount. Flag any auth bypass vectors.",
        model="gemini-3.1-pro-preview"
      )
      ```
- [ ] **Codex review** -- execute:
      ```json
      mcp__codex__codex(
        prompt="Security review of dufs WebDAV provider and JWT auth
          proxy in CWD. Focus on: 1. Path traversal prevention
          2. JWT validation (bypass vectors) 3. WebDAV client
          error handling 4. Room isolation enforcement 5. Token
          injection or header manipulation. Treat as a pentest.",
        sandbox="read-only",
        approval-policy="on-failure"
      )
      ```
- [ ] All Critical/High findings fixed in code
- [ ] All Medium findings fixed or justified in PR description
- [ ] Re-run both reviews after fixes -- no new Critical/High findings
- [ ] Autonomous checks re-pass after fixes

---

### Slice 2: REST API Endpoints

- **Spec:** [slice-2-rest-api.md](slice-2-rest-api.md)
- **Branch:** `feat/workspace-provider/slice-2`
- **PR target:** `feat/workspace-provider/slice-1`
- **Depends on:** Slice 1

#### Implementation

- [ ] FastAPI router: `/api/v1/rooms/{room_id}/files/`
- [ ] Endpoints: list, upload, download, delete, create folder, move
- [ ] Provider selection via configuration
- [ ] OpenAPI schema generated and reviewed

#### Code Quality (autonomous)

- [ ] `uv run ruff check` -- 0 issues
- [ ] `uv run ruff format --check` -- no changes
- [ ] `uv run pyright` -- 0 errors, 0 warnings
- [ ] `uv run pre-commit run --all-files` -- all hooks pass

#### Tests (autonomous)

- [ ] `uv run pytest tests/unit/` -- all pass, 100% coverage
- [ ] Unit tests use `MockWorkspaceProvider` (no external deps)
- [ ] All endpoints tested: happy path + error cases
- [ ] Auth enforcement tested (unauthorized, wrong room)

#### AI Review Gate (MANDATORY)

- [ ] **Gemini review** -- execute:
      ```json
      mcp__gemini__read_files(
        file_paths=[
          "src/soliplex_workspace/api/router.py",
          "src/soliplex_workspace/api/dependencies.py"
        ],
        prompt="Review FastAPI REST endpoints for workspace files. Check:
          1. REST API design (resource naming, HTTP verbs, status codes)
          2. Input validation (path params, query params, file size)
          3. Error response format consistency
          4. Auth dependency injection correctness
          5. OpenAPI schema quality (descriptions, examples)
          6. Streaming upload/download handling",
        model="gemini-3.1-pro-preview"
      )
      ```
- [ ] **Codex review** -- execute:
      ```json
      mcp__codex__codex(
        prompt="Review FastAPI REST API endpoints in CWD. Focus on:
          1. Input validation and sanitization 2. Auth enforcement
          on every endpoint 3. Error handling consistency
          4. File upload size limits 5. Path injection via URL params
          6. Missing endpoints for workspace operations.",
        sandbox="read-only",
        approval-policy="on-failure"
      )
      ```
- [ ] All Critical/High findings fixed in code
- [ ] All Medium findings fixed or justified in PR description
- [ ] Re-run both reviews after fixes -- no new Critical/High findings
- [ ] Autonomous checks re-pass after fixes

---

### Slice 3: OpenCloud Backend -- Space Management

- **Spec:** [slice-3-opencloud-spaces.md](slice-3-opencloud-spaces.md)
- **Branch:** `feat/workspace-provider/slice-3`
- **PR target:** `feat/workspace-provider/slice-2`
- **Depends on:** Slice 2

#### Implementation

- [ ] `OpenCloudWorkspaceProvider` -- Space CRUD via Graph API
- [ ] Keycloak `client_credentials` token acquisition
- [ ] Token caching with TTL-based refresh
- [ ] Create Space, delete Space, get Space, list files
- [ ] Member management: invite user, remove user

#### Code Quality (autonomous)

- [ ] `uv run ruff check` -- 0 issues
- [ ] `uv run ruff format --check` -- no changes
- [ ] `uv run pyright` -- 0 errors, 0 warnings
- [ ] `uv run pre-commit run --all-files` -- all hooks pass

#### Tests (autonomous)

- [ ] `uv run pytest tests/unit/` -- all pass, 100% coverage
- [ ] Unit tests mock HTTP calls (respx)
- [ ] `uv run pytest tests/integration/ -m opencloud` -- all pass
- [ ] Integration: create space, upload, list, download, delete, remove space

#### AI Review Gate (MANDATORY -- architecture + security critical)

- [ ] **Gemini review** -- execute:
      ```json
      mcp__gemini__read_files(
        file_paths=[
          "src/soliplex_workspace/providers/opencloud.py",
          "src/soliplex_workspace/auth.py"
        ],
        prompt="Review OpenCloud Graph API provider. Check:
          1. Graph API usage correctness (Spaces CRUD, permissions)
          2. Keycloak client_credentials flow (token refresh, caching)
          3. Token security (no logging tokens, secure storage)
          4. Error recovery (409 conflicts, 503 retries, token expiry)
          5. Member sync correctness (role mapping, edge cases)
          6. WebDAV file operations (upload, download, PROPFIND)
          Compare against OpenCloud LibreGraph API spec.",
        model="gemini-3.1-pro-preview"
      )
      ```
- [ ] **Codex review** -- execute:
      ```json
      mcp__codex__codex(
        prompt="Security + architecture review of OpenCloud provider
          in CWD. Focus on: 1. Token handling (client_credentials,
          caching, refresh races) 2. Graph API error handling
          3. Member permission sync correctness 4. Data leakage
          between rooms 5. HTTP client security (TLS, timeouts)
          6. Retry logic (idempotency, backoff).",
        sandbox="read-only",
        approval-policy="on-failure"
      )
      ```
- [ ] All Critical/High findings fixed in code
- [ ] All Medium findings fixed or justified in PR description
- [ ] Re-run both reviews after fixes -- no new Critical/High findings
- [ ] Autonomous checks re-pass after fixes

---

### Slice 4: OpenCloud Lifecycle Hooks + Embed Mode

- **Spec:** [slice-4-opencloud-lifecycle.md](slice-4-opencloud-lifecycle.md)
- **Branch:** `feat/workspace-provider/slice-4`
- **PR target:** `feat/workspace-provider/slice-3`
- **Depends on:** Slice 3

#### Implementation

- [ ] Room create -> auto-create OpenCloud Space
- [ ] Room delete -> soft-delete OpenCloud Space (trash)
- [ ] User join room -> add to Space with role
- [ ] User leave room -> remove from Space
- [ ] Embed URL generation with delegated auth params
- [ ] WebDAV URL generation per room

#### Code Quality (autonomous)

- [ ] `uv run ruff check` -- 0 issues
- [ ] `uv run ruff format --check` -- no changes
- [ ] `uv run pyright` -- 0 errors, 0 warnings
- [ ] `uv run pre-commit run --all-files` -- all hooks pass

#### Tests (autonomous)

- [ ] `uv run pytest tests/unit/` -- all pass, 100% coverage
- [ ] `uv run pytest tests/integration/ -m opencloud` -- lifecycle tests pass
- [ ] Integration: full lifecycle (create room -> add user -> upload ->
      remove user -> verify access denied -> delete room)

#### AI Review Gate (MANDATORY -- security critical)

- [ ] **Gemini review** -- execute:
      ```json
      mcp__gemini__read_files(
        file_paths=[
          "src/soliplex_workspace/lifecycle.py",
          "src/soliplex_workspace/embed.py"
        ],
        prompt="Review OpenCloud lifecycle hooks and embed mode. Check:
          1. Race conditions (concurrent room create/delete)
          2. Cleanup on partial failure (Space created but member add
             fails -- rollback?)
          3. Embed URL generation security (CSP, origin validation,
             token delegation via postMessage)
          4. Soft-delete vs hard-delete semantics
          5. Role mapping correctness (room admin -> Space manager?)
          6. Event ordering (what if user leaves before Space exists?)",
        model="gemini-3.1-pro-preview"
      )
      ```
- [ ] **Codex review** -- execute:
      ```json
      mcp__codex__codex(
        prompt="Review lifecycle hooks and embed mode in CWD. Focus on:
          1. Race conditions in room create/delete 2. Embed URL
          security (origin validation, CSP headers, clickjacking)
          3. Cleanup on failure (partial state) 4. Permission
          escalation vectors 5. Token delegation security.",
        sandbox="read-only",
        approval-policy="on-failure"
      )
      ```
- [ ] All Critical/High findings fixed in code
- [ ] All Medium findings fixed or justified in PR description
- [ ] Re-run both reviews after fixes -- no new Critical/High findings
- [ ] Autonomous checks re-pass after fixes

---

### Slice 5: Ephemeral Per-Chat Workspaces

- **Spec:** [slice-5-ephemeral-workspaces.md](slice-5-ephemeral-workspaces.md)
- **Branch:** `feat/workspace-provider/slice-5`
- **PR target:** `feat/workspace-provider/slice-4`
- **Depends on:** Slice 4

#### Implementation

- [ ] `EphemeralWorkspace` model (chat_id, room_id, created_at, expires_at,
      last_accessed_at)
- [ ] `EphemeralWorkspaceMixin` -- wraps any `WorkspaceProvider` with
      session-scoped namespacing (prefix `/ephemeral/{chat_id}/`)
- [ ] TTL-based expiry: configurable `ephemeral_ttl_days` (default: 7)
- [ ] `last_accessed_at` touch on every file operation (extends TTL window)
- [ ] Reaper: async background task that purges expired ephemeral workspaces
- [ ] Reaper config: `reaper_interval_minutes` (default: 60)
- [ ] Per-workspace size cap: `ephemeral_max_size_bytes` (default: 50MB)
- [ ] Promotion: copy files from ephemeral to persistent workspace
- [ ] Manual teardown: `delete_ephemeral_workspace(room_id, chat_id)`

#### Code Quality (autonomous)

- [ ] `uv run ruff check` -- 0 issues
- [ ] `uv run ruff format --check` -- no changes
- [ ] `uv run pyright` -- 0 errors, 0 warnings
- [ ] `uv run pre-commit run --all-files` -- all hooks pass

#### Tests (autonomous)

- [ ] `uv run pytest tests/unit/` -- all pass, 100% coverage
- [ ] Unit: ephemeral workspace CRUD (create, list, upload, download, delete)
- [ ] Unit: TTL expiry -- workspace with past `expires_at` is reaped
- [ ] Unit: `last_accessed_at` extends on file ops
- [ ] Unit: size cap enforcement -- upload beyond limit raises error
- [ ] Unit: promotion copies files to persistent workspace
- [ ] Unit: cross-chat isolation within same room
- [ ] Integration: reaper task purges expired workspaces

#### AI Review Gate (MANDATORY -- architecture)

- [ ] **Gemini review** -- execute:
      ```json
      mcp__gemini__read_files(
        file_paths=[
          "src/soliplex_workspace/ephemeral.py",
          "src/soliplex_workspace/reaper.py"
        ],
        prompt="Review ephemeral per-chat workspace system. Check:
          1. Namespace isolation (/ephemeral/{chat_id}/ prefix safety)
          2. TTL correctness (expiry calculation, timezone handling)
          3. Reaper race conditions (deleting while user is uploading)
          4. Size cap enforcement (TOCTOU between check and upload)
          5. Promotion correctness (atomic copy, partial failure)
          6. Data leakage (can chat A access chat B's files?)
          7. Cleanup completeness (no orphaned files after reap)",
        model="gemini-3.1-pro-preview"
      )
      ```
- [ ] **Codex review** -- execute:
      ```json
      mcp__codex__codex(
        prompt="Review ephemeral workspace system in CWD. Focus on:
          1. Namespace escape (can /ephemeral/../../ reach persistent?)
          2. Reaper concurrency safety 3. Size cap TOCTOU bugs
          4. Promotion atomicity 5. TTL bypass vectors
          6. Memory leaks in long-running reaper task.",
        sandbox="read-only",
        approval-policy="on-failure"
      )
      ```
- [ ] All Critical/High findings fixed in code
- [ ] All Medium findings fixed or justified in PR description
- [ ] Re-run both reviews after fixes -- no new Critical/High findings
- [ ] Autonomous checks re-pass after fixes

---

### Slice 6: RAG Integration Pipeline

- **Spec:** [slice-6-rag-integration.md](slice-6-rag-integration.md)
- **Branch:** `feat/workspace-provider/slice-6`
- **PR target:** `feat/workspace-provider/slice-5`
- **Depends on:** Slice 5

#### Implementation

- [ ] File change detection (poll-based via WebDAV PROPFIND)
- [ ] Configurable ingest rules (file types, size limits)
- [ ] Trigger haiku.rag pipeline for new/updated files
- [ ] Remove vectors on file deletion
- [ ] Per-room ingest enable/disable
- [ ] Ephemeral workspace files excluded from RAG by default (configurable)

#### Code Quality (autonomous)

- [ ] `uv run ruff check` -- 0 issues
- [ ] `uv run ruff format --check` -- no changes
- [ ] `uv run pyright` -- 0 errors, 0 warnings
- [ ] `uv run pre-commit run --all-files` -- all hooks pass

#### Tests (autonomous)

- [ ] `uv run pytest tests/unit/` -- all pass, 100% coverage
- [ ] Unit tests: change detection logic, ingest rule matching
- [ ] Integration: upload PDF -> verify vectors created in LanceDB

#### AI Review Gate (MANDATORY)

- [ ] **Gemini review** -- execute:
      ```json
      mcp__gemini__read_files(
        file_paths=[
          "src/soliplex_workspace/rag/watcher.py",
          "src/soliplex_workspace/rag/ingest.py"
        ],
        prompt="Review RAG integration pipeline. Check:
          1. Change detection reliability (missed events, duplicates)
          2. Ingest rule correctness (file type matching, size limits)
          3. Vector cleanup on file deletion (orphaned vectors?)
          4. Ephemeral file exclusion logic
          5. Error handling (RAG pipeline down, partial ingest)
          6. Performance (polling interval, batch size, backpressure)",
        model="gemini-3.1-pro-preview"
      )
      ```
- [ ] **Codex review** -- execute:
      ```json
      mcp__codex__codex(
        prompt="Review RAG integration pipeline in CWD. Focus on:
          1. File content injection (malicious PDF/DOCX) 2. Ingest
          rule bypass 3. Vector store consistency 4. Error recovery
          5. Resource exhaustion (unbounded queue, large files).",
        sandbox="read-only",
        approval-policy="on-failure"
      )
      ```
- [ ] All Critical/High findings fixed in code
- [ ] All Medium findings fixed or justified in PR description
- [ ] Re-run both reviews after fixes -- no new Critical/High findings
- [ ] Autonomous checks re-pass after fixes

---

### Slice 7: Security Audit + Production Hardening

- **Spec:** [slice-7-security-hardening.md](slice-7-security-hardening.md)
- **Branch:** `feat/workspace-provider/slice-7`
- **PR target:** `feat/workspace-provider/slice-6`
- **Depends on:** Slices 0-6

#### Implementation

- [ ] Path traversal prevention (all providers)
- [ ] Token scope minimization (Keycloak client config)
- [ ] Rate limiting on file endpoints
- [ ] CSP headers for embed mode
- [ ] File size limits enforced
- [ ] Antivirus integration documented (OpenCloud antivirus service)
- [ ] Backup strategy documented and tested
- [ ] Ephemeral reaper: verify no data leaks after purge

#### Code Quality (autonomous)

- [ ] `uv run ruff check` -- 0 issues
- [ ] `uv run ruff format --check` -- no changes
- [ ] `uv run pyright` -- 0 errors, 0 warnings
- [ ] `uv run pre-commit run --all-files` -- all hooks pass
- [ ] `bandit -r src/ -ll` -- 0 high/critical findings

#### Tests (autonomous)

- [ ] `uv run pytest` -- all pass, 100% coverage
- [ ] Security test: path traversal attempts rejected
- [ ] Security test: expired/invalid tokens rejected
- [ ] Security test: cross-room access denied
- [ ] Security test: oversized upload rejected
- [ ] Security test: ephemeral namespace cannot escape to persistent

#### AI Review Gate (MANDATORY -- FULL SECURITY AUDIT)

- [ ] **Gemini review** -- execute:
      ```json
      mcp__gemini__read_files(
        file_paths=["src/soliplex_workspace/"],  # entire src directory
        prompt="FULL SECURITY AUDIT of workspace provider library. Check:
          1. OWASP Top 10 (injection, broken auth, XSS, SSRF, etc.)
          2. Path traversal in ALL providers (mock, dufs, opencloud)
          3. Token handling (storage, refresh, expiry, logging)
          4. CSP headers for embed mode (clickjacking, XSS)
          5. Input validation on all public API surfaces
          6. Race conditions in concurrent file operations
          7. Ephemeral reaper data leakage
          8. Dependency supply chain (pinned versions?)
          This is the final security gate. Be adversarial.",
        model="gemini-3.1-pro-preview"
      )
      ```
- [ ] **Codex review** -- execute:
      ```json
      mcp__codex__codex(
        prompt="FULL SECURITY AUDIT of workspace provider library in CWD.
          Treat this as a penetration test. Check ALL files in src/ for:
          1. Auth bypass vectors 2. Path traversal 3. Token leakage
          4. SSRF 5. Injection (SQL, command, header) 6. Race conditions
          7. Deserialization bugs 8. Privilege escalation 9. DoS vectors
          10. Ephemeral namespace escape. Report severity for each finding.",
        sandbox="read-only",
        approval-policy="on-failure"
      )
      ```
- [ ] All Critical/High findings fixed in code
- [ ] All Medium findings fixed or justified in PR description
- [ ] **Zero unresolved Critical/High findings** (hard gate)
- [ ] Re-run both reviews after fixes -- clean pass
- [ ] Autonomous checks re-pass after fixes

---

### Slice 8: Documentation + Release

- **Spec:** [slice-8-docs-release.md](slice-8-docs-release.md)
- **Branch:** `feat/workspace-provider/slice-8`
- **PR target:** `feat/workspace-provider/slice-7`
- **Depends on:** Slices 0-7

#### Implementation

- [ ] README with quickstart, configuration, architecture diagram
- [ ] Developer guide: adding new providers
- [ ] Configuration reference (YAML schema)
- [ ] Docker Compose examples (dufs, OpenCloud, full stack)
- [ ] CHANGELOG.md

#### Code Quality (autonomous)

- [ ] `uv run ruff check` -- 0 issues
- [ ] `uv run ruff format --check` -- no changes
- [ ] `uv run pyright` -- 0 errors, 0 warnings
- [ ] `uv run pre-commit run --all-files` -- all hooks pass
- [ ] Markdown lint -- 0 issues

#### Tests (autonomous)

- [ ] `uv run pytest` -- all pass, 100% coverage
- [ ] All code examples in docs are tested or extracted from tests

#### AI Review Gate (MANDATORY -- docs quality)

- [ ] **Gemini review** -- execute:
      ```json
      mcp__gemini__read_files(
        file_paths=["README.md", "docs/"],
        prompt="Review documentation for completeness and accuracy. Check:
          1. README quickstart actually works (correct commands)
          2. Architecture diagram matches actual code structure
          3. Configuration reference covers all options
          4. Developer guide is sufficient to add a new provider
          5. Docker Compose examples are correct and tested
          6. No stale references to removed/renamed code",
        model="gemini-3.1-pro-preview"
      )
      ```
- [ ] **Codex review** -- execute:
      ```json
      mcp__codex__codex(
        prompt="Review documentation in CWD for accuracy. Verify:
          1. Code examples compile and match actual API 2. Install
          instructions work 3. Config examples are valid YAML
          4. No secrets or internal URLs in docs 5. Links are valid.",
        sandbox="read-only",
        approval-policy="on-failure"
      )
      ```
- [ ] All findings addressed
- [ ] Autonomous checks re-pass after fixes

---

## Workflow

```text
For each slice:
  1. Branch from previous slice
  2. Implement (code + tests)
  3. Run autonomous checks:
     - uv run ruff check
     - uv run ruff format --check
     - uv run pyright
     - uv run pytest
     - uv run pre-commit run --all-files
  4. Run AI Review Gate:
     a. mcp__gemini__read_files (gemini-3.1-pro-preview) -- see slice prompt
     b. mcp__codex__codex (read-only sandbox) -- see slice prompt
     c. Triage: Critical/High = must fix, Medium = fix or justify
     d. Fix code, re-run autonomous checks
     e. Re-run both AI reviews on fixed code
     f. Mark all gate checkboxes
  5. Commit + push + create PR
  6. Merge only after ALL gate checkboxes are checked
  7. Next slice branches from merged result
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
