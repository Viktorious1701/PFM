# Environment record

Verified 2026-07-30 on the development machine. Each row states a fact and the decision it forced. Referenced by constitution rules ENV-01…04.

## Machine

| Property | Value |
| :-- | :-- |
| OS | Ubuntu 26.04 LTS on WSL2 (kernel 6.18.33.1-microsoft-standard) |
| Working dir | `/mnt/d/Work/PFM` (Windows drive via WSL mount) |
| WSL IP | `172.17.96.48` (NAT'd — not reachable from the LAN) |

## Toolchain

| Tool | State | Consequence |
| :-- | :-- | :-- |
| System Python | 3.14.4, **no `pip`, no `ensurepip`** | Cannot install packages with system Python at all |
| `uv` | 0.12.0, installed to `~/.local/bin` without sudo | **ENV-01:** every Python command is `uv run …` |
| CPython | 3.13.14 installed by `uv` | **ENV-02:** pinned in `.python-version`; avoids 3.14 wheel gaps |
| Node | 24.18.0 / npm 11.16.0 | Available but unused in round 1 |
| JDK | OpenJDK 17.0.19 | Only relevant to a future Android build |
| Git | present, repo initialised, no commits at start | `.gitignore` landed with the first commit |
| `sudo` | requires an interactive password | Nothing may depend on installing system packages |

Why sudo matters: the obvious fix for the missing pip was `sudo apt install python3-venv python3-pip`. That needs a password the automation does not have, so `uv` — which installs to the home directory and manages its own interpreters — was the only viable route.

## Blocked capabilities

| Capability | Status | Effect |
| :-- | :-- | :-- |
| **Docker** | CLI present at `/mnt/c/Program Files/Docker/…`, but the **daemon is unreachable** from WSL2 (integration disabled) | No PostgreSQL container, no Mailpit. **ENV-03:** SQLite locally; PostgreSQL remains the deployment target per SDS §4.5 |
| **Android SDK** | absent — no `adb`, no `emulator`, `ANDROID_HOME` unset | No emulator. **ENV-04:** mobile deferred; see `../mobile-readiness.md` |
| **Physical device** | none attached | Combined with WSL2's NAT, a phone could not reach a dev server without a tunnel |

## Consequences for testing

- **Database:** SQLite for both local runs and the test suite. Nothing may rely on SQLite-specific behaviour, since production is PostgreSQL. Two known divergences to guard against:
  - SQLite drops `tzinfo`, so stored datetimes read back naive → `clock.ensure_aware()` exists for this.
  - SQLite cannot `ALTER` in place → `render_as_batch=True` in `migrations/env.py`.
- **Email:** Gmail SMTP is reachable outbound. Tests mock it by default; a real send is opt-in via `pytest -m smtp` and needs an App Password in `.env` (constitution TST-07).
- **Mobile:** no device or emulator means React Native work cannot be verified here at all. It is deferred rather than written blind.

## Re-verification

```bash
uv --version && uv python list --only-installed
docker info >/dev/null 2>&1 && echo docker-up || echo docker-down
echo "ANDROID_HOME=${ANDROID_HOME:-unset}"; command -v adb emulator || echo "no android tools"
cd backend && uv run pytest -q && uv run ruff check . && uv run mypy app
```
