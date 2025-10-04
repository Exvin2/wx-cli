# Repository Guidelines

## Project Structure & Module Organization
- Core package lives in `wx/`, with CLI entrypoints in `wx/cli.py`, configuration in `wx/config.py`, and network adapters in `wx/fetchers.py` and `wx/orchestrator.py`.
- Rendering helpers are in `wx/render.py`; forecasting logic and AI fallbacks sit in `wx/forecaster.py`.
- Tests belong in `tests/` alongside existing pytest suites such as `tests/test_cli.py` and `tests/test_fetchers.py`.
- Cached state is written to `~/.cache/wx/` via `wx/config.py`; avoid committing anything under that path.

## Build, Test, and Development Commands
- `python -m pip install -e .[dev]` installs runtime and dev dependencies from `pyproject.toml`.
- `python -m wx.cli --help` exercises the Typer CLI without installing the console script.
- `pytest` runs the full unit suite; use `pytest tests/test_cli.py -k offline` to scope checks while iterating.
- `python -m compileall wx` is a fast sanity check for syntax errors before opening a PR.

## Coding Style & Naming Conventions
- Code targets Python 3.11; prefer type hints and dataclasses (`wx/config.py`) where appropriate.
- Run `ruff check .` and `ruff format .` to keep lint and formatting aligned with `ruff.toml` (line length 100, double quotes, spaces for indentation).
- Modules use snake_case filenames; functions and variables follow the same. Reserve CamelCase for classes and dataclasses.

## Testing Guidelines
- Pytest is the standard; add fixtures to `tests/conftest.py` when sharing setup across files.
- Mirror module names when adding tests (e.g., new logic in `wx/orchestrator.py` should land in `tests/test_orchestrator.py`).
- Cover new branches, especially around offline/online toggles and API fallbacks. Include regression tests when fixing bugs.

## Commit & Pull Request Guidelines
- Follow concise, imperative commit summaries similar to `Update licensing and improve CLI invocation`; add context in the body when needed.
- Each PR should describe behaviour changes, reference related issues, and attach CLI output or screenshots for UX-facing tweaks.
- Note any env flags touched (`WX_OFFLINE`, `PRIVACY_MODE`, API keys) so reviewers can reproduce the scenario safely.

## Configuration & Secrets
- Load secrets via environment variables (`OPENROUTER_API_KEY`, `GEMINI_API_KEY`, `WX_OFFLINE`); never commit plaintext keys or state files.
- Document new configuration flags in `README.md` and update `wx/config.py` defaults to match.
