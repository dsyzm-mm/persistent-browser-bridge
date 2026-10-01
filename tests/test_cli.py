import json

from typer.testing import CliRunner

from pbb.cli import app

runner = CliRunner()


def test_help_lists_core_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("start", "status", "open", "snapshot", "click", "fill", "download", "tabs", "tab", "mcp", "close"):
        assert command in result.stdout


def test_status_json_when_daemon_absent(monkeypatch) -> None:
    monkeypatch.setenv("PBB_PORT", "65431")
    result = runner.invoke(app, ["status", "--json"])
    assert result.exit_code == 1
    assert '"error": "daemon_not_running"' in result.stdout


def test_json_output_handles_non_ascii(monkeypatch) -> None:
    monkeypatch.setattr(
        "pbb.cli.DaemonClient.status",
        lambda _self: {"success": True, "title": "مرحبا"},
    )
    result = runner.invoke(app, ["status", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["title"] == "مرحبا"
