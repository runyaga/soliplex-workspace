# Slice 3.5: LLM Workspace Tools

## Context

Slices 0-3 are complete: `WorkspaceProvider` protocol, `DufsWorkspaceProvider`,
REST API, full test pyramid (166 tests, all passing against real dufs). AI
review gates passed.

**The need:** The provider has basic CRUD but lacks the higher-level operations
that LLM agents need — recursive directory walking, text file reading/writing,
file search. Without these, an LLM can't effectively explore or manipulate a
room's workspace.

**This slice** adds three provider-level enhancements and eight LLM tool
functions that compose them, enabling Soliplex agents to read, write, search,
and organize workspace files.

---

## Architecture Decision: No pydantic-ai Dependency

Tool functions are **plain async functions** taking `(provider, room_id, ...params)`.
They return `dict` (JSON-serializable), not dataclasses. This keeps
`soliplex-workspace` reusable as a standalone library.

Soliplex integrates via its existing `ToolConfig` mechanism: a thin wrapper
binds `provider` and `room_id` from `ctx.deps`, exposing only LLM-facing
params. This integration is documented but out of scope for this slice.

---

## Step 1: Provider Enhancements

Add 3 new methods to the protocol and all providers.

### Files Modified

| File | Change |
|------|--------|
| `src/soliplex_workspace/protocol.py` | Add 3 protocol methods |
| `src/soliplex_workspace/providers/dufs.py` | Implement 3 methods |
| `src/soliplex_workspace/providers/mock.py` | Implement 3 methods |
| `src/soliplex_workspace/providers/disabled.py` | Raise `WorkspaceDisabledError` |

### 1a. `list_files_recursive`

```python
async def list_files_recursive(
    self, room_id: str, path: str = "/", max_depth: int = 10,
) -> list[FileInfo]:
```

- **Dufs**: Iterative BFS using existing `list_files()` (Depth=1). Collect
  directories into a queue, process each up to `max_depth`. Sorted by path.
- **Mock**: Filter `self._files` and `self._dirs` by path prefix. Trivial.
- Avoids PROPFIND `Depth=infinity` (dufs may not support it; BFS is safe).

### 1b. `read_text`

```python
async def read_text(
    self, room_id: str, path: str, encoding: str = "utf-8",
) -> str:
```

Delegates to `download_file()` then `.decode(encoding)`. Raises
`WorkspaceFileNotFoundError` on missing file; propagates `UnicodeDecodeError`
on binary files.

### 1c. `write_text`

```python
async def write_text(
    self, room_id: str, path: str, content: str, encoding: str = "utf-8",
) -> FileInfo:
```

Delegates to `upload_file(room_id, path, content.encode(encoding))`.

---

## Step 2: LLM Tool Functions

All tools live in `src/soliplex_workspace/tools/core.py`. Each returns a `dict`.
Errors are caught and returned as `{"error": "..."}` dicts.

### Files Created

| File | Purpose |
|------|---------|
| `src/soliplex_workspace/tools/__init__.py` | Public exports |
| `src/soliplex_workspace/tools/core.py` | 8 tool implementations |

### Helper

```python
def _file_to_dict(info: FileInfo) -> dict:
    """Convert FileInfo to JSON-serializable dict."""
```

### Tool Signatures

#### `workspace_list(provider, room_id, path="/", recursive=False, max_depth=10) -> dict`

> List files and folders in the workspace. Set recursive=True for full tree.

Returns: `{"path": str, "files": [...]}`

#### `workspace_read(provider, room_id, path, encoding="utf-8") -> dict`

> Read a text file's contents. Works with code, markdown, CSV, JSON, etc.

Returns: `{"path": str, "content": str, "size_bytes": int}`
On binary: `{"error": "File appears to be binary..."}`

#### `workspace_write(provider, room_id, path, content, encoding="utf-8") -> dict`

> Write or create a text file. Overwrites if exists.

Returns: `{"path": str, "name": str, "size_bytes": int}`

#### `workspace_info(provider, room_id, path) -> dict`

> Get metadata about a file or folder (size, type, modified date).

Returns: `{"name", "path", "size_bytes", "content_type", "is_directory", "modified_at", "etag"}`

#### `workspace_search(provider, room_id, pattern, path="/") -> dict`

> Search for files by name pattern (glob). Searches recursively.

Uses `fnmatch.fnmatch()` against `list_files_recursive()` results.
Returns: `{"pattern": str, "matches": [...], "total": int}`

#### `workspace_mkdir(provider, room_id, path) -> dict`

> Create a directory.

Returns: `{"path": str, "name": str, "is_directory": true}`

#### `workspace_move(provider, room_id, src, dst) -> dict`

> Move or rename a file or folder.

Returns: `{"src": str, "dst": str, "name": str}`

#### `workspace_delete(provider, room_id, path) -> dict`

