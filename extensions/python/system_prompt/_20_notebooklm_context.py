"""Inject NotebookLM grounding rules into system prompt — always reflects current notebook state.

MUST be a class subclassing Extension — A0 uses load_classes_from_folder which
only discovers Extension subclasses. Function-based extensions are silently ignored.
"""
from __future__ import annotations

import json
from pathlib import Path

from helpers.extension import Extension
from agent import LoopData

STORAGE_DIR = Path("/a0/tmp/notebooklm")


class NotebooklmContext(Extension):
    """Inject current NotebookLM notebook state and grounding rules into system prompt each turn."""

    async def execute(
        self,
        system_prompt: list[str] = [],
        loop_data: LoopData = LoopData(),
        **kwargs,
    ):
        if not self.agent:
            return

        notebook_id = ""
        notebook_title = ""

        # Always re-read from per-chat file — reflects the notebook selected RIGHT NOW
        # (user may have changed it in the UI since the last turn)
        try:
            context_id = getattr(getattr(self.agent, "context", None), "id", None)
            if context_id:
                ctx_file = STORAGE_DIR / f"{context_id}.json"
                if ctx_file.exists():
                    state = json.loads(ctx_file.read_text())
                    notebook_id = state.get("active_notebook_id", "").strip()
                    notebook_title = state.get("active_notebook_title", "").strip()
        except Exception:
            pass

        if not notebook_id:
            # No notebook selected — inject a reminder so the agent prompts the user
            system_prompt.append("""
## NotebookLM — No Notebook Selected

No NotebookLM notebook is currently selected.
- Do NOT attempt to call `notebooklm_ask` — it will fail without an active notebook.
- If the user asks a question that requires notebook sources, tell them:
  > "Please select a NotebookLM notebook first — click the 📓 NotebookLM button in the chat input area."
""")
            return

        system_prompt.append(f"""
## NotebookLM — Active Notebook (Current Turn)

> ⚠️ This is re-evaluated every turn. The user may have changed the notebook in the UI.
> Always use the notebook shown HERE — never use a notebook ID from a previous turn.

**Currently selected**: `{notebook_id}` — "{notebook_title}"

### First Thing — Check This Notebook
Before answering any question about notebook content:
1. Note the notebook above — it is the CURRENT selection as of this message.
2. If the user's question references a different notebook or topic, use THIS notebook.
3. If the user asks to switch or change notebooks, do NOT change anything — tell them to use the 📓 NotebookLM button in the chat input area to select a different notebook.

### Grounding Rules — MANDATORY
1. Use the `notebooklm_ask` tool to answer ANY question about notebook content.
2. Pass the user's question **directly and verbatim** — do not rephrase, summarize, or add context.
3. NEVER answer from your own training knowledge — all responses must be grounded in notebook sources.
4. If `notebooklm_ask` returns no relevant information or an error, say so honestly.

### Pass-Through Rule — MANDATORY
NotebookLM is itself a full LLM. Its response is already grounded, structured, and cited.
- Return the answer **EXACTLY as received** — do NOT rewrite, rephrase, summarize, or reformat.
- Preserve ALL inline `[N]` citation markers exactly as they appear.
- Preserve the `**References:**` section exactly — do NOT remove, merge, reorder, or re-list it.
- Do NOT add commentary, interpretation, or "based on the sources..." wrappers.
- Do NOT add your own Sources section — the tool already returns References.

### Artifact Generation — ASYNC (MANDATORY)
Artifact generation (audio, video, report, quiz, flashcards, mind-map, infographic, slide-deck, data-table) runs on NotebookLM servers and can take minutes.
**NEVER block the conversation waiting for an artifact. Always use this async pattern:**

1. Do NOT call `notebooklm_ask` for the generate command in the main turn.
2. Instead, create a **scheduler adhoc task** (`scheduler:create_adhoc_task`) with:
   - `name`: e.g. `notebooklm_generate_audio`
   - `dedicated_context`: `true` ← **CRITICAL** — runs in its own isolated agent context, never blocks the main conversation
   - `system_prompt`: `You are a background NotebookLM artifact generation monitor. When generation completes, use notify_user to alert the user. Use the notebooklm_ask tool to run CLI commands.`
   - `prompt`: `Use notebooklm_ask to run this command: generate <type> "<description>" -n {notebook_id} --wait\nWhen done, use notify_user with title "NotebookLM" and message: "Your <type> is ready! Ask me to download it.". If it fails, notify with the error.`
3. Immediately tell the user: *"Generation started in the background — I'll notify you when it's ready (typically 2–5 min for audio/video)."*

**Why**: `--no-wait` is already the default, but the user still needs to be notified when done. The scheduler task runs in its own context, doesn't block the conversation, uses notify_user when complete.
""")
