from pbb.browser.locator import LocatorResolutionError


def test_locator_error_has_machine_readable_fields() -> None:
    exc = LocatorResolutionError("ambiguous_target", "many", {"matches": [1, 2]})
    assert exc.code == "ambiguous_target"
    assert exc.details["matches"] == [1, 2]
