#!/usr/bin/env python3
"""
Check whether the Russian translations are in sync with their English sources.

Every translated document is registered in ``docs/translations.json`` together with a hash of
its English source as it stood when the translation was written, plus the commit that source
was last changed in. Drift is detected from the hash, so the check behaves the same in a full
clone, a shallow clone and an export; the commit is only an anchor for showing what changed.

Usage:
    python3 scripts/check_translations.py            # report stale translations
    python3 scripts/check_translations.py --update   # record the current sources as synced
    python3 scripts/check_translations.py --markdown # report as Markdown for a job summary

Exit codes:
    0: all translations are up to date
    1: at least one translation is stale
    2: the manifest is missing or malformed
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "docs" / "translations.json"
DIFF_LIMIT = 4000


def git(*args: str) -> str:
    """Run a git command in the repository and return its stripped stdout."""
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def source_hash(source: str) -> str:
    """Return the SHA-256 of an English source file, or "" if it cannot be read."""
    try:
        return hashlib.sha256((REPO_ROOT / source).read_bytes()).hexdigest()
    except OSError:
        return ""


def load_manifest() -> list[dict[str, str]]:
    """Load the translation manifest, exiting with code 2 if it cannot be read."""
    try:
        return json.loads(MANIFEST_PATH.read_text())["translations"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {MANIFEST_PATH.relative_to(REPO_ROOT)}: {exc}", file=sys.stderr)
        sys.exit(2)


def save_manifest(entries: list[dict[str, str]]) -> None:
    """Write the translation manifest back to disk with a trailing newline."""
    MANIFEST_PATH.write_text(json.dumps({"translations": entries}, indent=2, ensure_ascii=False) + "\n")


def find_stale(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return the manifest entries whose English source no longer matches its recorded hash."""
    return [e for e in entries if source_hash(e["source"]) not in ("", e["source_sha256"])]


def source_diff(entry: dict[str, str]) -> str:
    """Return the diff of an entry's source since its recorded commit, or "" if unavailable."""
    commit = entry.get("source_commit", "")
    if not commit:
        return ""
    return git("diff", commit, "--", entry["source"])[:DIFF_LIMIT]


def report(stale: list[dict[str, str]]) -> None:
    """Print a human-readable summary of the stale translations."""
    if not stale:
        print("All translations are up to date.")
        return
    print(f"{len(stale)} translation(s) out of date:\n")
    for entry in stale:
        print(f"- {entry['source']} -> {entry['translation']}")
        print(f"  diff: git diff {entry.get('source_commit', 'HEAD')} -- {entry['source']}\n")


def markdown_report(stale: list[dict[str, str]]) -> str:
    """Render the stale translations as Markdown, for a GitHub Actions job summary."""
    lines = ["## Translations out of sync", "", "These translations no longer match their English sources.", ""]
    for entry in stale:
        lines += [f"### `{entry['source']}` -> `{entry['translation']}`", ""]
        diff = source_diff(entry)
        lines += ["```diff", diff, "```", ""] if diff else ["The English source changed.", ""]
    lines += [
        "Update each translation, then run `python3 scripts/check_translations.py --update`",
        "and commit the translation together with `docs/translations.json`.",
    ]
    return "\n".join(lines)


def main() -> int:
    """Compare each translation against its source and optionally record a fresh sync."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="record the current sources as synced")
    parser.add_argument("--markdown", action="store_true", help="report as Markdown for a job summary")
    args = parser.parse_args()

    entries = load_manifest()
    if args.update:
        for entry in entries:
            entry["source_sha256"] = source_hash(entry["source"])
            entry["source_commit"] = git("log", "-1", "--format=%H", "--", entry["source"])
        save_manifest(entries)
        print(f"Recorded {len(entries)} translation(s) as up to date.")
        return 0

    stale = find_stale(entries)
    if args.markdown:
        print(markdown_report(stale) if stale else "## Translations are up to date")
    else:
        report(stale)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
