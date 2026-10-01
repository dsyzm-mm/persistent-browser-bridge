from pbb.config import Settings
from pbb.daemon.app import create_app, error


def test_error_shape() -> None:
    assert error("element_not_found", "missing") == {
        "success": False,
        "error": "element_not_found",
        "message": "missing",
        "details": {},
    }


def test_app_has_required_routes() -> None:
    app = create_app(Settings(), "test")
    paths = {route.path for route in app.routes}
    assert {
        "/status",
        "/start",
        "/navigate",
        "/snapshot",
        "/click",
        "/fill",
        "/text",
        "/download",
        "/screenshot",
        "/tabs",
        "/tabs/switch",
        "/tabs/close",
        "/close",
        "/shutdown",
    } <= paths
