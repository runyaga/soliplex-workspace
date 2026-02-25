"""Bridge: bind workspace tools to a provider + room for LLM agents.

``make_workspace_tools()`` returns a list of async callables with
signatures suitable for pydantic-ai (or any framework that introspects
``__signature__`` and ``__doc__``).  No pydantic-ai dependency here.
"""

from __future__ import annotations

import functools
import inspect
import logging
from collections.abc import Callable
from typing import Any

from soliplex_workspace.tools import core

logger = logging.getLogger(__name__)

_TOOL_FUNCTIONS = [
    core.workspace_list,
    core.workspace_read,
    core.workspace_write,
    core.workspace_info,
    core.workspace_search,
    core.workspace_mkdir,
    core.workspace_move,
    core.workspace_delete,
    core.workspace_copy,
]

_BOUND_PARAMS = frozenset(("provider", "room_id"))


async def _ensure_workspace(provider: Any, room_id: str) -> None:
    """Create workspace lazily if it doesn't exist yet."""
    ws = await provider.get_workspace(room_id)
    if ws is None:
        logger.info("auto-creating workspace for room=%s", room_id)
        await provider.create_workspace(room_id, room_id)


def make_workspace_tools(
    provider: Any,
    room_id: str,
    *,
    auto_create: bool = True,
) -> list[Callable[..., Any]]:
    """Create bound workspace tool callables for an LLM agent.

    Each returned callable has the same ``__doc__``,
    ``__annotations__``, and ``__signature__`` as the original tool,
    minus the ``provider`` and ``room_id`` parameters.  This allows
    pydantic-ai (or any framework) to introspect parameter schemas
    and generate tool descriptions.

    If *auto_create* is True (default), the workspace is lazily
    created on the first tool call if it doesn't already exist.
    """
    return [
        _bind_tool(func, provider, room_id, auto_create=auto_create)
        for func in _TOOL_FUNCTIONS
    ]


def _bind_tool(
    func: Callable[..., Any],
    provider: Any,
    room_id: str,
    *,
    auto_create: bool = True,
) -> Callable[..., Any]:
    """Bind provider and room_id, preserving signature."""
    orig_sig = inspect.signature(func)
    new_params = [
        p for p in orig_sig.parameters.values() if p.name not in _BOUND_PARAMS
    ]
    new_sig = orig_sig.replace(parameters=new_params)

    # Strip bound-param annotations; leave the rest as strings.
    # Frameworks resolve them via __module__ + sys.modules.
    new_annotations = {
        k: v for k, v in func.__annotations__.items() if k not in _BOUND_PARAMS
    }

    _workspace_ensured = False

    @functools.wraps(func)
    async def bound_tool(**kwargs: Any) -> Any:
        nonlocal _workspace_ensured
        if auto_create and not _workspace_ensured:
            await _ensure_workspace(provider, room_id)
            _workspace_ensured = True
        logger.debug(
            "tool call %s room=%s kwargs=%s", func.__name__, room_id, kwargs
        )
        result = await func(provider=provider, room_id=room_id, **kwargs)
        logger.debug("tool done %s room=%s", func.__name__, room_id)
        return result

    bound_tool.__signature__ = new_sig  # type: ignore[attr-defined]
    bound_tool.__annotations__ = new_annotations
    return bound_tool
