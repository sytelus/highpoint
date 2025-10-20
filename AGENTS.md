# Repository Guidelines

## Project Structure & Module Organization
Highpoint is currently a clean slate; keep the layout predictable as modules arrive. Place production code in `src/` and mirror tests under `tests/`. Use `assets/` for datasets or prompt templates and `scripts/` for helper CLIs. Give each agent a subpackage at `src/highpoint/<agent_name>/` with local `config.py` and `handlers/`, keep shared helpers in `src/highpoint/common/`, and record design decisions in ADRs under `docs/`.

## Build, Test, and Development Commands
Standardize on Make so humans and agents run the same workflow. Maintain these root targets: `make bootstrap` (create `.venv/` and install from `requirements.txt`), `make lint` (run `ruff` and `black --check` on `src/` and `tests/`), `make test` (`pytest --cov=src/highpoint`), and `make run` (`python -m highpoint.app`). When new tooling appears, extend the targets instead of committing raw commands.

## Coding Style & Naming Conventions
Target Python 3.11+. Use four-space indentation, full type annotations, and `snake_case` for modules, functions, and variables; reserve `PascalCase` for classes. Format with `black`, lint with `ruff --fix`, and gate PRs with `mypy --strict`. Keep module interfaces slim, prefer dataclasses for structured payloads, and store configs in `configs/` with uppercase keys plus inline comments.

## Testing Guidelines
Write tests with `pytest` and mirror production paths (`src/highpoint/foo.py` → `tests/highpoint/test_foo.py`). Name cases `test_<behavior>__<expected>()` for quick scanning, aim for ≥90% branch coverage, and fail fast on flaky suites. Keep reusable fixtures in `tests/fixtures/`, prefer factories over hard-coded IDs, and land regression tests before merging fixes.

## Commit & Pull Request Guidelines
Follow Conventional Commits (e.g., `feat: add routing agent`, `fix: guard auth token refresh`). Keep commits focused and include motivation in the body when the diff is not obvious. PRs must outline scope, link tracking issues, list executed commands, and attach screenshots or logs for behavioral changes. Request review only after `make lint` and `make test` pass locally.

## Security & Configuration Tips
Never commit secrets; store runtime credentials in `.env.local` and update `.gitignore` when new keys appear. Document every environment variable in `docs/configuration.md` with defaults and rotation notes. Rotate tokens shared with automation promptly and record expirations in the PR. Editor adjustments live in `.vscode/`; propose changes through review before committing.
