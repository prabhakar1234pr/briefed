"""
LangSmith tracing for v2 LLM observability.

Initializes LangSmith env vars based on Briefed settings, exposes a `traced`
decorator that's a no-op when LangSmith isn't configured, and a `tag_run()`
helper for attaching meeting_id / agent_id to active runs.

Usage:
    from app.tracing import traced, tag_run

    @traced(name="answer_question_streaming", run_type="llm")
    async def answer_question_streaming(question, ...):
        tag_run(meeting_id=meeting_id, agent_id=agent_id)
        ...

When `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` is set, calls show up in
the LangSmith dashboard. Otherwise everything no-ops so dev/test envs don't
need LangSmith credentials.
"""
from __future__ import annotations

import os
from functools import wraps
from typing import Any, Callable, TypeVar

from app.config import get_settings
from app.logger import get_logger

log = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

_initialized = False


def _ensure_init() -> bool:
    """Lazily configure LangSmith env vars. Returns True if tracing is active."""
    global _initialized
    if _initialized:
        return os.environ.get("LANGSMITH_TRACING", "").lower() == "true"

    settings = get_settings()
    api_key = settings.get("langsmith_api_key")
    if not api_key or not settings.get("langsmith_tracing"):
        _initialized = True
        return False

    # The langsmith SDK reads these from os.environ.
    os.environ["LANGSMITH_API_KEY"] = api_key
    os.environ["LANGSMITH_PROJECT"] = settings.get("langsmith_project") or "briefed-dev"
    os.environ["LANGSMITH_TRACING"] = "true"
    _initialized = True
    log.info("langsmith_enabled", project=os.environ["LANGSMITH_PROJECT"])
    return True


def traced(
    *,
    name: str | None = None,
    run_type: str = "chain",
    tags: list[str] | None = None,
) -> Callable[[F], F]:
    """
    Decorator that wraps a function in a LangSmith trace span when tracing is
    enabled. No-op otherwise.

    `run_type` is one of: chain, llm, tool, retriever, embedding, parser, prompt.
    """
    def decorator(fn: F) -> F:
        active = _ensure_init()
        if not active:
            return fn
        try:
            from langsmith import traceable
        except ImportError:
            log.warning("langsmith_sdk_missing")
            return fn

        wrapped = traceable(
            name=name or fn.__name__,
            run_type=run_type,
            tags=tags or [],
        )(fn)

        @wraps(fn)
        def _wrap(*args, **kwargs):
            return wrapped(*args, **kwargs)

        return _wrap  # type: ignore

    return decorator


def tag_run(**metadata: Any) -> None:
    """
    Attach metadata (meeting_id, agent_id, trigger_type, etc.) to the
    currently-active LangSmith run. No-op when tracing is disabled or there
    is no active run.
    """
    if not _ensure_init():
        return
    try:
        from langsmith.run_helpers import get_current_run_tree
        run = get_current_run_tree()
        if run is None:
            return
        # Convert all values to strings for safe serialization
        clean = {k: str(v) for k, v in metadata.items() if v is not None}
        run.add_metadata(clean)
    except Exception as e:
        log.debug("langsmith_tag_failed", error=str(e)[:160])
