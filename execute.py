"""NotebookLM Plugin — Setup & Maintenance Script.

Run via the Plugins UI "Execute" button.
Safe to run multiple times (idempotent).

Steps:
  1. Install notebooklm-py into a dedicated venv (if not present)
  2. Optionally install Playwright browsers (needed only for `notebooklm login`)
  3. Ensure auth directory exists
  4. Verify authentication status
"""

import os
import subprocess
import sys
import json
import shutil

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(PLUGIN_DIR, ".venv")
VENV_BIN = os.path.join(VENV_DIR, "bin")
VENV_PYTHON = os.path.join(VENV_BIN, "python")
NLM_BINARY = os.path.join(VENV_BIN, "notebooklm")
DEFAULT_AUTH_DIR = os.path.expanduser("~/.notebooklm")
PACKAGE = "notebooklm-py"


def step(n: int, title: str):
    print(f"\n{'='*60}")
    print(f"  Step {n}: {title}")
    print(f"{'='*60}")


def run(cmd: list, **kwargs) -> subprocess.CompletedProcess:
    """Run a command, print it, and return the result."""
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, text=True, **kwargs)


def install_notebooklm():
    """Install notebooklm-py into a plugin-local venv."""
    step(1, "Install notebooklm-py")

    if os.path.isfile(NLM_BINARY):
        # Check version
        result = run([NLM_BINARY, "--version"], capture_output=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"  ✓ Already installed: {version}")
            # Try to upgrade
            print("  → Checking for updates...")
            run([VENV_PYTHON, "-m", "pip", "install", "--upgrade", "--quiet", PACKAGE])
            result2 = run([NLM_BINARY, "--version"], capture_output=True)
            if result2.returncode == 0 and result2.stdout.strip() != version:
                print(f"  ✓ Upgraded to: {result2.stdout.strip()}")
            else:
                print(f"  ✓ Already at latest version")
            return True

    # Create venv if needed
    if not os.path.isfile(VENV_PYTHON):
        print("  → Creating virtual environment...")
        result = run([sys.executable, "-m", "venv", VENV_DIR])
        if result.returncode != 0:
            print("  ✗ Failed to create venv")
            return False

    # Install package
    print(f"  → Installing {PACKAGE}...")
    result = run([VENV_PYTHON, "-m", "pip", "install", "--quiet", PACKAGE])
    if result.returncode != 0:
        print(f"  ✗ Failed to install {PACKAGE}")
        return False

    if os.path.isfile(NLM_BINARY):
        result = run([NLM_BINARY, "--version"], capture_output=True)
        print(f"  ✓ Installed: {result.stdout.strip() if result.returncode == 0 else 'unknown version'}")
        return True
    else:
        print("  ✗ Binary not found after install")
        return False


def install_playwright():
    """Install Playwright browsers (optional — only needed for `notebooklm login`)."""
    step(2, "Install Playwright Browsers (optional)")

    # Check if playwright is available
    result = run(
        [VENV_PYTHON, "-c", "import playwright; print('ok')"],
        capture_output=True,
    )
    if result.returncode != 0:
        print("  ⊘ Playwright not installed — skipping browser install")
        print("  ℹ Playwright is only needed for interactive login via `notebooklm login`")
        print("  ℹ You can also authenticate by importing cookies (see plugin skill docs)")
        return True

    # Check if browsers are already installed
    pw_bin = os.path.join(VENV_BIN, "playwright")
    if not os.path.isfile(pw_bin):
        print("  ⊘ Playwright CLI not found — skipping")
        return True

    result = run([VENV_PYTHON, "-m", "playwright", "install", "chromium"], capture_output=True)
    if result.returncode == 0:
        print("  ✓ Chromium browser installed for Playwright")
    else:
        print("  ⚠ Playwright browser install had issues (non-critical)")
        print(f"    {result.stderr.strip()[:200] if result.stderr else ''}")

    # Install system deps (best-effort)
    result = run(
        [VENV_PYTHON, "-m", "playwright", "install-deps", "chromium"],
        capture_output=True,
    )
    if result.returncode == 0:
        print("  ✓ System dependencies installed")
    else:
        print("  ⚠ System deps install had issues (may need manual install)")

    return True


