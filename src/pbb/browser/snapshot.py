"""Compact, safe DOM snapshots designed for agent tool calls."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from playwright.async_api import Frame, Page

SNAPSHOT_SCRIPT = r"""
(scopeSelector) => {
  const clean = (v) => (v || '').replace(/\s+/g, ' ').trim();
  const visible = (el) => { const s = getComputedStyle(el), r = el.getBoundingClientRect(); return s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0' && r.width > 0 && r.height > 0; };
  const root = scopeSelector ? document.querySelector(scopeSelector) : (document.querySelector('main') || document.body);
  if (!root) return {elements: [], headings: [], text: '', tables: [], dialogs: []};
  const selector = (el) => { if (el.id && CSS.escape) return '#' + CSS.escape(el.id); const parts = []; let node = el; while (node && node.nodeType === Node.ELEMENT_NODE && node !== document.body) { let part = node.tagName.toLowerCase(); const parent = node.parentElement; if (parent) { const siblings = [...parent.children].filter(x => x.tagName === node.tagName); if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(node) + 1})`; } parts.unshift(part); node = parent; if (parts.length >= 7) break; } return parts.join(' > '); };
  const roleOf = (el) => { if (el.getAttribute('role')) return el.getAttribute('role'); const tag = el.tagName.toLowerCase(), type = (el.getAttribute('type') || '').toLowerCase(); if (tag === 'a' && el.hasAttribute('href')) return 'link'; if (tag === 'button' || ['button','submit','reset'].includes(type)) return 'button'; if (tag === 'textarea' || (tag === 'input' && !['button','submit','reset','checkbox','radio','file','hidden'].includes(type))) return 'textbox'; if (type === 'checkbox') return 'checkbox'; if (type === 'radio') return 'radio'; if (tag === 'select') return 'combobox'; return tag; };
  const nameOf = (el) => { const aria = el.getAttribute('aria-label'); if (aria) return clean(aria); const labelled = el.getAttribute('aria-labelledby'); if (labelled) return clean(labelled.split(/\s+/).map(id => document.getElementById(id)?.innerText || '').join(' ')); if (el.labels?.length) return clean([...el.labels].map(x => x.innerText).join(' ')); return clean(el.innerText || el.getAttribute('alt') || el.getAttribute('title') || el.getAttribute('name') || el.getAttribute('placeholder')); };
  const candidates = [...root.querySelectorAll('a[href],button,input:not([type=hidden]),textarea,select,[role],[contenteditable=true]')].filter(visible).slice(0, 500);
  const elements = candidates.map((el, index) => { const type = (el.getAttribute('type') || '').toLowerCase(); const item = {id:index + 1, role:roleOf(el), name:nameOf(el), selector:selector(el), fingerprint:`${el.tagName}|${roleOf(el)}|${nameOf(el)}`}; const label = el.labels?.length ? clean([...el.labels].map(x => x.innerText).join(' ')) : ''; for (const [key, value] of [['label', label],['placeholder',el.getAttribute('placeholder')],['href',el.getAttribute('href')],['type',type],['expanded',el.getAttribute('aria-expanded')]]) if (value) item[key] = clean(value).slice(0, 500); if (type !== 'password' && ['checkbox','radio'].includes(type)) item.checked = !!el.checked; if (el.tagName.toLowerCase() === 'select') item.selected = clean(el.selectedOptions?.[0]?.textContent || ''); if (type !== 'password' && ['input','textarea'].includes(el.tagName.toLowerCase()) && el.value) item.value_preview = clean(el.value).slice(0, 120); if (el.disabled) item.disabled = true; return item; });
  const headings = [...root.querySelectorAll('h1,h2,h3')].filter(visible).slice(0, 30).map(el => ({level:Number(el.tagName[1]), text:clean(el.innerText).slice(0, 500)})).filter(x => x.text);
  const blocks = [...root.querySelectorAll('p,li,dt,dd,blockquote,pre,article,[role=article],[role=status],[role=alert]')].filter(visible).map(el => clean(el.innerText)).filter(Boolean);
  const tables = [...root.querySelectorAll('table')].filter(visible).slice(0, 10).map((table, i) => ({id:i + 1, headers:[...table.querySelectorAll('th')].slice(0, 20).map(x => clean(x.innerText)), rows:table.querySelectorAll('tbody tr').length || Math.max(0, table.querySelectorAll('tr').length - 1), preview:[...table.querySelectorAll('tr')].slice(1,4).map(row => [...row.querySelectorAll('th,td')].slice(0,20).map(cell => clean(cell.innerText)))}));
  const dialogs = [...document.querySelectorAll('dialog,[role=dialog],[role=alertdialog]')].filter(visible).slice(0, 5).map(el => ({role:roleOf(el), name:nameOf(el), text:clean(el.innerText).slice(0, 500)}));
  return {elements, headings, text:clean(blocks.length ? blocks.join(' ') : root.innerText).slice(0, 20000), tables, dialogs};
}
"""


@dataclass
class SnapshotStore:
    snapshot_id: str = ""
    page_url: str = ""
    elements: dict[int, dict[str, Any]] | None = None

    def update(self, url: str, elements: list[dict[str, Any]]) -> None:
        digest = hashlib.sha256((url + repr(elements)).encode()).hexdigest()[:10]
        self.snapshot_id = f"s_{digest}"
        self.page_url = url
        self.elements = {int(item["id"]): item for item in elements}

    def get(self, element_id: int) -> dict[str, Any] | None:
        return (self.elements or {}).get(element_id)


async def _capture_frame(frame: Frame | Page | Any, selector: str | None) -> dict[str, Any]:
    try:
        return await frame.evaluate(SNAPSHOT_SCRIPT, selector)
    except TypeError:
        # Lightweight test doubles from v0.1 accepted only the script argument.
        return await frame.evaluate(SNAPSHOT_SCRIPT)


async def capture_snapshot(page: Page, store: SnapshotStore, max_chars: int, *, max_elements: int | None = None, include_text: bool = True, selector: str | None = None, active_tab_index: int = 0) -> dict[str, Any]:
    main_frame = getattr(page, "main_frame", page)
    raw = await _capture_frame(main_frame, selector)
    elements = raw["elements"]
    frames: list[dict[str, Any]] = []
    for frame_index, frame in enumerate(getattr(page, "frames", [])[1:], start=1):
        try:
            frame_raw = await _capture_frame(frame, None)
        except Exception:
            frames.append({"index": frame_index, "url": frame.url, "accessible": False})
            continue
        frames.append({"index": frame_index, "url": frame.url, "accessible": True})
        for item in frame_raw["elements"]:
            item["frame"] = frame_index
            item["id"] = len(elements) + 1
            elements.append(item)
    store.update(page.url, elements)
    limit = max_elements if max_elements is not None else 100
    public_keys = {"id", "role", "name", "label", "placeholder", "href", "type", "checked", "selected", "disabled", "expanded", "value_preview", "frame"}
    public_elements = [{k: v for k, v in item.items() if k in public_keys} for item in elements[:limit]]
    text = raw["text"][:max_chars] if include_text else ""
    return {"success": True, "snapshot_id": store.snapshot_id, "url": page.url, "title": await page.title(), "active_tab": active_tab_index, "elements": public_elements, "headings": raw["headings"], "form_controls": [item for item in public_elements if item.get("role") in {"textbox", "checkbox", "radio", "combobox"}], "tables": raw.get("tables", []), "dialogs": raw.get("dialogs", []), "iframes": frames, "text": text, "text_summary": text, "truncated": len(raw["text"]) > max_chars or len(elements) > limit}


def format_snapshot(data: dict[str, Any]) -> str:
    lines = ["PAGE", f"Title: {data['title']}", f"URL: {data['url']}", f"Snapshot: {data['snapshot_id']}", "", "INTERACTIVE ELEMENTS"]
    for item in data["elements"]:
        lines.append(f"[{item['id']}] {item['role']}")
        for key in ("name", "label", "placeholder", "href", "type", "checked", "selected", "disabled", "expanded", "value_preview", "frame"):
            if key in item and item[key] not in {"", None}:
                lines.append(f"{key}: {item[key]}")
        lines.append("")
    if data.get("headings"):
        lines.extend(("HEADINGS", *(f"[H{x['level']}] {x['text']}" for x in data["headings"]), ""))
    if data.get("dialogs"):
        lines.extend(("DIALOGS", *(f"{x['role']}: {x['name']}" for x in data["dialogs"]), ""))
    if data.get("iframes"):
        lines.extend(("IFRAMES", *(f"FRAME [{x['index']}] {x['url']}" for x in data["iframes"]), ""))
    if data.get("text"):
        lines.extend(("TEXT", data["text"]))
    return "\n".join(lines).rstrip()
