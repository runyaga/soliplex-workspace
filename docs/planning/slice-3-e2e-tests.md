# Slice 3: E2E Tests Through Soliplex

## Goal

End-to-end tests that exercise the full stack: HTTP request -> FastAPI
router -> DufsWorkspaceProvider -> real dufs server. Validates the
complete integration works as a user would experience it.

## Files

| File | Description |
|------|-------------|
| `src/soliplex_workspace/api/integration.py` | Factory + mount helper |
| `tests/e2e/__init__.py` | Package init |
| `tests/e2e/conftest.py` | E2E fixtures: `e2e_client` |
| `tests/e2e/test_workspace_e2e.py` | 14 E2E tests |
| `scripts/run-integration-tests.sh` | Docker up, pytest, docker down |
| `scripts/run-all-tests.sh` | Unit + integration + E2E |

## Integration Bridge

`create_workspace_provider(config)` factory:

- `backend: "mock"` -> MockWorkspaceProvider
- `backend: "dufs"` -> DufsWorkspaceProvider(dufs_url)
- `backend: "disabled"` -> DisabledWorkspaceProvider

`mount_workspace_api(app, provider)` wires provider + routes + error
handlers into any FastAPI app.

## E2E Test Cases (14)

All marked `@pytest.mark.dufs` and `@pytest.mark.e2e`:

1. full_lifecycle (create -> upload -> list -> download -> delete -> destroy)
2. upload_download_roundtrip_pdf (real PDF bytes, byte-for-byte)
3. upload_download_roundtrip_image (PNG)
4. folder_operations (create -> upload into -> list -> move out -> delete)
5. move_across_folders
6. overwrite_semantics (upload same path twice, verify latest)
7. cross_room_isolation_via_api (2 rooms, files don't leak)
8. error_responses_are_json (trigger 404/400, verify JSON detail)
9. path_traversal_blocked_e2e (attempt ../ via API, verify 400)
10. concurrent_uploads_via_api (5 rapid uploads, all persisted)
11. delete_workspace_cleans_dufs (files actually gone on disk)
12. large_file_upload_download (5MB, verify integrity)
13. special_filenames_via_api (spaces, unicode chars)
14. workspace_info_after_operations (verify state changes)

## Test Runner Scripts

### `scripts/run-integration-tests.sh`

```bash
docker compose -f docker-compose.test.yml up -d --wait
uv run pytest tests/integration/ -m dufs -v --no-cov
docker compose -f docker-compose.test.yml down -v
```

### `scripts/run-all-tests.sh`

```bash
uv run pytest tests/unit/ -v                              # unit
docker compose -f docker-compose.test.yml up -d --wait
uv run pytest tests/integration/ -m dufs -v --no-cov     # integration
uv run pytest tests/e2e/ -m dufs -v --no-cov             # e2e
docker compose -f docker-compose.test.yml down -v
```

## Verification

1. `uv run ruff check && uv run ruff format --check`
2. `uv run pyright` -- 0 errors
3. `uv run pytest` -- 100% unit coverage
4. `docker compose -f docker-compose.test.yml up -d --wait`
5. `uv run pytest tests/integration/ -m dufs -v`
6. `uv run pytest tests/e2e/ -m dufs -v`
7. `docker compose -f docker-compose.test.yml down -v`

## AI Review Gate

- **Gemini** (`gemini-3.1-pro-preview`): E2E test completeness, integration
  patterns, fixture cleanup correctness
- **Codex** (`read-only`): E2E security scenarios, cleanup reliability,
  race conditions in concurrent tests
