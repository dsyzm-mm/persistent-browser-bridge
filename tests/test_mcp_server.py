from pbb.mcp import server


def test_mcp_status_uses_daemon_client(monkeypatch) -> None:
    monkeypatch.setattr(server, "_request", lambda method, path, payload=None: {"success": True, "path": path})
    assert server.browser_status() == {"success": True, "path": "/status"}


def test_mcp_unavailable_is_structured(monkeypatch) -> None:
    monkeypatch.setattr(server, "_request", lambda method, path, payload=None: server._error("daemon_not_running", "missing"))
    result = server.browser_open("https://example.test")
    assert result["error"] == "daemon_not_running"
