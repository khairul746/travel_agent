from uuid import uuid4
from typing import Any, Dict, Optional
from pydantic import BaseModel
import asyncio
try:
    from pydantic import ConfigDict   # Pydantic v2
    _V2 = True
except Exception:
    _V2 = False

from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page # type: ignore


class PWSession(BaseModel):
    """
    Single Playwright session container.
    Keeps references to the Playwright driver, the browser, its context, the page,
    plus a small 'data' dict for any session-scoped metadata you want to cache.

    Fields:
      sid:      Unique identifier for this session (UUID string).
      p:        The top-level Playwright controller (from async_playwright().start()).
      browser:  The launched Chromium/Firefox/WebKit browser instance.
      context:  The BrowserContext created for this session.
      page:     The active Page within the context.
      data:     Free-form dict to store session-related data (inputs, preferences, etc).
    """
    if _V2:
        model_config = ConfigDict(arbitrary_types_allowed=True)
    else:
        class Config:
            arbitrary_types_allowed = True

    sid: str
    p: Playwright
    browser: Browser
    context: BrowserContext
    page: Page
    data: Dict[str, Any] = {}


SESSIONS: Dict[str, PWSession] = {}


async def create_session(headless: bool = True) -> str:
    """
    Create and register a new Playwright session and return its session id (sid).

    Steps:
      1) Start Playwright (async_playwright().start()).
      2) Launch a new browser (Chromium by default).
      3) Create a fresh BrowserContext and Page.
      4) Generate a UUID sid and store everything in SESSIONS[sid].

    Args:
      headless: Whether to launch the browser in headless mode.

    Returns:
      str: The newly created session id (UUID string).
    """
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=headless)
    context = await browser.new_context()
    page = await context.new_page()
    sid = str(uuid4())
    SESSIONS[sid] = PWSession(sid=sid, p=p, browser=browser, context=context, page=page, data={})
    return sid


def get_session(sid: str) -> PWSession:
    """
    Retrieve a previously created session by its sid.

    Raises:
      RuntimeError: If the sid is missing or the session has been closed/expired.

    Returns:
      PWSession: The live session object.
    """
    sess = SESSIONS.get(sid)
    if not sess:
        raise RuntimeError("Session not found or expired. Run search first.")
    return sess

async def close_session(sid: str) -> None:
    """
    Close and remove a session by sid.

    This attempts to:
      - Close the browser (which also closes all contexts/pages).
      - Stop the Playwright driver (p.stop()) in a 'finally' so it always runs.
    Args:
      sid: The session id to close. If it doesn’t exist, this is a no-op.
    """
    sess = SESSIONS.pop(sid, None)
    if not sess:
        return
    try:
        await sess.browser.close()
    finally:
        await sess.p.stop()

async def close_all_sessions() -> None:
    """Close all live sessions. Safe to call repeatedly."""
    for sid in list(SESSIONS.keys()):
        try:
            await close_session(sid)
        except Exception:
            pass

def close_all_sessions_sync(timeout: float | None = None) -> None:
    """
    Synchronous wrapper for close_all_sessions().
    Call this from a signal handler (SIGINT/SIGTERM) when stopping Flask,
    so Playwright is shut down before the process exits.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        fut = asyncio.run_coroutine_threadsafe(close_all_sessions(), loop)
        try:
            fut.result(timeout or 5)
        except Exception:
            pass
    else:
        loop = loop or asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(close_all_sessions())
        finally:
            loop.close()