> Delete a file or folder. Cannot be undone.

Returns: `{"deleted": str, "ok": true}`

---

## Step 3: Tests

### Files Created

| File | Purpose |
|------|---------|
| `tests/unit/test_tools.py` | ~35 tests for all 8 tools (MockWorkspaceProvider) |
| `tests/integration/test_tools_dufs.py` | ~8 integration tests against real dufs |

### Files Modified

| File | Change |
|------|--------|
| `tests/unit/test_mock_provider.py` | Tests for `list_files_recursive`, `read_text`, `write_text` |
| `tests/unit/test_dufs_provider.py` | Tests for 3 new methods (respx mocks) |
| `tests/unit/test_disabled_provider.py` | Tests for 3 new methods |
| `tests/unit/test_protocol.py` | Verify protocol compliance still holds |

### Unit Test Classes (test_tools.py)

```text
TestWorkspaceList       — root, subdirectory, recursive, max_depth, empty, error
TestWorkspaceRead       — text file, nonexistent→error, binary→error, custom encoding
TestWorkspaceWrite      — new file, overwrite, metadata, nonexistent workspace→error
TestWorkspaceInfo       — file, directory, nonexistent→error
TestWorkspaceSearch     — by extension, by prefix, no matches, subdirectory, glob
TestWorkspaceMkdir      — create, nested
TestWorkspaceMove       — file, directory, nonexistent→error
TestWorkspaceDelete     — file, folder, nonexistent→error
TestReturnTypes         — all tools return dicts, errors return dicts
```

### Integration Tests (test_tools_dufs.py)

```text
test_list_recursive_real         — create nested dirs, verify full tree
test_read_write_cycle            — write text → read back → verify content
test_search_real                 — upload mixed files → search by pattern
test_full_use_case_synthesis     — simulate UC1 (research synthesis) end-to-end
```

---

## Seven Use Cases

### UC1: Research Synthesis

> "Summarize all the meeting notes in my workspace."

```python
workspace_search(pattern="*.md", path="/research")
workspace_read(path="/research/paper1.md")   # repeat for each match
→ LLM synthesizes findings
workspace_write(path="/research/synthesis.md", content="# Synthesis\n...")
```

**Tools:** search, read, write

### UC2: Project Scaffolding

> "Set up a Python project structure with src/, tests/, README, pyproject.toml."

```python
workspace_mkdir(path="/myproject/src/mypackage")
workspace_mkdir(path="/myproject/tests")
workspace_write(path="/myproject/src/mypackage/__init__.py", content='"""..."""')
workspace_write(path="/myproject/README.md", content="# My Project\n...")
workspace_write(path="/myproject/pyproject.toml", content="[project]...")
workspace_list(path="/myproject", recursive=True)   # verify structure
```

**Tools:** mkdir, write, list(recursive)

### UC3: Data Analysis Report

> "Read the CSV data and write a summary report."

```python
workspace_list(path="/data")
workspace_read(path="/data/sales_2024.csv")
→ LLM analyzes CSV content
workspace_write(path="/reports/sales_analysis.md", content="# Analysis\n...")
workspace_info(path="/reports/sales_analysis.md")   # confirm saved
```

**Tools:** list, read, write, info

### UC4: File Organization

> "My workspace is messy. Organize files into folders by type."

```python
workspace_list(path="/", recursive=True)
→ LLM categorizes by extension
workspace_mkdir(path="/documents")
workspace_mkdir(path="/images")
workspace_move(src="/readme.md", dst="/documents/readme.md")
workspace_move(src="/logo.png", dst="/images/logo.png")
workspace_list(path="/", recursive=True)   # verify new layout
```

**Tools:** list(recursive), mkdir, move

### UC5: Code Documentation

> "Find all Python files and generate API docs for them."

```python
workspace_search(pattern="*.py", path="/src")
workspace_read(path="/src/main.py")    # repeat for each match
→ LLM generates documentation
workspace_mkdir(path="/docs")
workspace_write(path="/docs/api_reference.md", content="# API Ref\n...")
```

**Tools:** search, read, mkdir, write

### UC6: Workspace Cleanup / Audit

> "Audit my workspace. What are the largest files? Anything I should delete?"

```python
workspace_list(path="/", recursive=True)
workspace_info(path="/old_backup.tar.gz")   # detailed check
workspace_info(path="/data/archive_2020.csv")
→ LLM presents size report + recommendations
workspace_delete(path="/old_backup.tar.gz")   # user confirms
```

**Tools:** list(recursive), info, delete

### UC7: Template Population

> "Use the meeting template and fill it in with today's standup notes."

```python
workspace_search(pattern="*template*")
workspace_read(path="/templates/meeting_template.md")
→ LLM fills in template with user-provided details
workspace_write(path="/meetings/2025-02-24-standup.md", content="# Standup...")
workspace_info(path="/meetings/2025-02-24-standup.md")   # confirm
```

