#!/usr/bin/env python3
"""sync_claude_settings.py — .lab-config.json の設定値から .claude/settings.json を自動生成・同期するツール

.claude/settings.json 自体はローカル環境の絶対パス（Google Driveのパスなど）を含むため、
git管理から除外します。代わりにテンプレートファイル .claude/settings.json.template と
本スクリプトを用いて、各ローカル環境で設定ファイルを同期します。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    root_dir = Path.cwd()  # install モデルでは tools/ が harness への symlink。記録層の設定を読み書きする
    config_file = root_dir / ".lab-config.json"
    template_file = root_dir / ".claude" / "settings.json.template"
    target_file = root_dir / ".claude" / "settings.json"

    # 1. Load config
    if not config_file.exists():
        print(f"Error: {config_file.name} not found. Please create it first.", file=sys.stderr)
        return 1

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error: Failed to parse {config_file.name}: {e}", file=sys.stderr)
        return 1

    drive_root = config.get("google_drive_root", "")
    drive_path = ""
    if drive_root:
        # Resolve the base folder of google_drive_root (strip 'experiments/' if present)
        # e.g., "~/Library/CloudStorage/GoogleDrive-<account>/共有ドライブ/<drive>/<notebook>/experiments/"
        # -> "~/Library/CloudStorage/GoogleDrive-<account>/共有ドライブ/<drive>/<notebook>/"
        p = Path(drive_root)
        if p.name == "experiments":
            drive_path = str(p.parent)
        elif "experiments" in p.parts:
            # If it's a subpath under experiments, or ends with experiments
            idx = p.parts.index("experiments")
            drive_path = str(Path(*p.parts[:idx]))
        else:
            drive_path = str(p)

    # 2. Load template
    defaults = {
        "permissions": {
            "additionalDirectories": [
                "../shared-kb"
            ]
        }
    }
    if template_file.exists():
        try:
            with open(template_file, "r", encoding="utf-8") as f:
                template = json.load(f)
                defaults.update(template)
        except Exception as e:
            print(f"Warning: Failed to load template {template_file.name}: {e}", file=sys.stderr)

    # Ensure permissions structure exists
    defaults.setdefault("permissions", {})
    dirs = defaults["permissions"].setdefault("additionalDirectories", [])

    # Convert paths to clean string format and avoid duplicates
    cleaned_dirs = []
    for d in dirs:
        if d not in cleaned_dirs:
            cleaned_dirs.append(d)

    if drive_path:
        # Avoid duplicate drive path
        drive_path_normalized = str(Path(drive_path))
        drive_path_posix = drive_path_normalized.replace("\\", "/")
        
        # Check if already exists in some format
        exists = False
        for existing in cleaned_dirs:
            ext_norm = str(Path(existing)).replace("\\", "/")
            if ext_norm.lower() == drive_path_posix.lower():
                exists = True
                break
        if not exists:
            # Add to the permissions
            cleaned_dirs.append(drive_path_normalized)
            print(f"Adding Drive path to additionalDirectories: {drive_path_normalized}")
    else:
        print("Warning: 'google_drive_root' is empty in config, skipping Drive permission sync.")

    defaults["permissions"]["additionalDirectories"] = cleaned_dirs

    # 3. Write target setting file
    try:
        target_file.parent.mkdir(parents=True, exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(defaults, f, indent=2, ensure_ascii=False)
        print(f"Successfully generated {target_file}")
    except Exception as e:
        print(f"Error: Failed to write {target_file.name}: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
