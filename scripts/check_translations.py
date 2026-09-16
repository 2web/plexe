#!/usr/bin/env python3
"""
Check whether the Russian translations are in sync with their English sources.

Every translated document is registered in ``docs/translations.json`` together with the
commit that last touched its English source at the time the translation was written.
This script compares that recorded commit with the source's current last commit and
reports every pair that has drifted.

Usage:
    python3 scripts/check_translations.py            # report stale translations
    python3 scripts/check_translations.py --update   # record the current commits as synced
    python3 scripts/check_translations.py --markdown # report as a Markdown summary

Exit codes:
    0: all translations are up to date
    1: at least one translation is stale
    2: the manifest is missing or malformed
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "docs" / "translations.json"
DIFF_LIMIT = 4000


def last_commit(source: str) -> str:
    """Return the hash of the most recent commit touching ``source``, or "" if unknown."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", source],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def load_manifest() -> list[dict[str, str]]:
    """Load the translation manifest, exiting with code 2 if it cannot be read."""
    try:
        entries = json.loads(MANIFEST_PATH.read_text())["translations"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {MANIFEST_PATH.relative_to(REPO_ROOT)}: {exc}", file=sys.stderr)
        sys.exit(2)
    return entries


def save_manifest(entries: list[dict[str, str]]) -> None:
    """Write the translation manifest back to disk with a trailing newline."""
    MANIFEST_PATH.write_text(json.dumps({"translations": entries}, indent=2, ensure_ascii=False) + "\n")


def find_stale(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return the manifest entries whose English source moved on since the last sync."""
    stale = []
    for entry in entries:
        current = last_commit(entry["source"])
        if current and current != entry["source_commit"]:
            stale.append({**entry, "current_commit": current})
    return stale


def source_diff(entry: dict[str, str]) -> str:
    """Return the diff of an entry's English source between its synced and current commit."""
    result = subprocess.run(
        ["git", "diff", f"{entry['source_commit']}..{entry['current_commit']}", "--", entry["source"]],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def markdown_report(stale: list[dict[str, str]]) -> str:
    """Render the stale translations as Markdown, for a GitHub Actions job summary."""
    lines = ["## Translations out of sync", "", "These translations no longer match their English sources.", ""]
    for entry in stale:
        lines += [f"### `{entry['source']}` -> `{entry['translation']}`", ""]
        diff = source_diff(entry)
        if diff:
            lines += ["```diff", diff[:DIFF_LIMIT], "```"]
            if len(diff) > DIFF_LIMIT:
                lines.append(f"_Diff truncated; run `git diff {entry['source_commit']}..{entry['current_commit']}`._")
        lines.append("")
    lines += [
        "Update each translation, then run `python3 scripts/check_translations.py --update`",
        "and commit the translation together with `docs/translations.json`.",
    ]
    return "\n".join(lines)


def report(stale: list[dict[str, str]]) -> None:
    """Print a human-readable summary of the stale translations."""
    if not stale:
        print("All translations are up to date.")
        return
    print(f"{len(stale)} translation(s) out of date:\n")
    for entry in stale:
        short = f"{entry['source_commit'][:8]}..{entry['current_commit'][:8]}"
        print(f"- {entry['source']} -> {entry['translation']}")
        print(f"  changed since last sync ({short})")
        print(f"  diff: git diff {entry['source_commit']}..{entry['current_commit']} -- {entry['source']}\n")


def main() -> int:
    """Compare each translation against its source and optionally record a fresh sync."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="record current source commits as synced")
    parser.add_argument("--markdown", action="store_true", help="report as Markdown for a job summary")
    args = parser.parse_args()

    entries = load_manifest()
    if args.update:
        for entry in entries:
            entry["source_commit"] = last_commit(entry["source"]) or entry["source_commit"]
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
