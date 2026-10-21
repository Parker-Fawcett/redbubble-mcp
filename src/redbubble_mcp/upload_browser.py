"""Uploads a design to Redbubble by driving a real browser (Playwright).

Strategy: open the "Add New Work" page, or better, the *duplicate* page of one of
your existing works so every product setting copies over - the approach used by
hand-maintained upload bots for years and the least bot-detectable thing to click.
"""

from __future__ import annotations

from redbubble_mcp.guards import DEFAULT_DIR

STATE_FILE = "storage_state.json"
ADD_NEW_URL = "https://www.redbubble.com/portfolio/images/new"
SUBMIT_DONE_HINT = "studio/promote"


class NoSessionError(Exception):
    pass


def _fill_first(page, selectors: list[str], value: str) -> bool:
    for sel in selectors:
        loc = page.locator(sel)
        if loc.count():
            loc.first.fill(value)
            return True
    return False


def _check_first(page, selectors: list[str]) -> bool:
    for sel in selectors:
        loc = page.locator(sel)
        if loc.count():
            loc.first.check()
            return True
    return False


def upload_via_browser(
    *,
    image_path: str,
    title: str,
    tags: str,
    description: str = "",
    template_work_url: str | None = None,
    headless: bool = False,
) -> dict:
    state_path = DEFAULT_DIR / STATE_FILE
    if not state_path.exists():
        raise NoSessionError(
            "No saved browser session. Run `redbubble-mcp-login` first."
        )

    from playwright.sync_api import sync_playwright

    url = (
        template_work_url.rstrip("/") + "/duplicate"
        if template_work_url
        else ADD_NEW_URL
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(storage_state=str(state_path))
        page = context.new_page()

        page.goto(url)
        if "auth" in page.url:
            raise NoSessionError(
                "Redbubble wants us to log in again - run `redbubble-mcp-login`."
            )

        file_input = page.locator("input[type=file]").first
        file_input.set_input_files(image_path)

        # wait (up to 3 min) for the image processing banner to disappear
        page.wait_for_function(
            "() => /Uploading|Processing/i.test(document.body.innerText) === false",
            timeout=180_000,
        )

        filled = {
            "title": _fill_first(
                page, ["input#work_title_en"], title
            ),
            "tags": _fill_first(
                page, ["textarea#work_tag_field_en"], tags
            ),
            "description": _fill_first(
                page, ["#work_description_en"], description
            )
            if description
            else True,
        }
        missing = [k for k, v in filled.items() if not v]
        if missing:
            context.storage_state(path=str(state_path))
            return {
                "status": "failed",
                "error": f"could not locate fields: {missing}",
                "page_url": page.url,
                "hint": "Redbubble's markup changed - open that URL manually and update selectors in upload_browser.py",
            }

        _check_first(page, ["#rightsDeclaration", "input[name='rightsDeclaration']"])
        submit = page.locator("button#submit-work, button[type=submit]").first
        submit.click()

        try:
            page.wait_for_url(
                lambda u: SUBMIT_DONE_HINT in u, timeout=120_000
            )
        except Exception:
            pass

        submitted = SUBMIT_DONE_HINT in page.url
        context.storage_state(path=str(state_path))
        browser.close()

    return {
        "status": "submitted" if submitted else "uncertain",
        "page_url": page.url,
    }
