from typing import Any

import pytest

from pbb.browser.snapshot import SnapshotStore, capture_snapshot


class FakePage:
    url = "https://example.test/"
    frames: list[object] = []

    async def evaluate(self, _script: str) -> dict[str, Any]:
        return {
            "elements": [
                {"id": 1, "role": "checkbox", "name": "Enabled", "checked": True, "selector": "#enabled"},
                {"id": 2, "role": "combobox", "name": "Choice", "selected": "Second", "selector": "#choice"},
            ],
            "headings": [], "text": "A short summary", "tables": [{"id": 1, "rows": 2}], "dialogs": [],
        }

    async def title(self) -> str:
        return "Example"


@pytest.mark.asyncio
async def test_snapshot_v2_has_agent_sections_and_limits() -> None:
    result = await capture_snapshot(FakePage(), SnapshotStore(), 5, max_elements=1)  # type: ignore[arg-type]
    assert result["active_tab"] == 0
    assert result["form_controls"][0]["checked"] is True
    assert result["tables"][0]["rows"] == 2
    assert result["truncated"] is True