def ensure_auth():
    """Ensure auth directory exists and check auth status."""
    step(3, "Authentication")

    # Try to read custom auth path from plugin config
    custom_auth_path = ""
    try:
        config_paths = [
            os.path.join(PLUGIN_DIR, "config.json"),  # Plugin config
            os.path.join(PLUGIN_DIR, "default_config.yaml"),  # Default
        ]
        for cp in config_paths:
            if os.path.isfile(cp):
                if cp.endswith(".json"):
                    with open(cp) as f:
                        data = json.load(f)
                elif cp.endswith(".yaml") or cp.endswith(".yml"):
                    # Simple YAML parsing for key: value
                    with open(cp) as f:
                        data = {}
                        for line in f:
                            line = line.strip()
                            if ":" in line and not line.startswith("#"):
                                k, v = line.split(":", 1)
                                data[k.strip()] = v.strip().strip('"').strip("'")
                else:
                    continue
                custom_auth_path = data.get("auth_storage_path", "").strip()
                if custom_auth_path:
                    break
    except Exception:
        pass

    # Determine effective auth dir
    if custom_auth_path and os.path.isdir(custom_auth_path):
        auth_dir = custom_auth_path
        print(f"  → Using custom auth path: {auth_dir}")
    else:
        auth_dir = DEFAULT_AUTH_DIR

    # Handle symlink or directory
    if os.path.islink(auth_dir):
        target = os.readlink(auth_dir)
        if os.path.exists(target):
            print(f"  ✓ Auth symlink: {auth_dir} → {target}")
        else:
            print(f"  ⚠ Broken symlink: {auth_dir} → {target}")
            os.unlink(auth_dir)
            os.makedirs(auth_dir, mode=0o700, exist_ok=True)
            print(f"  → Created fresh auth directory: {auth_dir}")
    elif os.path.isdir(auth_dir):
        print(f"  ✓ Auth directory exists: {auth_dir}")
    else:
        os.makedirs(auth_dir, mode=0o700, exist_ok=True)
        print(f"  → Created auth directory: {auth_dir}")

    # Check for storage_state.json
    storage_file = os.path.join(auth_dir, "storage_state.json")
    if os.path.isfile(storage_file):
        print(f"  ✓ Auth file found: {storage_file}")
    else:
        print(f"  ⚠ No auth file yet: {storage_file}")
        print("  ℹ To authenticate, use one of these methods:")
        print("    1. Interactive login: notebooklm login (requires Playwright + GUI)")
        print("    2. Import cookies: copy storage_state.json to ~/.notebooklm/")
        print("    3. Environment variable: export NOTEBOOKLM_AUTH_JSON='{...}'")
        print("    See the plugin skill docs for detailed instructions.")
        return True

    # Verify auth with CLI
    if os.path.isfile(NLM_BINARY):
        print("  → Verifying authentication...")
        result = run([NLM_BINARY, "auth", "check", "--json"], capture_output=True)
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                status = data.get("status", "unknown")
                if status == "ok":
                    print(f"  ✓ Authentication verified (status: {status})")
                    # Show details if available
                    details = data.get("details", {})
                    if details:
                        cookie_count = details.get("total_cookies", "?")
                        domains = details.get("domains", "?")
                        print(f"    Cookies: {cookie_count} across {domains} domains")
                else:
                    print(f"  ⚠ Auth status: {status}")
                    print(f"    {result.stdout[:200]}")
            except json.JSONDecodeError:
                if "ok" in result.stdout.lower():
                    print("  ✓ Authentication appears valid")
                else:
                    print(f"  ⚠ Could not parse auth response: {result.stdout[:200]}")
        else:
            print(f"  ⚠ Auth check failed (exit code {result.returncode})")
            if result.stderr:
                print(f"    {result.stderr[:200]}")
            print("  ℹ You may need to re-authenticate (see plugin skill docs)")

    return True


def update_default_config():
    """Update default_config.yaml to point to the plugin-local venv binary."""
    import yaml  # noqa: might not be available
    config_path = os.path.join(PLUGIN_DIR, "default_config.yaml")
    if os.path.isfile(config_path):
        with open(config_path) as f:
            content = f.read()
        # Update binary path to point to plugin-local venv
        old_binary = '/a0/usr/skills/notebooklm/.venv/bin/notebooklm'
        if old_binary in content and NLM_BINARY != old_binary:
            content = content.replace(old_binary, NLM_BINARY)
            with open(config_path, 'w') as f:
                f.write(content)
            print(f"  → Updated default binary path to: {NLM_BINARY}")


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║          NotebookLM Plugin — Setup & Maintenance        ║")
    print("║          https://github.com/teng-lin/notebooklm-py      ║")
    print("╚══════════════════════════════════════════════════════════╝")

    ok = True

    # Step 1: Install notebooklm-py
    if not install_notebooklm():
        print("\n✗ Installation failed. Cannot continue.")
        return 1

    # Step 2: Install Playwright (optional)
    install_playwright()

    # Step 3: Auth
    ensure_auth()

    print("\n" + "=" * 60)
    print("  Setup Complete!")
    print("=" * 60)
    print("\n  Next steps:")
    print("  1. If not authenticated: see SKILL.md for auth methods")
    print("  2. Refresh the A0 web UI")
    print("  3. Click the NotebookLM icon in the chat input area")
    print("  4. Select a notebook and start asking questions!")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
