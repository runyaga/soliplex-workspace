# Soliplex Workspace -- Roadmap

> Persistent file workspaces for Soliplex rooms. Facade architecture with
> swappable backends: dufs (MVP) -> OpenCloud (production).
>
> **Every slice has a mandatory AI review gate.** See
> [current-plan.md](current-plan.md) for exact tool invocations and prompts.

## Timeline Overview

```text
Week 1-2    Slice 0: Project Setup + Provider Interface
Week 2-3    Slice 1: dufs Backend + Auth Proxy
Week 3-4    Slice 2: REST API Endpoints + Basic Flutter Widget
Week 5-6    Slice 3: OpenCloud Backend Implementation
Week 6-7    Slice 4: OpenCloud Lifecycle Hooks + Embed Mode
Week 7-8    Slice 5: Ephemeral Per-Chat Workspaces
Week 8-9    Slice 6: RAG Integration Pipeline
Week 10-11  Slice 7: Security Audit + Production Hardening
Week 12-13  Slice 8: Documentation + Release
```

## Milestones

### M0: Foundation (Weeks 1-2)

> Repo setup, tooling, provider protocol, mock provider, 100% coverage
> baseline established.

- Project scaffolding (pyproject.toml, pre-commit, CI)
- `WorkspaceProvider` Protocol defined
- `MockWorkspaceProvider` for testing
- `DisabledWorkspaceProvider` for backward compatibility
- ADR-0001 committed

### M1: dufs MVP (Weeks 2-4)

> Users can upload/download/list/delete files in a room workspace.
> Auth validated against Soliplex JWT. Basic web UI via dufs built-in.

- `DufsWorkspaceProvider` implementation
- JWT auth proxy middleware
- REST API: `GET/POST/DELETE /api/v1/rooms/{room_id}/files/`
- Docker Compose: Soliplex + dufs
- Integration tests against real dufs instance

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
> configurable TTL (default: 7 days). Lets users create throwaway file
> contexts without polluting the room's persistent workspace.

- `EphemeralWorkspaceProvider` decorator/wrapper around any base provider
- Session-scoped workspace creation (chat_id + room_id composite key)
- TTL metadata tracking (created_at, expires_at, last_accessed_at)
- Reaper background task: purge expired workspaces on schedule
- API: `POST /api/v1/rooms/{room_id}/chats/{chat_id}/workspace/` (create)
- API: `DELETE .../workspace/` (manual teardown before TTL)
- Config: `ephemeral_ttl_days`, `ephemeral_max_size_bytes`, `reaper_interval`
- Isolation: ephemeral workspaces live in a separate namespace (prefix `/ephemeral/`)
- Promotion: option to "keep" files by copying to room's persistent workspace

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

## AI Review Gate Protocol

Every slice must pass an AI review gate before merging. The gate consists of:

1. **Gemini review** via `mcp__gemini__read_files` (model: `gemini-3.1-pro-preview`)
   - Reviews architecture, typing, completeness, edge cases
2. **Codex review** via `mcp__codex__codex` (sandbox: `read-only`)
   - Reviews security, bugs, correctness, edge cases
3. **Triage**: Critical/High = must fix. Medium = fix or justify.
4. **Re-review** after fixes to confirm resolution.

See [current-plan.md](current-plan.md) for per-slice review prompts and
exact tool invocation syntax.
