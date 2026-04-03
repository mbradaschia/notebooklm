"""Shared CLI runner for notebooklm-py commands."""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

# Binary resolution order:
# 1. Plugin config override (if set)
# 2. Plugin-local venv (installed by execute.py)
# 3. Skill venv (legacy fallback)
PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_VENV_BINARY = os.path.join(PLUGIN_DIR, ".venv", "bin", "notebooklm")
SKILL_VENV_BINARY = "/a0/usr/skills/notebooklm/.venv/bin/notebooklm"
DEFAULT_AUTH_DIR = os.path.expanduser("~/.notebooklm")

# Per-chat isolated NOTEBOOKLM_HOME directories
CHAT_HOME_BASE = Path("/a0/tmp/notebooklm/home")
STORAGE_DIR = Path("/a0/tmp/notebooklm")


def _find_binary() -> str:
    """Find the notebooklm binary in order of preference."""
    if os.path.isfile(PLUGIN_VENV_BINARY):
        return PLUGIN_VENV_BINARY
    if os.path.isfile(SKILL_VENV_BINARY):
        return SKILL_VENV_BINARY
    return PLUGIN_VENV_BINARY  # Default path even if not yet installed


def get_binary(agent=None) -> str:
    """Get notebooklm binary path from plugin config or auto-detect."""
    if agent:
        try:
            from helpers.plugins import get_plugin_config
            config = get_plugin_config("notebooklm", agent=agent) or {}
            configured = config.get("notebooklm_binary", "").strip()
            if configured and os.path.isfile(configured):
                return configured
        except Exception:
            pass
    return _find_binary()


def _get_auth_storage_path(agent=None) -> str:
    """Resolve the storage_state.json path from config or default."""
    if agent:
        try:
            from helpers.plugins import get_plugin_config
            config = get_plugin_config("notebooklm", agent=agent) or {}
            path = config.get("auth_storage_path", "").strip()
            if path:
                if os.path.isdir(path):
                    path = os.path.join(path, "storage_state.json")
                if os.path.isfile(path):
                    return path
        except Exception:
            pass
    # Default location
    default = os.path.join(DEFAULT_AUTH_DIR, "storage_state.json")
    if os.path.isfile(default):
        return default
    return ""


def get_storage_flag(agent=None) -> list:
    """Get --storage flag if custom auth path is configured."""
    path = _get_auth_storage_path(agent)
    if path:
        return ["--storage", path]
    return []


def get_active_notebook(agent=None) -> tuple[str, str]:
    """Get the currently active notebook (id, title) — per-chat ONLY. No global fallback."""
    if agent:
        try:
            context_id = getattr(getattr(agent, "context", None), "id", None)
            if context_id:
                ctx_file = STORAGE_DIR / f"{context_id}.json"
                if ctx_file.exists():
                    state = json.loads(ctx_file.read_text())
                    nb_id = state.get("active_notebook_id", "").strip()
                    nb_title = state.get("active_notebook_title", "").strip()
                    if nb_id:
                        return nb_id, nb_title
        except Exception:
            pass
    return "", ""


def setup_chat_home(context_id: str, notebook_id: str, notebook_title: str, agent=None) -> str:
    """Create an isolated NOTEBOOKLM_HOME for a specific chat context.

    This is the RELIABLE way to ensure the correct notebook is used by the CLI.
    Uses NOTEBOOKLM_HOME env var instead of the unreliable -n flag.

    Returns the path to the isolated home directory.
    """
    home_dir = CHAT_HOME_BASE / context_id
    home_dir.mkdir(parents=True, exist_ok=True)

    # Symlink storage_state.json from persistent auth path
    auth_path = _get_auth_storage_path(agent)
    storage_link = home_dir / "storage_state.json"
    if auth_path and os.path.isfile(auth_path):
        # Remove stale symlink or file if needed
        if storage_link.exists() or storage_link.is_symlink():
            if storage_link.is_symlink() and os.readlink(str(storage_link)) == auth_path:
                pass  # Already correct symlink
            else:
                storage_link.unlink()
                storage_link.symlink_to(auth_path)
        else:
            storage_link.symlink_to(auth_path)

    # Write context.json with CORRECT notebook — no conversation_id (forces fresh start)
    context_json = home_dir / "context.json"
    context_data = {
        "notebook_id": notebook_id,
        "title": notebook_title,
    }
    context_json.write_text(json.dumps(context_data, ensure_ascii=False))

    return str(home_dir)


