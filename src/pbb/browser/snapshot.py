"""Compact, safe DOM snapshots for agents."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from playwright.async_api import Page

SNAPSHOT_SCRIPT = r"""
() => {
  const visible = (el) => {
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
  };
  const clean = (v) => (v || '').replace(/\s+/g, ' ').trim();
  const selector = (el) => {
    if (el.id && CSS.escape) return '#' + CSS.escape(el.id);
    const parts = [];
    let node = el;
    while (node && node.nodeType === Node.ELEMENT_NODE && node !== document.body) {
      let part = node.tagName.toLowerCase();
      const parent = node.parentElement;
      if (parent) {
        const siblings = [...parent.children].filter(x => x.tagName === node.tagName);
        if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
      }
      parts.unshift(part); node = parent;
      if (parts.length >= 6) break;
    }
    return parts.join(' > ');
  };
  const roleOf = (el) => {
    if (el.getAttribute('role')) return el.getAttribute('role');
    const tag = el.tagName.toLowerCase(), type = (el.getAttribute('type') || '').toLowerCase();
    if (tag === 'a' && el.hasAttribute('href')) return 'link';
    if (tag === 'button' || type === 'button' || type === 'submit' || type === 'reset') return 'button';
    if (tag === 'textarea' || (tag === 'input' && !['button','submit','reset','checkbox','radio','file','hidden'].includes(type))) return 'textbox';
    if (type === 'checkbox') return 'checkbox';
    if (type === 'radio') return 'radio';
    if (tag === 'select') return 'combobox';
    return tag;
  };
  const nameOf = (el) => {
    const aria = el.getAttribute('aria-label'); if (aria) return clean(aria);
    const labelled = el.getAttribute('aria-labelledby');
    if (labelled) return clean(labelled.split(/\s+/).map(id => document.getElementById(id)?.innerText || '').join(' '));
    if (el.labels?.length) return clean([...el.labels].map(x => x.innerText).join(' '));
    return clean(el.innerText || el.getAttribute('alt') || el.getAttribute('title') || el.getAttribute('name') || el.getAttribute('placeholder'));
  };
  const candidates = [...document.querySelectorAll('a[href],button,input:not([type=hidden]),textarea,select,[role],[contenteditable=true]')]
    .filter(visible).slice(0, 500);
  const elements = candidates.map((el, index) => {
    const type = (el.getAttribute('type') || '').toLowerCase();
    const item = {id:index + 1, role:roleOf(el), name:nameOf(el), selector:selector(el)};
    for (const [key, value] of [['placeholder',el.getAttribute('placeholder')],['href',el.getAttribute('href')],['type',type]]) {
      if (value) item[key] = clean(value).slice(0, 500);
    }
    if (type !== 'password' && ['checkbox','radio'].includes(type)) item.checked = !!el.checked;
    if (el.disabled) item.disabled = true;
    return item;
  });
  const headings = [...document.querySelectorAll('h1,h2,h3')].filter(visible).slice(0, 30)
    .map(el => ({level:Number(el.tagName[1]), text:clean(el.innerText).slice(0, 500)})).filter(x => x.text);
  const root = document.querySelector('main') || document.body;
  const clone = root.cloneNode(true);
  clone.querySelectorAll('script,style,svg,noscript,input,textarea,select,button,a,nav,header,footer,[hidden],[aria-hidden=true]').forEach(x => x.remove());
  const text = clean(clone.innerText).slice(0, 20000);
  return {elements, headings, text};
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


async def capture_snapshot(page: Page, store: SnapshotStore, max_chars: int) -> dict[str, Any]:
    raw = await page.evaluate(SNAPSHOT_SCRIPT)
    elements = raw["elements"]
    store.update(page.url, elements)
    public_keys = {"id", "role", "name", "placeholder", "href", "type", "checked", "disabled"}
    public_elements = [{k: v for k, v in item.items() if k in public_keys} for item in elements]
    return {
        "success": True,
        "snapshot_id": store.snapshot_id,
        "url": page.url,
        "title": await page.title(),
        "elements": public_elements,
        "headings": raw["headings"],
        "text": raw["text"][:max_chars],
        "truncated": len(raw["text"]) > max_chars,
    }


def format_snapshot(data: dict[str, Any]) -> str:
    lines = [
        "PAGE",
        f"Title: {data['title']}",
        f"URL: {data['url']}",
        f"Snapshot: {data['snapshot_id']}",
        "",
        "INTERACTIVE ELEMENTS",
    ]
    for item in data["elements"]:
        lines.append(f"[{item['id']}] {item['role']}")
        for key in ("name", "placeholder", "href", "type", "checked", "disabled"):
            if key in item and item[key] not in {"", None}:
                lines.append(f"{key}: {item[key]}")
        lines.append("")
    if data["headings"]:
        lines.append("HEADINGS")
        lines.extend(f"[H{x['level']}] {x['text']}" for x in data["headings"])
        lines.append("")
    if data["text"]:
        lines.extend(("TEXT", data["text"]))
    return "\n".join(lines).rstrip()
