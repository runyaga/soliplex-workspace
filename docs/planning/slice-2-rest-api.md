# Slice 2: REST API + API Integration Tests

## Goal

Create FastAPI REST endpoints for workspace file operations following
Soliplex conventions. Full API integration test suite using TestClient
with MockWorkspaceProvider.

## Files

| File | Description |
|------|-------------|
| `src/soliplex_workspace/api/__init__.py` | Package init |
| `src/soliplex_workspace/api/router.py` | FastAPI router with all endpoints |
| `src/soliplex_workspace/api/dependencies.py` | Provider dependency injection |
| `src/soliplex_workspace/api/models.py` | Pydantic request/response models |
| `src/soliplex_workspace/api/error_handlers.py` | Exception -> HTTPException mapping |
| `tests/integration/test_workspace_api.py` | 20 API tests via TestClient |

## Endpoints

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/v1/rooms/{room_id}/workspace` | 201 | Create workspace |
| GET | `/v1/rooms/{room_id}/workspace` | 200 | Get workspace info |
| DELETE | `/v1/rooms/{room_id}/workspace` | 204 | Delete workspace + files |
| GET | `/v1/rooms/{room_id}/workspace/files` | 200 | List files (`?path=/`) |
| GET | `/v1/rooms/{room_id}/workspace/files/info` | 200 | Stat file (`?path=`) |
| POST | `/v1/rooms/{room_id}/workspace/files/upload` | 201 | Upload (multipart) |
| GET | `/v1/rooms/{room_id}/workspace/files/download` | 200 | Download (streaming) |
| DELETE | `/v1/rooms/{room_id}/workspace/files` | 204 | Delete file/folder |
| POST | `/v1/rooms/{room_id}/workspace/folders` | 201 | Create folder |
| POST | `/v1/rooms/{room_id}/workspace/files/move` | 200 | Move/rename |

## Error Mapping

| Exception | HTTP | Detail |
|-----------|------|--------|
| WorkspaceNotFoundError | 404 | No workspace for room |
| WorkspaceAlreadyExistsError | 409 | Already exists |
| WorkspaceFileNotFoundError | 404 | File not found |
| DirectoryNotEmptyError | 409 | Not empty |
| InvalidPathError | 400 | Invalid path |
| QuotaExceededError | 413 | Quota exceeded |
| WorkspaceDisabledError | 503 | Feature disabled |

## API Test Cases (20)

1. create_workspace returns 201 + JSON
2. create_duplicate returns 409
3. get_workspace returns 200
4. get_nonexistent_workspace returns 404
5. delete_workspace returns 204
6. list_files_empty returns 200 + empty list
7. upload_file_multipart returns 201 + FileInfo
8. upload_missing_content returns 422
9. download_file returns bytes with content-type
10. download_nonexistent returns 404
11. delete_file returns 204
12. delete_nonexistent_file returns 404
13. create_folder returns 201 + is_directory
14. move_file returns 200 + new path
15. move_with_traversal returns 400
16. path_traversal_in_query returns 400
17. workspace_disabled returns 503
18. get_file_info returns 200
19. list_files_with_path_param
20. quota_exceeded returns 413

## Verification

1. `uv run ruff check && uv run ruff format --check`
2. `uv run pyright` -- 0 errors
3. `uv run pytest` -- 100% unit coverage

## AI Review Gate

- **Gemini** (`gemini-3.1-pro-preview`): REST API design, input validation,
  OpenAPI schema quality
- **Codex** (`read-only`): Input sanitization, auth enforcement, file
  upload limits
