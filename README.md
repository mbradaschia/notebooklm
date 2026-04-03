# NotebookLM Plugin for Agent Zero

Integrate [Google NotebookLM](https://notebooklm.google.com/) into Agent Zero. Select notebooks from the chat UI, ask questions grounded exclusively in your notebook sources, and generate artifacts.

Powered by [notebooklm-py](https://github.com/teng-lin/notebooklm-py) — an unofficial Python CLI for Google NotebookLM.

---

## Features

- **📓 Notebook Selector** — Browse, search, and select notebooks from the chat input area
- **🤖 Grounded Q&A** — `notebooklm_ask` routes questions through NotebookLM; answers are grounded exclusively in your sources with inline citations `[1]` and a References section
- **🔬 Specialized Agent** — Auto-activates the `notebooklm_researcher` profile when a notebook is selected; auto-deactivates on deselect
- **📦 Self-Contained** — Installs its own virtual environment; no external dependencies required

---

## Quick Start

1. **Enable** the plugin in A0 Settings → Plugins
2. **Run Setup** — Click the Execute button on the plugin card to install `notebooklm-py`
3. **Authenticate** — See [Authentication](#authentication) below
4. **Select a Notebook** — Click the 📓 icon in the chat input area
5. **Ask Questions** — The agent answers using only your notebook sources

---

## Authentication

NotebookLM requires a Google account. Run `notebooklm login` **on your local machine** to generate the auth file, then upload it to A0.

### Step 1 — Generate `storage_state.json` on your local machine

```bash
pip install notebooklm-py
notebooklm login
# A browser window opens — log in to Google
# File saved to: ~/.notebooklm/storage_state.json
```

### Step 2 — Upload to A0

1. Refresh the A0 web UI
2. Click the **📓 NotebookLM** icon in the chat input area
3. The auth panel appears — drag & drop `~/.notebooklm/storage_state.json` onto the upload zone, or click **Browse File**
4. Click **Re-check Auth** — your notebooks load automatically

### Verify Authentication

```bash
/a0/usr/skills/notebooklm/.venv/bin/notebooklm auth check --json
```

### Persistence Across Restarts

Auth is saved to `/a0/usr/secrets/notebooklm/storage_state.json` which is on A0's persistent volume. Your session survives container restarts.

---

## Using the Plugin

### Selecting a Notebook

1. Click the **📓 NotebookLM** button in the chat input area
2. The notebook selector modal opens — search, sort by title or date, click a row to select
3. The button label changes to **NLM: My Notebook Title** (truncated) and turns purple
4. The agent automatically switches to the `notebooklm_researcher` profile
5. To deselect, open the modal and click **✕ Deselect** in the active notebook banner

### Asking Questions

Once a notebook is selected, ask naturally. The response comes directly from NotebookLM — **inline citations `[1]` `[2]` and the References section are returned verbatim and never rewritten.**

```
You: What are the main findings of the study?

Agent: The study found three main results:

1. Participants in the intervention group showed a 34% improvement in outcomes [1]
2. The effect was strongest in the 25–35 age cohort [2]
3. Long-term retention at 6 months was 78% compared to 52% in the control group [1][3]

**References:**
[1] Smith et al. (2023) — Randomized Controlled Trial of...
[2] Figure 4: Subgroup Analysis by Age
[3] Table 2: Follow-up Outcomes at 6 Months
```

---

## Usage Guide — Best Way to Ask Each Thing

### 💬 Q&A — Asking Questions

Just type your question. NotebookLM answers from your notebook sources only.

```
What are the main themes in my notebook?
Summarize the key arguments across all sources.
What does the research say about transformer attention mechanisms?
How do the two papers differ in their methodology?
List all datasets mentioned with their sample sizes.
What open research questions are identified in my sources?
```

> **Tip**: NotebookLM is itself an LLM — you can ask it complex reasoning questions, comparisons, and synthesis tasks directly. No need to simplify.

---

### 📎 Adding Sources

Add any URL, YouTube video, local file, or pasted text to the active notebook:

```
Add this article to my notebook: https://arxiv.org/abs/2310.06825
Add this YouTube video as a source: https://youtube.com/watch?v=abc123
Add the file /home/user/paper.pdf to my notebook
Add this text as a source: "My research notes on..."
Add this Google Drive document: https://docs.google.com/document/d/...
```

Search the web or Google Drive and import the results automatically:
```
Search the web for "quantum computing recent breakthroughs" and add the sources
Do a deep web search for "LLM fine-tuning techniques" and add everything you find
Search my Google Drive for "project proposal" and add the docs
```

---

### 🎙️ Generate Audio (Podcast)

Creates a conversational audio overview between two AI hosts.

```
Generate a podcast from my notebook
Create an audio overview focusing on chapter 3
Make a short podcast overview of my sources
Generate a debate-format audio about the main controversies in my notebook
Create a funny casual podcast for a non-technical audience
```

Format options: `deep-dive` (default), `brief`, `critique`, `debate`  
Length options: `short`, `default`, `long`

---

### 🎬 Generate Video

```
Generate a video overview of my notebook
Create a short explainer video about the key concepts
Make a video summary for a general audience
```

---

### 📊 Generate Report

Formats: `briefing-doc` (default), `study-guide`, `blog-post`, or a custom description.

```
Generate a briefing document from my notebook
Create a study guide from my sources
Write a blog post based on my notebook
Generate a white paper on the main findings — focus on practical implications
What report topics would work well for this notebook?
```

> Use "What report topics would work well?" to get AI-suggested topics based on your notebook content before generating.

---

### 📝 Generate Quiz

```
Generate a quiz from my notebook
Create a quiz focusing on vocabulary terms
Make a hard quiz testing the key concepts
Generate more questions with medium difficulty
```

Difficulty: `easy`, `medium`, `hard` — Quantity: `fewer`, `standard`, `more`

---

### 🃏 Generate Flashcards

```
Generate flashcards from my notebook
Create flashcards for the key definitions in my sources
Make flashcards focusing on the methodology section
```

---

### 🗺️ Generate Mind Map

```
Generate a mind map of my notebook
Create a mind map showing the connections between main concepts
Download the mind map as a JSON file
```

---

### 📊 Generate Infographic

```
Generate an infographic summarizing my notebook
Create a visual overview of the key statistics in my sources
```

---

### 📋 Generate Slide Deck

```
Generate a slide deck from my notebook
Create presentation slides for a 10-minute talk on my sources
Make slides for an executive audience
```

---

### 📈 Generate Data Table

```
Extract all numerical results from my notebook into a data table
Generate a data table of all experiments and their outcomes
Create a comparison table of the methodologies in my sources
```

---

### ⬇️ Downloading Artifacts

After generating, download the output:

```
Download the latest podcast
Download the report as a markdown file
Download all quiz questions
Download the slide deck PDF
Download the mind map JSON
Export the report to Google Docs
```

---

### 📓 Notes

Create and manage notes inside your notebook:

```
Create a note: "Remember to check this claim against source 3"
Create a note titled "Key Questions" with: What is the mechanism for X?
List all my notes in this notebook
Show me the content of my note about key questions
```

---

### 🔗 Sharing

```
Share my notebook publicly
Disable public sharing for my notebook
Share my notebook with colleague@example.com as a viewer
Share my notebook with editor@example.com as an editor
Show the current sharing status of my notebook
Remove access for colleague@example.com
```

---

### ⚙️ Configure Chat Mode

Change how NotebookLM responds in the current notebook:

```
Set the chat mode to learning guide
Make responses more concise
Switch to detailed mode for longer responses
Set a custom persona: "Act as a PhD supervisor reviewing my literature"
Reset to default chat mode
```

Modes: `default`, `learning-guide`, `concise`, `detailed`

---

### 📚 Notebook Management

```
List all my notebooks
Create a new notebook called "Machine Learning Papers"
Rename my current notebook to "Q1 Research"
Delete notebook abc123
Get a summary of my current notebook
Get a summary with suggested topics
```

---

## Configuration

Access via A0 Settings → Plugins → NotebookLM:

| Setting | Description | Default |
|---------|-------------|---------|
| `notebooklm_binary` | Path to notebooklm CLI binary (empty = auto-detect) | `""` |
| `auth_storage_path` | Auth storage directory or file path | `/a0/usr/secrets/notebooklm` |
| `auto_switch_agent` | Auto-switch to `notebooklm_researcher` on notebook selection | `true` |

---

## Plugin Structure

```
notebooklm/
├── plugin.yaml                    # Plugin manifest
├── default_config.yaml            # Default settings
├── execute.py                     # Auto-installer & setup script
├── hooks.py                       # Lifecycle hooks (install)
├── SKILL.md                       # Full CLI skill reference
├── README.md                      # This file
├── LICENSE                        # MIT License
├── agents/
│   └── notebooklm_researcher/
│       └── agent.yaml             # Specialized researcher profile
├── api/
│   ├── notebooklm_auth.py         # Auth check endpoint
│   ├── notebooklm_notebooks.py    # List notebooks endpoint
│   ├── notebooklm_set_active.py   # Set active notebook endpoint
│   └── notebooklm_upload_auth.py  # Cookie/storage_state upload endpoint
├── tools/
│   └── notebooklm_ask.py          # Grounded Q&A tool
├── helpers/
│   ├── cli.py                     # Shared CLI runner
│   └── extract_auth.py            # Cookie extraction utility
├── prompts/
│   └── agent.system.tool.notebooklm_ask.md
├── extensions/
│   ├── python/system_prompt/
│   │   └── _20_notebooklm_context.py  # Injects active notebook into system prompt
│   └── webui/chat-input-bottom-actions-end/
│       └── notebooklm-button.html     # Chat toolbar button
└── webui/
    ├── config.html                # Plugin settings UI
    ├── notebooklm-modal.html      # Notebook selector modal
    └── notebooklm-store.js        # Alpine.js store
```

---

## How It Works

1. **Notebook selection** is stored in the plugin config (`active_notebook_id`, `active_notebook_title`)
2. The system prompt extension (`_20_notebooklm_context.py`) injects the active notebook context into every agent turn
3. When the agent receives a question relevant to the notebook, it calls `notebooklm_ask` with the question and notebook ID
4. `notebooklm_ask` calls the `notebooklm chat` CLI, which sends the question to NotebookLM's API and returns a grounded answer with source references
5. Source UUIDs are resolved to real titles via parallel CLI calls and formatted as numbered citations

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Notebooks not loading after upload | Click **Re-check Auth** in the modal |
| "Authentication expired" error | Re-run `notebooklm login` locally and re-upload `storage_state.json` |
| Modal shows auth panel even after upload | Refresh the page (Ctrl+R) to reset Alpine.js state |
| `notebooklm_ask` times out | The notebook may have many sources; try a more specific question |
| Binary not found | Set `notebooklm_binary` in plugin settings to the full path: `/a0/usr/skills/notebooklm/.venv/bin/notebooklm` |

---

## Acknowledgments

Built on [notebooklm-py](https://github.com/teng-lin/notebooklm-py) by [teng-lin](https://github.com/teng-lin). NotebookLM is a product of Google.

## License

MIT — see [LICENSE](LICENSE)
