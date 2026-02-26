# TODO

## Blocking: Ollama content:null

pydantic-ai `OpenAIChatModel._into_message_param()` sets `content: null`
on assistant messages that contain only tool calls (no text). Ollama rejects
this with `"invalid message content type: <nil>"`, crashing multi-turn tool
conversations.

**Fix:** Subclass `OpenAIChatModel`, override `_into_message_param` to emit
`content: ""` instead of `None`. Code was written and tested but reverted from
the workspace PR to keep it scoped. Needs a separate `fix/ollama-content-null`
branch on soliplex.

**Location:** `soliplex/agents.py` — replace `OpenAIChatModel` with the
subclass for the `OLLAMA` provider type.

## P0: URL-encoded filenames

`dufs.py:list_files` (~line 194) parses WebDAV `href` elements but does not
call `urllib.parse.unquote()`. Files with spaces show up as `my%20file.txt`
and subsequent reads/writes double-encode to `my%2520file.txt` causing 404s.

**Fix:** `rel = urllib.parse.unquote(urllib.parse.urlparse(entry.href).path)`

## P1: Race condition in \_ensure\_workspace

`bridge.py:_ensure_workspace` uses a `_workspace_ensured` flag per bound tool.
When the LLM invokes multiple tools in parallel and the workspace does not
exist yet, all concurrent calls pass the `if not _workspace_ensured` check
and try to create the workspace simultaneously. The losers get
`WorkspaceAlreadyExistsError`.

**Fix:** Catch `WorkspaceAlreadyExistsError` inside `_ensure_workspace`, or
use an `asyncio.Lock`.

## P1: OOM on large file download

`workspace_read` and `workspace_copy` download the entire file into RAM before
truncating. A 5 GB file will crash the process.

**Fix:** Add a `HEAD`/`get_file_info` size check before `download_file`, or
implement streaming reads in the provider.

## P2: Agent cache ignores room\_id

`agents.py:get_agent_from_configs` caches agents by `agent_config.id`. If two
rooms share the same agent config but have different workspace tool bindings
(different `room_id`), the second room gets the first room's tools.

**Fix:** Include `room_id` in the cache key when `extra_tools` are provided,
or skip caching for workspace-enabled agents.

## P2: REST API not mounted

`mount_workspace_api()` from `soliplex_workspace.api.integration` is never
called during application startup. The workspace only works via LLM tools;
no REST endpoint exists for a UI file browser.

## P2: No provider teardown

`DufsWorkspaceProvider` holds an `httpx.AsyncClient` that is never closed on
shutdown. Add `await provider.close()` to the soliplex lifespan.

## Future slices

- **Slice 5:** OpenCloud backend (Graph API + WebDAV, production)
- **Slice 6:** Ephemeral per-chat workspaces (TTL, reaper, promotion)
- **Slice 7:** Vector search over file contents
