# Soliplex Workspace -- Roadmap

> Persistent file workspaces for Soliplex rooms. Facade architecture with
> swappable backends: dufs (MVP) -> OpenCloud (production).
>
> **Every slice has a mandatory AI review gate.** See
> [current-plan.md](current-plan.md) for exact tool invocations and prompts.

## Timeline Overview

```text
Week 1-2    Slice 0: Project Setup + Provider Interface         [DONE]
Week 2-3    Slice 1: dufs Backend + Integration Test Infra      [restructured]
Week 3-4    Slice 2: REST API + API Integration Tests           [restructured]
Week 4-5    Slice 3: E2E Tests Through Soliplex                 [NEW]
Week 5-6    Slice 4: OpenCloud Backend                          [was Slice 3]
Week 6-7    Slice 5: OpenCloud Lifecycle + Embed Mode           [was Slice 4]
Week 7-8    Slice 6: Ephemeral Per-Chat Workspaces              [was Slice 5]
Week 8-9    Slice 7: RAG Integration Pipeline                   [was Slice 6]
Week 10-11  Slice 8: Security Audit + Production Hardening      [was Slice 7]
Week 12-13  Slice 9: Docs + Release                             [was Slice 8]
```

## Milestones

### M0: Foundation (Weeks 1-2) [DONE]

> Repo setup, tooling, provider protocol, mock provider, 100% coverage
> baseline established.

- Project scaffolding (pyproject.toml, pre-commit, CI)
- `WorkspaceProvider` Protocol defined
- `MockWorkspaceProvider` for testing
- `DisabledWorkspaceProvider` for backward compatibility
- ADR-0001 committed

### M1: dufs MVP + Integration Infra (Weeks 2-5)

> Slices 1-3. Users can upload/download/list/delete files via REST API
> backed by dufs. Full test pyramid: unit + integration + E2E.

- `DufsWorkspaceProvider` implementation (WebDAV over httpx)
- REST API endpoints: `/v1/rooms/{room_id}/workspace/...`
- Docker Compose test infrastructure
- Integration tests against real dufs instance
- E2E tests through full stack
- Shared `normalize_path()` utility extracted

### M2: OpenCloud Integration (Weeks 5-7)

> Rooms get full-featured workspaces via OpenCloud Spaces.
> Versioning, sharing, WebDAV, embed UI.

- `OpenCloudWorkspaceProvider` implementation
- Keycloak client_credentials M2M auth
- Room lifecycle: create/delete Space on room create/delete
- Member sync: room ACL -> Space permissions
- Docker Compose: Soliplex + OpenCloud + Keycloak
- Integration tests against real OpenCloud instance

### M2.5: Ephemeral Per-Chat Workspaces (Week 7-8)

> Temp workspaces scoped to a single chat session. Auto-reaped after
> configurable TTL (default: 7 days).

- `EphemeralWorkspaceProvider` decorator/wrapper
- Session-scoped workspace creation
- TTL metadata tracking + reaper background task
- Promotion: copy files from ephemeral to persistent workspace

### M3: RAG + Production (Weeks 8-11)

> Workspace files auto-ingest into RAG pipeline.
> Security hardened. Monitoring. Backup strategy.

- File watcher / event-driven ingestion
- Per-room ingest configuration
- Security audit (token flows, path traversal, CSP)
- Monitoring dashboards
- Backup documentation and testing

### M4: Release (Weeks 12-13)

> Documentation complete. Published to PyPI. Soliplex integration PR.

- User documentation
- Developer guide (adding new providers)
- Configuration reference
- PyPI package published
- PR to soliplex/soliplex for integration

---

## Backlog (Future Milestones)

### B1: LLM Tooling / Skills for Workspace Operations

> LLM agents and skills that can read, write, search, and operate on
> workspace contents. Enables AI-powered file workflows within rooms.

- **Workspace tools for LLM**: read_file, write_file, list_files, search
- **Context injection**: auto-include relevant workspace files in LLM context
- **File generation**: LLM can create files and save to workspace
- **Skill registry**: workspace operations as Soliplex skills
- **Permission model**: LLM tool access scoped to room-level permissions
- **Audit trail**: all LLM-initiated file operations logged

---

## AI Review Gate Protocol

Every slice must pass an AI review gate before merging. The gate consists of:

1. **Autonomous checks**: ruff, pyright, pytest (100% coverage)
2. **Gemini review** via `mcp__gemini__read_files` (model: `gemini-3.1-pro-preview`)
3. **Codex review** via `mcp__codex__codex` (sandbox: `read-only`)
4. **Triage**: Critical/High = must fix. Medium = fix or justify.
5. **Re-review** after fixes to confirm resolution.

See [current-plan.md](current-plan.md) for per-slice review prompts and
exact tool invocation syntax.
