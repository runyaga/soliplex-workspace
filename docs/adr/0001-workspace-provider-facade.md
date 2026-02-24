# ADR-0001: Workspace Provider Facade Architecture

**Status:** Accepted
**Date:** 2026-02-24
**Deciders:** runyaga

## Context

Soliplex rooms need persistent file workspaces. Users should be able to upload,
download, share, and collaboratively manage files within a room. Today rooms
have conversation threads and RAG vector databases but no file storage.

We evaluated six candidate backends:

| Candidate | Verdict | Reason |
|-----------|---------|--------|
| **OpenCloud** | Selected (Phase 2) | Spaces = rooms, Graph API, WebDAV, embed mode, OIDC, Apache-2.0 |
| **dufs** | Selected (Phase 1 MVP) | Tiny, fast, MIT, WebDAV, good enough for validation |
| MinIO | Eliminated | OSS frozen (July 2024), MBSL license, must build entire UI |
| Nextcloud | Eliminated | PHP, heavy, overkill for file workspace |
| FileBrowser | Eliminated | Maintenance mode, undocumented API |
| Build from scratch | Rejected | 3-6 month engineering cost for table-stakes features |

## Decision

Implement a **Workspace Provider Interface** (Python Protocol) that abstracts
file workspace operations. Soliplex rooms interact only with this interface,
never with a specific backend directly.

### Phase 1: dufs backend (MVP)

- Validates the workspace concept with real users
- Minimal integration work (days, not weeks)
- dufs provides WebDAV + built-in web UI
- Auth handled by a thin proxy validating Soliplex JWTs

### Phase 2: OpenCloud backend (Production)

- Create an OpenCloud Project Space per Soliplex room
- Manage members via LibreGraph Graph API
- File ops via WebDAV
- Embed OpenCloud web UI via iframe with delegated authentication
- Shared Keycloak OIDC provider

### Why a facade?

1. **No lock-in.** If OpenCloud's fork dies (legal risk from Kiteworks), swap
   to another backend without changing Soliplex.
2. **Test-friendly.** Mock provider for unit tests — no external dependencies.
3. **Incremental.** Validate demand with dufs before committing to OpenCloud ops.
4. **Clean boundary.** Workspace concerns don't leak into room/agent logic.

## Consequences

### Positive

- Swap backends via YAML configuration
- Unit tests use mock provider (fast, deterministic)
- Integration tests target each provider independently
- Future providers (S3, custom) plug in without touching room code

### Negative

- Facade adds one layer of indirection
- Must maintain parity across provider implementations
- Some advanced features (e.g., OpenCloud embed mode) may not map cleanly to
  the generic interface — escape hatches needed

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| OpenCloud fork dies | Low-Medium | High | Facade enables swap in 1-2 weeks |
| Kiteworks lawsuit | Low | Medium | Apache-2.0 server license is clean |
| xattr metadata loss | Low | High | S3 backend driver (`s3ng`), rsync -aXS |
| AGPL web UI contamination | Low | Medium | iframe embed only, no modification |
| dufs limitations frustrate users | Medium | Low | Set expectations, upgrade to OpenCloud |

## References

- [Full analysis](/Users/runyaga/dev/soliplex-owncloud/ANALYSIS.md)
- [OpenCloud Graph API](https://docs.opencloud.eu/swagger/libre-graph-api/)
- [OpenCloud Embed Mode](https://docs.opencloud.eu/docs/next/dev/web/embed-mode/)
- [dufs](https://github.com/sigoden/dufs)
