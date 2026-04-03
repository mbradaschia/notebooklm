"""API handler to persist/read active notebook selection — per chat context."""

import json
from pathlib import Path

from helpers.api import ApiHandler, Request, Response

STORAGE_DIR = Path("/a0/tmp/notebooklm")


def _ctx_file(context_id: str) -> Path:
    """Return path to per-chat notebook state file."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return STORAGE_DIR / f"{context_id}.json"


class NotebooklmSetActive(ApiHandler):
    """Persist or read the active notebook selection for the current chat context."""

    async def process(self, input: dict, request: Request) -> dict | Response:
        try:
            data = input if isinstance(input, dict) else {}
            if isinstance(input, str) and input.strip():
                data = json.loads(input)

            action = str(data.get("action", "set")).strip()
            context_id = str(data.get("context_id", "")).strip()

            # ── GET ACTIVE (read per-context state) ──────────────────────────
            if action == "get_active":
                if not context_id:
                    return {"active_notebook_id": "", "active_notebook_title": ""}
                ctx_file = _ctx_file(context_id)
                if ctx_file.exists():
                    state = json.loads(ctx_file.read_text())
                    return {
                        "active_notebook_id": state.get("active_notebook_id", ""),
                        "active_notebook_title": state.get("active_notebook_title", ""),
                        "context_id": context_id,
                    }
                return {"active_notebook_id": "", "active_notebook_title": "", "context_id": context_id}

            # ── SET ACTIVE (write per-context state) ─────────────────────────
            notebook_id = str(data.get("notebook_id", "")).strip()
            notebook_title = str(data.get("notebook_title", "")).strip()

            if not context_id:
                return {"error": "context_id required — per-chat activation only"}

            state = {
                "active_notebook_id": notebook_id,
                "active_notebook_title": notebook_title,
            }
            _ctx_file(context_id).write_text(json.dumps(state))
            # Debug log
            import datetime
            with open("/a0/tmp/notebooklm/debug.log", "a") as _log:
                _log.write(f"[{datetime.datetime.now().isoformat()}] SET context_id={context_id!r} notebook_id={notebook_id!r} notebook_title={notebook_title!r}\n")

            return {
                "success": True,
                "active_notebook_id": notebook_id,
                "active_notebook_title": notebook_title,
                "deselected": not notebook_id,
                "context_id": context_id,
            }

        except Exception as e:
            return {"error": str(e)}
