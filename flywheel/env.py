"""Dev-time ``.env`` loading.

A tiny, guarded helper so the dev server and demo scripts pick up a gitignored
repo-root ``.env`` (keys like ``OPENAI_API_KEY`` / ``FIRECRAWL_API_KEY`` and
``FLYWHEEL_VENTURE``) without you exporting them by hand or pasting them into the
git-tracked ``launch.json``.

Deliberately defensive:
- ``python-dotenv`` is a dev-only dep; if it's absent (prod/CI), this is a no-op.
- Existing environment variables are **not** overridden (``override=False``), so
  values set by the shell or the VS Code debugger ``env`` block always win.
"""

from __future__ import annotations

from pathlib import Path

# Repo root = two levels up from this file (flywheel/env.py -> repo/).
_REPO_ROOT = Path(__file__).resolve().parents[1]


def load_dotenv_if_present() -> bool:
    """Load ``<repo>/.env`` into ``os.environ`` if possible. Returns whether it ran.

    No-op (returns ``False``) when python-dotenv isn't installed or no ``.env``
    file exists. Never raises — env loading must not break startup.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False
    env_path = _REPO_ROOT / ".env"
    if not env_path.exists():
        return False
    return bool(load_dotenv(env_path, override=False))
