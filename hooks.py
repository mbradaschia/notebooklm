"""Lifecycle hooks for the NotebookLM plugin."""

import asyncio
import sys
import os


async def install() -> None:
    """Run once after the plugin is installed to set up the venv and dependencies."""
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    execute_py = os.path.join(plugin_dir, "execute.py")
    proc = await asyncio.create_subprocess_exec(
        sys.executable, execute_py,
        cwd=plugin_dir,
    )
    await proc.wait()