def ensure_auth_dir(persistent_path: str = ""):
    """Ensure ~/.notebooklm is properly set up for auth storage."""
    link = DEFAULT_AUTH_DIR

    if os.path.islink(link):
        target = os.readlink(link)
        if os.path.exists(target):
            return
        os.unlink(link)
    elif os.path.isdir(link):
        if persistent_path and os.path.isdir(persistent_path):
            contents = os.listdir(link)
            if not contents:
                os.rmdir(link)
                os.symlink(persistent_path, link)
                return
        return

    if not os.path.exists(link):
        if persistent_path and os.path.isdir(persistent_path):
            os.symlink(persistent_path, link)
        else:
            os.makedirs(link, mode=0o700, exist_ok=True)


async def run_cli(
    args: list,
    agent=None,
    timeout: int = 30,
    input_data: Optional[str] = None,
    notebook_id: str = "",
    notebook_title: str = "",
) -> dict:
    """Run notebooklm CLI command and return parsed output.

    When notebook_id is provided, uses NOTEBOOKLM_HOME isolation to ensure
    the correct notebook context is used (more reliable than -n flag).

    Args:
        args: CLI arguments (e.g. ["ask", "--new", "question", "--json"])
        agent: Agent instance for config lookup
        timeout: Command timeout in seconds
        input_data: Optional stdin data
        notebook_id: If set, creates isolated NOTEBOOKLM_HOME for this notebook
        notebook_title: Title for the context.json in isolated home

    Returns:
        dict with keys: returncode, stdout, stderr, data (parsed JSON or None)
    """
    # Auto-restore symlink if auth_storage_path is configured
    persistent_path = ""
    if agent:
        try:
            from helpers.plugins import get_plugin_config
            config = get_plugin_config("notebooklm", agent=agent) or {}
            persistent_path = config.get("auth_storage_path", "").strip()
            if persistent_path and os.path.isdir(persistent_path):
                persistent_path = os.path.join(persistent_path, "storage_state.json")
                persistent_path = os.path.dirname(persistent_path)  # back to dir
        except Exception:
            pass
    ensure_auth_dir(persistent_path)

    binary = get_binary(agent)

    # Build environment for subprocess
    env = os.environ.copy()

    if notebook_id and agent:
        # Use NOTEBOOKLM_HOME isolation — most reliable approach
        # SKILL.md Known Bug #1: -n flag is less reliable than `use` or NOTEBOOKLM_HOME
        context_id = getattr(getattr(agent, "context", None), "id", None) or "default"
        chat_home = setup_chat_home(context_id, notebook_id, notebook_title, agent)
        env["NOTEBOOKLM_HOME"] = chat_home
        # No --storage flag needed — NOTEBOOKLM_HOME handles it via symlinked storage_state.json
        cmd = [binary] + args
    else:
        # No notebook isolation — use --storage flag for auth only
        storage = get_storage_flag(agent)
        cmd = [binary] + storage + args

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE if input_data else asyncio.subprocess.DEVNULL,
        env=env,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=input_data.encode() if input_data else None),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "data": None,
        }

    result = {
        "returncode": proc.returncode,
        "stdout": stdout.decode().strip(),
        "stderr": stderr.decode().strip(),
    }

    if result["stdout"]:
        try:
            result["data"] = json.loads(result["stdout"])
        except json.JSONDecodeError:
            result["data"] = None
    else:
        result["data"] = None

    return result
