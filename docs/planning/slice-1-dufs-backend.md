# Slice 1: dufs Backend + Integration Test Infrastructure

## Goal

Implement `DufsWorkspaceProvider` backed by a real dufs WebDAV server,
extract shared path validation utility, create Docker-based integration
test infrastructure.

## Files

| File | Description |
|------|-------------|
| `src/soliplex_workspace/utils.py` | Shared `normalize_path()` extracted from mock |
| `src/soliplex_workspace/providers/dufs.py` | WebDAV-based provider using httpx |
| `docker-compose.test.yml` | dufs service for integration tests |
| `tests/integration/conftest.py` | Fixtures: `requires_dufs`, `dufs_provider`, `dufs_workspace` |
| `tests/integration/test_dufs_provider.py` | 20 integration tests (all `@requires_dufs`) |
| `tests/unit/test_dufs_provider.py` | Unit tests with respx HTTP mocking |

## DufsWorkspaceProvider Design

- Room isolation: each room = `/rooms/{room_id}/` subdirectory on dufs
- WebDAV verbs: PUT (upload), GET (download), DELETE, MKCOL (mkdir),
  MOVE, PROPFIND (list/stat)
- XML parsing: `xml.etree.ElementTree` for PROPFIND responses
- Content-type detection: extension-based mapping
- Error mapping: HTTP 404 -> `WorkspaceFileNotFoundError`,
  409 -> `DirectoryNotEmptyError`, 507 -> `QuotaExceededError`

## Integration Test Cases (20)

1. create_workspace creates directory on dufs
2. upload_and_download roundtrip (byte-for-byte)
3. upload_large_file (10MB)
4. list_files_after_upload
5. list_files_in_subfolder
6. delete_file removes from dufs
7. create_folder via MKCOL
8. move_file via MOVE verb
9. move_directory with children
10. get_file_info returns correct metadata
11. cross_room_isolation
12. delete_workspace_removes_all
13. delete_nonempty_dir_raises
14. path_traversal_rejected
15. download_nonexistent_raises
16. content_type_detection
17. special_characters_in_filename
18. overwrite_existing_file
19. get_webdav_url returns valid URL
20. concurrent_uploads (asyncio.gather 10 files)

## Verification

1. `uv run ruff check && uv run ruff format --check`
2. `uv run pyright` -- 0 errors
3. `uv run pytest` -- 100% unit coverage
4. `docker compose -f docker-compose.test.yml up -d --wait`
5. `uv run pytest tests/integration/ -m dufs -v`
6. `docker compose -f docker-compose.test.yml down -v`

## AI Review Gate

- **Gemini** (`gemini-3.1-pro-preview`): WebDAV correctness, path traversal,
  httpx lifecycle, room isolation, Docker healthcheck
- **Codex** (`read-only`): Security review -- room isolation, error recovery,
  path traversal
