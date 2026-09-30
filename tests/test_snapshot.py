from typing import Any

import pytest

from pbb.browser.snapshot import SnapshotStore, capture_snapshot, format_snapshot


class FakePage:
    url = "https://example.test/"

    async def evaluate(self, _script: str) -> dict[str, Any]:
        return {
            "elements": [
                {
                    "id": 1,
                    "role": "textbox",
                    "name": "Password",
                    "type": "password",
                    "value": "must-not-leak",
                    "selector": "#pw",
                },
                {"id": 2, "role": "button", "name": "Sign in", "selector": "#go"},
            ],
            "headings": [{"level": 1, "text": "Welcome"}],
            "text": "Safe page text",
        }

    async def title(self) -> str:
        return "Example"


@pytest.mark.asyncio
async def test_snapshot_hides_internal_selector_and_formats_refs() -> None:
    store = SnapshotStore()
    data = await capture_snapshot(FakePage(), store, 5000)  # type: ignore[arg-type]
    assert data["elements"][0]["type"] == "password"
    assert "selector" not in data["elements"][0]
    assert "value" not in data["elements"][0]
    assert "[2] button" in format_snapshot(data)
    assert store.get(1)["selector"] == "#pw"  # type: ignore[index]


def test_snapshot_id_is_stable_for_same_page() -> None:
    store = SnapshotStore()
    elements = [{"id": 1, "selector": "#x"}]
    store.update("https://example.test", elements)
    first = store.snapshot_id
    store.update("https://example.test", elements)
    assert store.snapshot_id == first
