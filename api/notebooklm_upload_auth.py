"""API handler to upload cookies JSON and save as NotebookLM auth storage state."""

import json
import os
from pathlib import Path

from helpers.api import ApiHandler, Request, Response
from helpers.plugins import get_plugin_config
from usr.plugins.notebooklm.helpers.cli import ensure_auth_dir


def _get_storage_path() -> Path:
    """Resolve auth storage path from plugin config, handling both dir and file values."""
    cfg = get_plugin_config("notebooklm") or {}
    raw = cfg.get("auth_storage_path", "/a0/usr/secrets/notebooklm")
    p = Path(raw)
    return p if p.suffix == ".json" else p / "storage_state.json"


# sameSite value normalization from Cookie-Editor → Playwright
_SAME_SITE_MAP = {
    "no_restriction": "None",
    "none": "None",
    "lax": "Lax",
    "strict": "Strict",
    "unspecified": "Lax",
}


def _cookie_editor_to_playwright(cookies: list[dict]) -> list[dict]:
    """Convert Cookie-Editor export array to Playwright cookies format."""
    out = []
    for c in cookies:
        same_site_raw = str(c.get("sameSite", c.get("same_site", "Lax"))).lower()
        same_site = _SAME_SITE_MAP.get(same_site_raw, "Lax")

        # 'expirationDate' (Cookie-Editor) → 'expires' (Playwright)
        expires = c.get("expires", c.get("expirationDate", -1))
        if expires is None:
            expires = -1

        out.append({
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
            "expires": float(expires),
            "httpOnly": bool(c.get("httpOnly", c.get("http_only", False))),
            "secure": bool(c.get("secure", False)),
            "sameSite": same_site,
        })
    return out


def _to_storage_state(data: dict | list) -> dict:
    """Normalize uploaded JSON to Playwright storage_state format."""
    if isinstance(data, list):
        # Cookie-Editor array export
        cookies = _cookie_editor_to_playwright(data)
        return {"cookies": cookies, "origins": []}

    if isinstance(data, dict):
        if "cookies" in data:
            # Already Playwright storage_state format — normalize cookie fields
            cookies = _cookie_editor_to_playwright(data["cookies"])
            return {
                "cookies": cookies,
                "origins": data.get("origins", []),
            }

    raise ValueError("Unrecognized format: expected a cookies array or storage_state object")


def _validate(storage_state: dict) -> None:
    """Basic validation: must have Google domain cookies."""
    cookies = storage_state.get("cookies", [])
    if not cookies:
        raise ValueError("No cookies found in the uploaded file")

    google_cookies = [
        c for c in cookies
        if "google" in c.get("domain", "").lower()
    ]
    if not google_cookies:
        raise ValueError(
            f"No Google cookies found ({len(cookies)} cookies total). "
            "Please export cookies from notebooklm.google.com"
        )


class NotebooklmUploadAuth(ApiHandler):
    """Receive uploaded cookies JSON and save as NotebookLM storage state."""

    async def process(self, input: dict, request: Request) -> dict | Response:
        cookies_json = input.get("cookies_json")
        if cookies_json is None:
            return {"error": "Missing cookies_json field"}

        try:
            storage_state = _to_storage_state(cookies_json)
            _validate(storage_state)
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to parse cookies: {e}"}

        try:
            storage_path = _get_storage_path()
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            storage_path.write_text(json.dumps(storage_state, indent=2))
            # Also write to ~/.notebooklm/storage_state.json (the CLI default path)
            default_dir = Path(os.path.expanduser("~/.notebooklm"))
            default_dir.mkdir(parents=True, exist_ok=True)
            default_path = default_dir / "storage_state.json"
            if default_path.is_symlink():
                default_path.unlink()
            default_path.write_text(json.dumps(storage_state, indent=2))
        except Exception as e:
            return {"error": f"Failed to save auth file: {e}"}
        count = len(storage_state["cookies"])
        return {
            "ok": True,
            "message": f"Authentication saved! {count} cookies stored.",
            "cookie_count": count,
        }
