# Slice 0: Project Setup + Provider Interface

**Branch:** `feat/workspace-provider/slice-0`
**PR:** `feat/workspace-provider/slice-0` -> `main`

---

## Goal

Establish the project with strict tooling (pre-commit, ruff, pytest, gitleaks),
define the `WorkspaceProvider` Protocol, and implement mock + disabled providers
for testing and backward compatibility.

## Deliverable

A fully configured Python package with the workspace abstraction layer. Other
slices build providers on top of this interface. The mock provider enables all
downstream unit tests to run without external dependencies.

---

## Implementation

### 1. Project scaffolding

**Files:**

- `pyproject.toml` -- package metadata, dependencies, ruff/pytest config
- `.pre-commit-config.yaml` -- ruff, gitleaks, yaml/toml checks, no-commit-to-branch
- `.gitleaks.toml` -- secret scanning allowlist
- `.gitignore` -- Python standard ignores
- `src/soliplex_workspace/__init__.py` -- package init
- `tests/conftest.py` -- shared fixtures

### 2. Provider Protocol

**File:** `src/soliplex_workspace/protocol.py`

```python
from typing import Protocol

class WorkspaceProvider(Protocol):
    async def create_workspace(
        self, room_id: str, name: str, quota_bytes: int | None = None
    ) -> WorkspaceInfo: ...

    async def delete_workspace(self, room_id: str) -> None: ...

    async def get_workspace(self, room_id: str) -> WorkspaceInfo | None: ...

    async def list_files(
        self, room_id: str, path: str = "/"
    ) -> list[FileInfo]: ...

    async def upload_file(
        self, room_id: str, path: str, content: bytes
    ) -> FileInfo: ...

    async def download_file(
        self, room_id: str, path: str
    ) -> bytes: ...

    async def delete_file(self, room_id: str, path: str) -> None: ...

    async def create_folder(
        self, room_id: str, path: str
    ) -> FileInfo: ...

    async def move(
        self, room_id: str, src: str, dst: str
    ) -> FileInfo: ...

    async def get_web_ui_url(self, room_id: str) -> str | None: ...

    async def get_webdav_url(self, room_id: str) -> str | None: ...
```

### 3. Data models

**File:** `src/soliplex_workspace/models.py`

| Model | Fields |
|-------|--------|
| `WorkspaceInfo` | `room_id`, `name`, `quota_bytes`, `used_bytes`, `web_ui_url`, `webdav_url`, `created_at` |
| `FileInfo` | `name`, `path`, `size_bytes`, `content_type`, `is_directory`, `modified_at`, `etag` |

### 4. Mock provider

**File:** `src/soliplex_workspace/providers/mock.py`

In-memory dict-of-dicts implementation. Keys: `room_id -> path -> bytes`.
Supports all `WorkspaceProvider` operations. Used in all unit tests.

### 5. Disabled provider

**File:** `src/soliplex_workspace/providers/disabled.py`

All methods raise `WorkspaceDisabledError`. Used when workspace feature is
turned off in Soliplex configuration.

---

## Files Changed

| File | Change |
|------|--------|
| `pyproject.toml` | New -- package config |
| `.pre-commit-config.yaml` | New -- pre-commit hooks |
| `.gitleaks.toml` | New -- secret scanning config |
| `.gitignore` | New -- ignore patterns |
| `src/soliplex_workspace/__init__.py` | New -- package exports |
| `src/soliplex_workspace/protocol.py` | New -- WorkspaceProvider Protocol |
| `src/soliplex_workspace/models.py` | New -- WorkspaceInfo, FileInfo |
| `src/soliplex_workspace/exceptions.py` | New -- WorkspaceDisabledError, etc. |
| `src/soliplex_workspace/providers/__init__.py` | New |
| `src/soliplex_workspace/providers/mock.py` | New -- MockWorkspaceProvider |
| `src/soliplex_workspace/providers/disabled.py` | New -- DisabledWorkspaceProvider |
| `tests/conftest.py` | New -- shared fixtures |
| `tests/unit/test_protocol.py` | New -- protocol compliance tests |
| `tests/unit/test_mock_provider.py` | New -- mock provider tests |
| `tests/unit/test_disabled_provider.py` | New -- disabled provider tests |
| `tests/unit/test_models.py` | New -- data model tests |
| `docs/adr/0001-workspace-provider-facade.md` | New -- ADR |

---

## Testing

All tests in this slice are **pure Python unit tests**. They run with `pytest`
(no network, no Docker, no external services).

### Autonomous test commands

```bash
# Run all tests with coverage
pytest

# Run only slice-0 tests
pytest tests/unit/test_protocol.py tests/unit/test_mock_provider.py tests/unit/test_disabled_provider.py tests/unit/test_models.py

# Lint + format
ruff check && ruff format --check

# Pre-commit
pre-commit run --all-files
```

### Test cases: MockWorkspaceProvider

| # | Test | Action | Assert |
|---|------|--------|--------|
| 1 | Create workspace | `create_workspace("room-1", "Test")` | Returns `WorkspaceInfo` with `room_id="room-1"` |
| 2 | Get workspace | After create | Returns same `WorkspaceInfo` |
| 3 | Get nonexistent | `get_workspace("nope")` | Returns `None` |
| 4 | Upload file | `upload_file("room-1", "/doc.pdf", b"...")` | Returns `FileInfo(name="doc.pdf")` |
| 5 | List files | After upload | Contains `doc.pdf` |
| 6 | Download file | `download_file("room-1", "/doc.pdf")` | Returns original bytes |
| 7 | Delete file | `delete_file("room-1", "/doc.pdf")` | `list_files` returns empty |
| 8 | Create folder | `create_folder("room-1", "/notes")` | `FileInfo(is_directory=True)` |
| 9 | Move file | Upload then `move("room-1", "/a.txt", "/b.txt")` | Old path gone, new path exists |
| 10 | Delete workspace | `delete_workspace("room-1")` | `get_workspace` returns `None` |
| 11 | Cross-room isolation | Upload to room-1, list room-2 | Room-2 list is empty |

### Test cases: DisabledWorkspaceProvider

| # | Test | Action | Assert |
|---|------|--------|--------|
| 1 | Create raises | `create_workspace(...)` | Raises `WorkspaceDisabledError` |
| 2 | List raises | `list_files(...)` | Raises `WorkspaceDisabledError` |
| 3 | Upload raises | `upload_file(...)` | Raises `WorkspaceDisabledError` |
| 4 | All methods raise | Every method | Raises `WorkspaceDisabledError` |

---

## Acceptance Criteria

- [ ] `ruff check` -- 0 issues
- [ ] `ruff format --check` -- no changes
- [ ] `pre-commit run --all-files` -- all hooks pass
- [ ] `pytest` -- all pass, >= 100% coverage
- [ ] `WorkspaceProvider` Protocol is fully typed (no `Any`)
- [ ] `MockWorkspaceProvider` passes all 11 test cases
- [ ] `DisabledWorkspaceProvider` raises on every method
- [ ] ADR-0001 committed and reviewed
- [ ] Package installs cleanly: `pip install -e .`

---

## Review Gate

After implementation, before merging:

1. **Gemini `read_files`** (`gemini-3.1-pro-preview`) of `protocol.py` and
   `models.py` -- interface completeness, typing best practices, missing edge
   cases in the protocol design
2. Review feedback addressed before moving to Slice 1