**Tools:** search, read, write, info

### Tool Coverage Matrix

| Tool | UC1 | UC2 | UC3 | UC4 | UC5 | UC6 | UC7 |
|------|-----|-----|-----|-----|-----|-----|-----|
| workspace_list | | x | x | x | | x | |
| workspace_read | x | | x | | x | | x |
| workspace_write | x | x | x | | x | | x |
| workspace_info | | | x | | | x | x |
| workspace_search | x | | | | x | | x |
| workspace_mkdir | | x | | x | x | | |
| workspace_move | | | | x | | | |
| workspace_delete | | | | | | x | |

**All 8 tools exercised.** Each appears in 1-4 use cases.

---

## Gap Analysis: Capabilities Left Unexercised

After the 7 use cases and 8 tools, these capabilities remain missing or unexercised:

| # | Gap | Why It Matters | Severity |
|---|-----|---------------|----------|
| 1 | **Content search (grep within files)** | LLM can only search by filename, not by content. Finding "all files mentioning 'deadline'" requires reading every file. | **Medium** — partially mitigated by read + LLM reasoning |
| 2 | **Binary file operations** | Images, PDFs, audio can be listed/moved/deleted but not read or processed. No text extraction from PDF/DOCX. | **Medium** — workspace_info describes them; extraction needs external tooling |
| 3 | **Streaming / chunked reads** | Files >10MB load fully into memory. No range requests or partial reads. | **Low** — most workspace text files are small |
| 4 | **Cross-room operations** | Can't copy/move files between rooms. Protocol is room-scoped by design. | **Low** — intentional isolation boundary |
| 5 | **Version history / undo** | No file versioning in dufs. Overwrites are destructive. | **Low** — OpenCloud (Slice 4+) adds versioning |
| 6 | **File copy** | No dedicated copy operation. Requires download + re-upload. | **Low** — easy to add as a convenience tool later |
| 7 | **Collaborative locking** | No file locks or conflict detection. Last-write-wins. | **Low** — single LLM per room makes conflicts unlikely |
| 8 | **Format conversion** | No PDF→text, DOCX→markdown, etc. | **Low** — outside workspace scope, needs external libs |
| 9 | **File append** | No append mode; must read-concat-write entire file. | **Low** — acceptable for text files |
| 10 | **Quota awareness** | Tools don't check available space before large writes. | **Low** — QuotaExceededError propagates naturally |

**Highest-impact gaps** for future work: content search (#1) and binary text
extraction (#2). Both could be added as additional tools in a later slice.

---

## Verification

```bash
# Lint
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Type check
uv run pyright

# Unit tests with coverage (target: 99%+)
uv run pytest tests/unit/ -v

# Integration tests (requires dufs at localhost:5001)
uv run pytest tests/integration/test_tools_dufs.py -m dufs -v --no-cov

# Protocol compliance
uv run pytest tests/unit/test_protocol.py -v

# Verify no pydantic-ai imports in tools module
grep -r "pydantic_ai" src/soliplex_workspace/tools/ && echo "FAIL" || echo "OK"

# Full suite
uv run pytest tests/ -v --no-cov
```

---

## AI Review Gate

### Gemini Review

```yaml
mcp__gemini__read_files:
  files: protocol.py, tools/core.py, providers/mock.py, providers/dufs.py, test_tools.py
  prompt: "Review Slice 3.5: LLM Workspace Tools. Check:
    1. Tool signatures — LLM-friendly? Clear docstrings?
    2. Return types — all dicts, JSON-serializable?
    3. Error handling — WorkspaceError caught → error dicts?
    4. list_files_recursive — BFS correct? max_depth? No infinite loops?
    5. workspace_search — fnmatch correctness, case sensitivity
    6. read_text/write_text — encoding edge cases
    7. Security — can tools bypass path validation? Pattern injection?
    8. Protocol compliance — new methods break runtime_checkable?"
  model: gemini-3.1-pro-preview
```

### Codex Review

```yaml
mcp__codex__codex:
  prompt: "Security review of LLM workspace tools. Focus on:
    1. Can LLM craft paths escaping room isolation?
    2. Can glob patterns in search cause ReDoS or path injection?
    3. Is max_depth in recursive listing enforced?
    4. Are error messages safe (no internal paths leaked)?
    5. Can tools compose to escalate permissions?"
  sandbox: read-only
```

---

## Pass Criteria

- All new provider methods implemented and tested
- All 8 tool functions return dicts (never dataclasses)
- ~45 new tests, all passing
- 0 skipped integration tests against real dufs
- ruff clean, pyright clean, coverage ≥99%
- No pydantic-ai dependency in `src/soliplex_workspace/tools/`
- AI review gate: 0 Critical/High unresolved
