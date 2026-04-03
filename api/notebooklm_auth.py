"""API handler to check NotebookLM auth status."""

from helpers.api import ApiHandler, Request, Response
from usr.plugins.notebooklm.helpers.cli import run_cli


class NotebooklmAuth(ApiHandler):
    """Check NotebookLM authentication status."""

    async def process(self, input: dict, request: Request) -> dict | Response:
        try:
            result = await run_cli(
                ["auth", "check", "--json"],
                timeout=15,
            )

            if result["data"]:
                data = result["data"]
                # Fix: 'status' == 'ok' is the authoritative signal.
                # Do NOT fall back to returncode — the CLI exits 0 even when
                # storage is missing, which caused authenticated=True incorrectly.
                if "authenticated" in data:
                    authenticated = bool(data["authenticated"])
                else:
                    authenticated = data.get("status") == "ok"
                return {
                    "authenticated": authenticated,
                    "details": data,
                }

            return {
                "authenticated": result["returncode"] == 0,
                "message": result["stdout"] or result["stderr"],
            }

        except Exception as e:
            return {"authenticated": False, "error": str(e)}
