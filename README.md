# soliplex-workspace

Persistent file workspace provider for Soliplex rooms.

## Overview

Provides a `WorkspaceProvider` facade with swappable backends:

- **MockWorkspaceProvider** -- in-memory (for tests)
- **DisabledWorkspaceProvider** -- no-op (feature off)
- **DufsWorkspaceProvider** -- dufs WebDAV backend (MVP)
- **OpenCloudWorkspaceProvider** -- OpenCloud Graph API + WebDAV (production)

## Installation

Add `soliplex-workspace` as an editable dependency in your Soliplex `pyproject.toml`:

```toml
[tool.uv.sources]
soliplex-workspace = { path = "../soliplex-owncloud/soliplex-workspace", editable = true }
```

Then sync:

```bash
cd ~/dev/soliplex && uv sync
```

Configure the workspace provider in `example/installation.yaml`:

```yaml
workspace:
  backend: dufs
  dufs_url: http://localhost:5001
```

Enable workspaces per room in `room_config.yaml`:

```yaml
workspace_enabled: true
```

## Running dufs

[dufs](https://github.com/sigoden/dufs) is a lightweight file server used as the MVP backend.

Install via Homebrew:

```bash
brew install dufs
```

Start the server:

```bash
dufs /tmp/dufs-test-data -A --enable-cors -p 5001
```

- `-A` allows all operations (upload, delete, mkdir, move)
- `--enable-cors` permits browser requests from the Soliplex UI
- `-p 5001` matches the `dufs_url` in `installation.yaml`

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
