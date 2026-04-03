import { createStore } from "/js/AlpineStore.js";

const API_BASE = "/plugins/notebooklm";

export const store = createStore("notebooklm", {
    // ── State ────────────────────────────────────────────
    notebooks: [],
    activeNotebookId: "",
    activeNotebookTitle: "",
    loading: false,
    authenticated: false,
    authChecked: false,

    // Modal state
    searchQuery: "",
    sortField: "created_at",
    sortAsc: false,

    // File upload auth state
    uploadState: "idle",        // idle | uploading | success | error
    uploadError: "",
    uploadDragover: false,
    pasteText: "",

    init() {
        this.checkAuth();
        this._startContextWatcher();
    },

    // ── Context Watcher ─────────────────────────────────
    // Detects chat switches (SPA-style, no full page reload) and syncs
    // the active notebook state from the backend for the new context.
    _currentContextId: "",

    _startContextWatcher() {
        this._currentContextId = typeof window.getContext === "function" ? window.getContext() : "";
        setInterval(() => {
            const newCtx = typeof window.getContext === "function" ? window.getContext() : "";
            if (newCtx && newCtx !== this._currentContextId) {
                this._currentContextId = newCtx;
                this._syncContextNotebook(newCtx);
            }
        }, 2000);
    },

    async _syncContextNotebook(contextId) {
        try {
            const res = await fetchApi(`${API_BASE}/notebooklm_set_active`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "get_active", context_id: contextId }),
            });
            const data = await res.json();
            this.activeNotebookId = data.active_notebook_id || "";
            this.activeNotebookTitle = data.active_notebook_title || "";
        } catch {
            this.activeNotebookId = "";
            this.activeNotebookTitle = "";
        }
    },

    // ── Auth ─────────────────────────────────────────────
    async checkAuth() {
        try {
            const res = await fetchApi(`${API_BASE}/notebooklm_auth`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({}),
            });
            const data = await res.json();
            this.authenticated = !!data.authenticated;
        } catch {
            this.authenticated = false;
        }
        this.authChecked = true;
    },

    forceReauth() {
        this.authenticated = false;
        this.authChecked = true;
        this.uploadState = '';
        this.uploadError = '';
        this.pasteText = '';
    },


    // ── File Upload / Paste Auth ─────────────────────────
    async pasteCookieJson() {
        const text = this.pasteText.trim();
        if (!text) return;
        try {
            const json = JSON.parse(text);
            await this._sendCookieJson(json);
        } catch (e) {
            this.uploadState = "error";
            this.uploadError = `Invalid JSON: ${e.message}`;
            toastFrontendError(this.uploadError, "NotebookLM");
        }
    },

    // ── File Upload Auth ─────────────────────────────────
    async _sendCookieJson(json) {
        this.uploadState = "uploading";
        this.uploadError = "";
        try {
            const res = await fetchApi(`${API_BASE}/notebooklm_upload_auth`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ cookies_json: json }),
            });
            const data = await res.json();
            if (data.error) {
                this.uploadState = "error";
                this.uploadError = data.error;
                toastFrontendError(data.error, "NotebookLM");
                return;
            }
            this.uploadState = "success";
            toastFrontendSuccess(data.message || "Authentication saved!", "NotebookLM");
            this.authenticated = true;
            setTimeout(() => { this.fetchNotebooks(); }, 1200);
        } catch (e) {
            this.uploadState = "error";
            this.uploadError = `Upload failed: ${e.message}`;
            toastFrontendError(this.uploadError, "NotebookLM");
        }
    },

    async uploadCookieFile(event) {
        const file = event.target.files[0];
        if (!file) return;
        try {
            const text = await file.text();
            const json = JSON.parse(text);
            await this._sendCookieJson(json);
        } catch (e) {
            this.uploadState = "error";
            this.uploadError = `Invalid JSON file: ${e.message}`;
        }
        // Reset file input so same file can be re-selected
        event.target.value = "";
    },

    async dropCookieFile(event) {
        this.uploadDragover = false;
        const file = event.dataTransfer.files[0];
        if (!file) return;
        try {
            const text = await file.text();
            const json = JSON.parse(text);
            await this._sendCookieJson(json);
        } catch (e) {
            this.uploadState = "error";
            this.uploadError = `Invalid JSON file: ${e.message}`;
        }
    },


    // ── Notebooks ────────────────────────────────────────
    async fetchNotebooks() {
        this.loading = true;
        try {
            const res = await fetchApi(`${API_BASE}/notebooklm_notebooks`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({}),
            });
            const data = await res.json();
            if (data.error) {
                toastFrontendError(data.error, "NotebookLM");
                this.notebooks = [];
            } else {
                this.notebooks = data.notebooks || [];
            }
        } catch (e) {
            toastFrontendError(`Failed to fetch notebooks: ${e.message}`, "NotebookLM");
            this.notebooks = [];
        }
        this.loading = false;
    },

    // ── Filtered + Sorted ────────────────────────────────
    get filteredNotebooks() {
        let list = [...this.notebooks];
        const q = (this.searchQuery || "").toLowerCase().trim();
        if (q) {
            list = list.filter(nb => (nb.title || "").toLowerCase().includes(q));
        }
        const field = this.sortField;
        const asc = this.sortAsc;
        list.sort((a, b) => {
            let va = a[field], vb = b[field];
            if (field === "title") {
                va = (va || "").toLowerCase();
                vb = (vb || "").toLowerCase();
                return asc ? va.localeCompare(vb) : vb.localeCompare(va);
            }
            if (field === "created_at") {
                va = va || ""; vb = vb || "";
                return asc ? va.localeCompare(vb) : vb.localeCompare(va);
            }
            if (field === "is_owner") {
                va = va ? 1 : 0; vb = vb ? 1 : 0;
                return asc ? va - vb : vb - va;
            }
            return 0;
        });
        return list;
    },

    toggleSort(field) {
        if (this.sortField === field) {
            this.sortAsc = !this.sortAsc;
        } else {
            this.sortField = field;
            this.sortAsc = field === "title";
        }
    },

    sortIcon(field) {
        if (this.sortField !== field) return "unfold_more";
        return this.sortAsc ? "arrow_upward" : "arrow_downward";
    },

    // ── Select / Deselect ────────────────────────────────
    async selectNotebook(nb) {
        try {
            const res = await fetchApi(`${API_BASE}/notebooklm_set_active`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ notebook_id: nb.id, notebook_title: nb.title, context_id: (typeof window.getContext === "function" ? window.getContext() : "") }),
            });
            const data = await res.json();
            if (data.error) {
                toastFrontendError(data.error, "NotebookLM");
                return;
            }
            this.activeNotebookId = nb.id;
            this.activeNotebookTitle = nb.title;
            toastFrontendSuccess(`Notebook selected: ${nb.title}`, "NotebookLM");
            if (typeof closeModal === "function") closeModal();
        } catch (e) {
            toastFrontendError(`Selection failed: ${e.message}`, "NotebookLM");
        }
    },

    async deselectNotebook() {
        try {
            await fetchApi(`${API_BASE}/notebooklm_set_active`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ notebook_id: "", notebook_title: "", context_id: (typeof window.getContext === "function" ? window.getContext() : "") }),
            });
            this.activeNotebookId = "";
            this.activeNotebookTitle = "";
            toastFrontendSuccess("Notebook deselected", "NotebookLM");
        } catch (e) {
            toastFrontendError(`Deselect failed: ${e.message}`, "NotebookLM");
        }
    },

    // ── Modal lifecycle ──────────────────────────────────
    onModalOpen() {
        this.searchQuery = "";
        this.authStep = "idle";
        this.authError = "";
        this.authVncUrl = "";
        if (!this.authChecked) this.checkAuth();
        if (this.camofoxAvailable === null) this.checkCamofox();
        if (this.authenticated) this.fetchNotebooks();
    },

    onModalClose() {
        if (this.authStep === "login_opened") {
            this.cancelCamofoxLogin();
        }
    },

    // ── Helpers ──────────────────────────────────────────
    get hasActiveNotebook() {
        return !!this.activeNotebookId;
    },

    get truncatedTitle() {
        const t = this.activeNotebookTitle || '';
        return t.length > 15 ? t.substring(0, 15) + '...' : t;
    },

    formatDate(dateStr) {
        if (!dateStr) return "—";
        try {
            const d = new Date(dateStr);
            if (isNaN(d.getTime())) return dateStr;
            return d.toLocaleDateString(undefined, {
                year: "numeric", month: "short", day: "numeric",
                hour: "2-digit", minute: "2-digit",
            });
        } catch {
            return dateStr;
        }
    },

    truncateId(id) {
        if (!id) return "";
        return id.length > 12 ? id.slice(0, 12) + "…" : id;
    },
});
