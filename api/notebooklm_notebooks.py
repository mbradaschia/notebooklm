"""API handler to list NotebookLM notebooks."""

from helpers.api import ApiHandler, Request, Response
from usr.plugins.notebooklm.helpers.cli import run_cli


class NotebooklmNotebooks(ApiHandler):
    """List all notebooks with metadata."""

    async def process(self, input: dict, request: Request) -> dict | Response:
        try:
            result = await run_cli(["list", "--json"], timeout=30)

            if result["returncode"] != 0:
                return {
                    "error": result["stderr"] or "Failed to list notebooks",
                    "notebooks": [],
                }

            data = result.get("data") or {}
            notebooks_raw = data.get("notebooks", [])

            enriched = []
            for nb in notebooks_raw:
                enriched.append({
                    "id": nb.get("id", ""),
                    "title": nb.get("title", "") or "Untitled",
                    "is_owner": nb.get("is_owner", True),
                    "created_at": nb.get("created_at", ""),
                })

            return {"notebooks": enriched}

        except Exception as e:
            return {"error": str(e), "notebooks": []}
