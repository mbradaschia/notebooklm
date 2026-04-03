"""Tool: notebooklm_ask — query the active NotebookLM notebook.

Self-contained implementation: does NOT import from helpers.cli to avoid
Python module cache issues (A0 watchdog does not reload helper modules).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any

from helpers.tool import Tool, Response

# Paths (same as helpers/cli.py — duplicated here to avoid module cache issues)
_PLUGIN_DIR = Path(__file__).parent.parent
_PLUGIN_VENV_BINARY = str(_PLUGIN_DIR / ".venv" / "bin" / "notebooklm")
_SKILL_VENV_BINARY = "/a0/usr/skills/notebooklm/.venv/bin/notebooklm"
_STORAGE_DIR = Path("/a0/tmp/notebooklm")
_CHAT_HOME_BASE = Path("/a0/tmp/notebooklm/home")
_PERSISTENT_AUTH_DIR = Path("/a0/usr/secrets/notebooklm")


def _binary() -> str:
    if os.path.isfile(_PLUGIN_VENV_BINARY):
        return _PLUGIN_VENV_BINARY
    if os.path.isfile(_SKILL_VENV_BINARY):
        return _SKILL_VENV_BINARY
    return _PLUGIN_VENV_BINARY


def _get_active_notebook(agent) -> tuple[str, str]:
    """Read per-chat active notebook — pure file I/O, no imports from helpers.cli."""
    try:
        context_id = getattr(getattr(agent, "context", None), "id", None)
        if context_id:
            ctx_file = _STORAGE_DIR / f"{context_id}.json"
            if ctx_file.exists():
                state = json.loads(ctx_file.read_text())
                nb_id = state.get("active_notebook_id", "").strip()
                nb_title = state.get("active_notebook_title", "").strip()
                if nb_id:
                    return nb_id, nb_title
    except Exception:
        pass
    return "", ""


def _setup_chat_home(context_id: str, notebook_id: str, notebook_title: str) -> str:
    """Create isolated NOTEBOOKLM_HOME for this chat context."""
    home_dir = _CHAT_HOME_BASE / context_id
    home_dir.mkdir(parents=True, exist_ok=True)

    # Symlink storage_state.json from persistent auth dir
    auth_src = _PERSISTENT_AUTH_DIR / "storage_state.json"
    auth_link = home_dir / "storage_state.json"
    if auth_src.exists() and not auth_link.exists():
        auth_link.symlink_to(auth_src)
    elif auth_link.is_symlink() and not auth_link.exists():
        # Broken symlink — re-create
        auth_link.unlink()
        if auth_src.exists():
            auth_link.symlink_to(auth_src)

    # Write fresh context.json with correct notebook_id, NO conversation_id
    ctx = {"notebook_id": notebook_id, "title": notebook_title}
    (home_dir / "context.json").write_text(json.dumps(ctx))

    return str(home_dir)


async def _run(args: list[str], env: dict, timeout: int = 60) -> dict:
    """Run notebooklm CLI command directly — no helpers.cli dependency."""
    binary = _binary()
    cmd = [binary] + args
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        stdout = stdout_b.decode(errors="replace")
        stderr = stderr_b.decode(errors="replace")
        data = None
        try:
            data = json.loads(stdout)
        except (json.JSONDecodeError, ValueError):
            pass
        return {"returncode": proc.returncode, "stdout": stdout, "stderr": stderr, "data": data}
    except asyncio.TimeoutError:
        return {"returncode": -1, "stdout": "", "stderr": f"Timeout after {timeout}s", "data": None}
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e), "data": None}


class NotebooklmAsk(Tool):
    """Query the active NotebookLM notebook. Returns grounded answer with academic references."""

    async def execute(self, question: str = "", **kwargs) -> Response:
        if not question:
            return Response(message="Please provide a question.", break_loop=False)

        # Get active notebook directly from file — no module imports
        notebook_id, notebook_title = _get_active_notebook(self.agent)
        if not notebook_id:
            return Response(
                message="No notebook is currently active. Please select a notebook using the 📓 button in the chat input.",
                break_loop=False,
            )

        # Set up isolated NOTEBOOKLM_HOME for this chat
        context_id = getattr(getattr(self.agent, "context", None), "id", "") or "default"
        chat_home = _setup_chat_home(context_id, notebook_id, notebook_title)

        # Build environment with NOTEBOOKLM_HOME isolation
        env = dict(os.environ)
        env["NOTEBOOKLM_HOME"] = chat_home

        # Step 1: run 'use <notebook_id>' to initialise a fresh conversation
        # (SKILL.md: "Always notebooklm use <id> first")
        use_result = await _run(["use", notebook_id], env=env, timeout=15)
        # Ignore use errors — context.json may already be correct

        # Step 2: run ask (continues the conversation opened by 'use') +
        #         source list concurrently
        ask_task = asyncio.create_task(
            _run(["ask", question, "--json"], env=env, timeout=120)
        )
        src_task = asyncio.create_task(
            _run(["source", "list", "--json"], env=env, timeout=30)
        )

        ask_result, src_result = await asyncio.gather(ask_task, src_task)

        # Handle errors
        if ask_result["returncode"] != 0:
            err = ask_result.get("stderr") or ask_result.get("stdout") or "Unknown error"
            if "auth" in err.lower() or "login" in err.lower():
                return Response(
                    message="NotebookLM authentication required. Please re-authenticate via the 📓 button.",
                    break_loop=False,
                )
            return Response(message=f"NotebookLM error: {err}", break_loop=False)

        # Build UUID → title map from source list
        uuid_to_title: dict[str, str] = {}
        if src_result["returncode"] == 0 and src_result.get("data"):
            src_data = src_result["data"]
            if isinstance(src_data, dict):
                for src in src_data.get("sources", []):
                    sid = src.get("id", "")
                    title = src.get("title", "") or src.get("name", "")
                    if sid and title:
                        uuid_to_title[sid] = title

        # Parse ask response
        data: dict[str, Any] = {}
        if ask_result.get("data") and isinstance(ask_result["data"], dict):
            data = ask_result["data"]
        else:
            try:
                data = json.loads(ask_result.get("stdout", "{}"))
            except (json.JSONDecodeError, TypeError):
                data = {"answer": ask_result.get("stdout", "")}

        # Extract answer text (preserves inline [N] citations)
        answer = str(data.get("answer", data.get("response", ask_result.get("stdout", ""))))

        # Parse references: citation_num → (source_id, title)
        references = data.get("references", data.get("sources", []))
        citation_map: dict[int, tuple[str, str]] = {}
        for ref in references:
            if not isinstance(ref, dict):
                continue
            cnum = ref.get("citation_number")
            src_id = ref.get("source_id", "")
            if cnum is not None and src_id:
                title = uuid_to_title.get(src_id, src_id[:8] + "\u2026")
                citation_map[int(cnum)] = (src_id, title)

        # Build academic references: deduplicate sources, assign sequential ref numbers
        source_to_ref: dict[str, tuple[int, str]] = {}
        cnum_to_ref: dict[int, int] = {}

        for cnum in sorted(citation_map.keys()):
            src_id, title = citation_map[cnum]
            if src_id not in source_to_ref:
                ref_num = len(source_to_ref) + 1
                source_to_ref[src_id] = (ref_num, title)
            cnum_to_ref[cnum] = source_to_ref[src_id][0]

        # Replace inline citations in answer text
        def replace_citation(match: re.Match) -> str:
            nums_str = match.group(1)
            nums = [int(n.strip()) for n in nums_str.split(",") if n.strip().isdigit()]
            ref_nums = sorted(set(cnum_to_ref.get(n, n) for n in nums))
            return "[" + ", ".join(str(r) for r in ref_nums) + "]"

        if cnum_to_ref:
            answer = re.sub(r"\[(\d+(?:,\s*\d+)*)\]", replace_citation, answer)

        # Build formatted response
        parts = [answer]

        if source_to_ref:
            parts.append("\n\n**References:**")
            for ref_num, title in sorted(source_to_ref.values(), key=lambda x: x[0]):
                parts.append(f"[{ref_num}] {title}")

        return Response(message="\n".join(parts), break_loop=False)
