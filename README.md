# soliplex-workspace

Persistent file workspace provider for Soliplex rooms.

## Overview

Provides a `WorkspaceProvider` facade with swappable backends:

- **MockWorkspaceProvider** -- in-memory (for tests)
- **DisabledWorkspaceProvider** -- no-op (feature off)
- **DufsWorkspaceProvider** -- dufs WebDAV backend (MVP)
- **OpenCloudWorkspaceProvider** -- OpenCloud Graph API + WebDAV (production)

## Development

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e . --group dev
pre-commit install
pytest
```

## Architecture

See [ADR-0001](docs/adr/0001-workspace-provider-facade.md) and
[current plan](docs/planning/current-plan.md).
