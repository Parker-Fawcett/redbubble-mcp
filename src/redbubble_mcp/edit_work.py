"""Edit an existing Redbubble work (title, tags, description) via the live browser session.

Edit page form facts (verified 2026-10 against current markup):
- #work_title_en         text input  (name=work[title_en])
- #work_tag_editor_en    hidden input (name=work[tag_field_en]) fed by the tag-chip UI;
                         set via React's native value setter so the UI state follows
- #work_description_en   textarea (name=work[description_en])
- #rightsDeclaration     rights checkbox (name=rights_declaration)
- #submit-work           "Save work" submit button
- 15 tags max, 50 chars per tag, primary tag is the first tag"""

from __future__ import annotations

from redbubble_mcp.browser_session import get_session

_TITLE = "#work_title_en"
_TAGS = "#work_tag_editor_en"
_DESCRIPTION = "#work_description_en"
_SUBMIT = "#submit-work"
_RIGHTS = "#rightsDeclaration"

SET_VALUE_JS = """({sel, value}) => {
    const el = document.querySelector(sel);
    if (!el) return false;
    const proto = el.tagName === 'TEXTAREA'
        ? window.HTMLTextAreaElement.prototype
        : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
    setter.call(el, value);
    el.dispatchEvent(new Event('input', {bubbles: true}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
    return true;
}"""


def normalize_tags(tags: str) -> str:
    """Split, trim, dedupe, cap: max 15 tags, 50 chars each."""
    seen: list[str] = []
    for raw in (tags or "").split(","):
        tag = raw.strip()
        if not tag or tag in seen:
            continue
        seen.append(tag[:50])
        if len(seen) == 15:
            break
    return ", ".join(seen)


def edit_work(
    *,
    work_url: str,
    title: str | None = None,
    tags: str | None = None,
    description: str | None = None,
    submit: bool = True,
) -> dict:
    """work_url: the work's portfolio URL or its /edit URL."""
    page = get_session().current_page
    url = work_url if work_url.endswith("/edit") else work_url.rstrip("/") + "/edit"
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_function(
        "() => document.querySelector('#work_title_en') && document.querySelector('#submit-work')",
        timeout=30_000,
    )

    changed = []
    if title is not None:
        page.evaluate(
            SET_VALUE_JS, {"sel": _TITLE, "value": title[:120]}
        )
        changed.append("title")
    if tags is not None:
        page.evaluate(SET_VALUE_JS, {"sel": _TAGS, "value": normalize_tags(tags)})
        changed.append("tags")
    if description is not None:
        page.evaluate(SET_VALUE_JS, {"sel": _DESCRIPTION, "value": description[:250]})
        changed.append("description")

    if not submit:
        return {"status": "draft", "changed": changed, "page_url": page.url}

    try:
        rights = page.locator(_RIGHTS)
        if rights.count() and not rights.first.is_checked():
            rights.first.check()
    except Exception:
        pass
    submit_btn = page.locator(_SUBMIT)
    if submit_btn.count():
        submit_btn.first.click()
        try:
            page.wait_for_load_state("domcontentloaded", timeout=30_000)
        except Exception:
            pass
        return {"status": "submitted", "changed": changed, "page_url": page.url}
    return {"status": "failed", "reason": "no submit button found", "page_url": page.url}
