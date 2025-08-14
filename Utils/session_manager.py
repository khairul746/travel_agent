from uuid import uuid4
from typing import Any, Dict, Optional
from pydantic import BaseModel
try:
    from pydantic import ConfigDict   # Pydantic v2
    _V2 = True
except Exception:
    _V2 = False

from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page # type: ignore

class PWSession(BaseModel):
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
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=headless)
    context = await browser.new_context()
    page = await context.new_page()
    sid = str(uuid4())
    SESSIONS[sid] = PWSession(sid=sid, p=p, browser=browser, context=context, page=page, data={})
    return sid

def get_session(sid: str) -> PWSession:
    sess = SESSIONS.get(sid)
    if not sess:
        raise RuntimeError("Session not found or expired. Run search first.")
    return sess

async def close_session(sid: str) -> None:
    sess = SESSIONS.pop(sid, None)
    if not sess:
        return
    try:
        await sess.browser.close()
    finally:
        await sess.p.stop()
