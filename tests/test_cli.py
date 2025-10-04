import pytest

from wx import cli


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        ([], []),
        (["How's", "weather?"], ["How's", "weather?"]),
        (["forecast", "Paris"], ["", "forecast", "Paris"]),
        (["--offline", "forecast", "Paris"], ["--offline", "", "forecast", "Paris"]),
        (["--style", "brief", "forecast", "Paris"], ["--style", "brief", "", "forecast", "Paris"]),
        (["", "forecast", "Paris"], ["", "forecast", "Paris"]),
        (["--", "forecast"], ["--", "forecast"]),
        (["risk", "--hazards", "wind"], ["", "risk", "--hazards", "wind"]),
    ],
)
def test_normalize_invocation(argv, expected):
    assert cli._normalize_invocation(argv) == expected
