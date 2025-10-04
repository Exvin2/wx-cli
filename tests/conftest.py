from __future__ import annotations

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "wx_state"
    monkeypatch.setenv("WX_STATE_DIR", str(path))
    return path


@pytest.fixture()
def cli_runner() -> CliRunner:
    return CliRunner()
