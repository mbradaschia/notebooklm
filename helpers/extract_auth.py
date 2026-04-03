#!/usr/bin/env python3
"""Extract Google auth cookies from browser storage or an existing file.

Bundled with the NotebookLM plugin. Based on the extract_auth.py from
https://github.com/teng-lin/notebooklm-py.

Usage:
    # After logging into Google via browser_agent:
    python /a0/usr/plugins/notebooklm/helpers/extract_auth.py

    # Custom output path:
    python /a0/usr/plugins/notebooklm/helpers/extract_auth.py --output /custom/path/storage_state.json

    # From an existing storage_state.json:
    python /a0/usr/plugins/notebooklm/helpers/extract_auth.py --from-file /path/to/existing/storage_state.json
"""

import argparse
import json
import os
import shutil
import stat
import sys
from pathlib import Path


def get_default_output() -> Path:
    """Get default output path respecting NOTEBOOKLM_HOME."""
    home = os.environ.get("NOTEBOOKLM_HOME", os.path.expanduser("~/.notebooklm"))
    return Path(home) / "storage_state.json"


def find_browser_storage() -> Path | None:
    """Find browser storage state files from various browser automation tools."""
    import glob

    candidates = [
        Path("/tmp/playwright_storage_state.json"),
        Path("/a0/tmp/browser/storage_state.json"),
        Path("/root/.cache/ms-playwright/storage_state.json"),
    ]

    # Also check for recently modified storage_state.json files
    for pattern in [
        "/tmp/**/storage_state*.json",
        "/a0/tmp/**/storage_state*.json",
    ]:
        candidates.extend(Path(p) for p in glob.glob(pattern, recursive=True))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def validate_storage_state(data: dict) -> bool:
    """Validate that storage state contains required Google cookies."""
    cookies = data.get("cookies", [])
    cookie_names = {c.get("name", "") for c in cookies}
    required = {"SID"}
    missing = required - cookie_names

    if missing:
        print(f"⚠️  Missing required cookies: {missing}")
        return False

    google_cookies = [c for c in cookies if "google" in c.get("domain", "").lower()]
    print(f"✅ Found {len(google_cookies)} Google cookies")

    key_names = {
        "SID", "HSID", "SSID", "APISID", "SAPISID",
        "__Secure-1PSID", "__Secure-3PSID",
    }
    found_key = key_names & cookie_names
    print(f"✅ Key cookies present: {', '.join(sorted(found_key))}")

    return True


def install_storage_state(source_path: Path, output_path: Path) -> bool:
    """Copy and secure a storage_state.json file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(str(output_path.parent), stat.S_IRWXU)  # 700

    try:
        data = json.loads(source_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"❌ Error reading {source_path}: {e}")
        return False

    if not validate_storage_state(data):
        print("❌ Storage state validation failed")
        return False

    if source_path != output_path:
        shutil.copy2(str(source_path), str(output_path))

    os.chmod(str(output_path), stat.S_IRUSR | stat.S_IWUSR)  # 600
    print(f"✅ Auth saved to: {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Extract/install NotebookLM auth credentials"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help=f"Output path (default: {get_default_output()})",
    )
    parser.add_argument(
        "--from-file", "-f",
        type=Path,
        default=None,
        help="Import from existing storage_state.json",
    )
    parser.add_argument(
        "--backup", "-b",
        action="store_true",
        help="Also backup to /a0/usr/workdir/.notebooklm_auth_backup.json",
    )

    args = parser.parse_args()
    output = args.output or get_default_output()

    if args.from_file:
        if not args.from_file.exists():
            print(f"❌ File not found: {args.from_file}")
            sys.exit(1)
        source = args.from_file
    else:
        source = find_browser_storage()
        if not source:
            print("❌ No browser storage state found.")
            print("\nTo authenticate, either:")
            print(
                "  1. Use browser_agent to log into Google, then run this script"
            )
            print(
                "  2. Import existing auth: "
                "python extract_auth.py --from-file /path/to/storage_state.json"
            )
            print("  3. Use NOTEBOOKLM_AUTH_JSON env var with inline JSON")
            sys.exit(1)

    print(f"📋 Source: {source}")
    print(f"📋 Output: {output}")

    if not install_storage_state(source, output):
        sys.exit(1)

    if args.backup:
        backup_path = Path("/a0/usr/workdir/.notebooklm_auth_backup.json")
        shutil.copy2(str(output), str(backup_path))
        os.chmod(str(backup_path), stat.S_IRUSR | stat.S_IWUSR)
        print(f"✅ Backup saved to: {backup_path}")

    print("\n🎉 Done! Verify with: notebooklm auth check --test")


if __name__ == "__main__":
    main()
