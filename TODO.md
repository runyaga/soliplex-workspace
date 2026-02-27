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
subclass for the `OLLAMA` provider type. The `_into_message_param` method
docstring explicitly says it is a hook for subclasses.

## P0: URL-encoded filenames

`dufs.py:list_files` (~line 194) parses WebDAV `href` elements but does not
call `urllib.parse.unquote()`. Files with spaces show up as `my%20file.txt`
and subsequent reads/writes double-encode to `my%2520file.txt` causing 404s.

**Fix:** `rel = urllib.parse.unquote(urllib.parse.urlparse(entry.href).path)`

## P1: Race condition in \_ensure\_workspace

`bridge.py:_ensure_workspace` uses a `_workspace_ensured` flag per bound tool
closure. Each tool created by `make_workspace_tools` gets its own independent
flag. When the LLM invokes multiple tools in parallel and the workspace does
not exist yet, all concurrent calls pass the `if not _workspace_ensured` check
and try to create the workspace simultaneously. The losers get
`WorkspaceAlreadyExistsError`.

**Fix:** Catch `WorkspaceAlreadyExistsError` inside `_ensure_workspace` (EAFP
pattern). An `asyncio.Lock` would also work but is heavier than needed since
workspace creation is idempotent.

## P1: OOM on large file download

`workspace_read` and `workspace_copy` download the entire file into RAM before
truncating. A 5 GB file will crash the process.

**Fix for `workspace_read`:** Call `get_file_info()` before `download_file()`
and raise a graceful error if `size_bytes > max_bytes`. This prevents the
download entirely.

**Fix for `workspace_copy`:** Accept as-is for MVP. A full fix requires
streaming support in the provider protocol (`aiter_bytes`), which is a larger
change.

## P2: Use RunContext/deps instead of extra\_tools

`agents.py:get_agent_from_configs` caches agents by `agent_config.id`. If two
rooms share the same agent config but have different workspace tool bindings
(different `room_id`), the second room gets the first room's tools.

The current approach uses `extra_tools` (closures bound to a specific
`room_id`) injected at agent creation time. This conflicts with agent caching.

**Idiomatic fix:** Use pydantic-ai `RunContext[AgentDependencies]` instead.
Soliplex already uses this pattern for other tools (see `soliplex/tools.py`).
The workspace tools should accept `ctx: RunContext[AgentDependencies]` and
read `ctx.deps.workspace_provider` and `ctx.deps.room_id` at call time.
This lets a single cached agent serve multiple rooms, with room-specific
context injected per-run through `deps`.

Requires:

- Add `room_id` to `AgentDependencies`
- Rewrite workspace tool signatures to use `RunContext`
- Remove `extra_tools` / closure-based binding from `bridge.py`

## P2: Mount REST API and provider teardown

`mount_workspace_api()` from `soliplex_workspace.api.integration` is never
called during application startup. The workspace only works via LLM tools;
no REST endpoint exists for a UI file browser.

`mount_workspace_api()` already registers provider teardown via
`app.router.on_shutdown.append(_close_provider)`. Mounting the API also
solves the `httpx.AsyncClient` leak on shutdown.

**Fix:** Call `mount_workspace_api(app, provider)` in soliplex's lifespan
or main app setup.

## Future slices

- **Slice 5:** OpenCloud backend (Graph API + WebDAV, production)
- **Slice 6:** Ephemeral per-chat workspaces (TTL, reaper, promotion)
- **Slice 7:** Vector search over file contents
