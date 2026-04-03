### notebooklm_ask:
Ask a question to Google NotebookLM, grounded in your notebook's sources.
Answers are generated exclusively from the sources in the selected notebook.
If no notebook is selected, prompt the user to select one first via the NotebookLM button.

**CRITICAL — Pass-Through Rule:**
NotebookLM is a full LLM. Its response is already grounded, structured, and cited.
- Return the answer **EXACTLY as received** — do NOT rewrite, rephrase, summarize, or reformat.
- Preserve ALL inline `[N]` citation markers — they are positionally matched to the References list below.
- Preserve the `**References:**` section exactly as returned — do NOT remove, merge, or reorder it.
- Do NOT add your own commentary, interpretation, or 'based on the notebook...' wrappers.
- Do NOT ask NotebookLM the same question multiple ways — one call per question.
- Pass the user's question DIRECTLY — no preprocessing, no reformulation.

**Arguments:**
- `question` (string, required): The question to ask — pass verbatim from the user
- `notebook_id` (string, optional): Notebook ID override. Uses the currently active notebook if empty.

**Usage:**
~~~json
{
    "thoughts": [
        "User wants to know about X from their NotebookLM sources.",
        "I will pass the question directly and return the response AS-IS."
    ],
    "headline": "Asking NotebookLM about X",
    "tool_name": "notebooklm_ask",
    "tool_args": {
        "question": "What does the research say about X?"
    }
}
~~~
