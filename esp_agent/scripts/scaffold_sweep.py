"""
Scaffold Sweep — §4 (Mock/Hardcode Lifecycle Management) of Agent_Debugging/debug_methods.md.

Scans the codebase for machine-readable `# MOCK_SCAFFOLD:` markers and prints a single
inventory of every mock/hardcoded fallback still present, with its reason / expiry / ref.
This turns "is this value real or mocked?" from a multi-file investigation into one command,
and gives an explicit tracked backlog of scaffolding rather than TODOs buried in code.

Marker convention (one line, above the fallback):
    # MOCK_SCAFFOLD: <reason> | reason: <...> | expiry: <condition> | ref: <pointer>

Usage:
    .venv\\Scripts\\python.exe scripts\\scaffold_sweep.py            # list inventory, exit 0
    .venv\\Scripts\\python.exe scripts\\scaffold_sweep.py --strict   # exit 1 if any markers found (CI gate)
    .venv\\Scripts\\python.exe scripts\\scaffold_sweep.py --root .    # scan a specific root
"""

import argparse
import os
import re
import sys

MARKER = "MOCK_SCAFFOLD:"
EXCLUDE_DIRS = {".venv", "__pycache__", ".git", "node_modules", "dist", ".next", "build", ".mypy_cache", ".pytest_cache"}
SCAN_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".yaml", ".yml"}

_FIELD_RE = re.compile(r"(reason|expiry|ref)\s*:\s*", re.IGNORECASE)


def parse_marker(text: str) -> dict:
    """Extract reason/expiry/ref from a marker line's text (best-effort)."""
    after = text.split(MARKER, 1)[1].strip() if MARKER in text else text.strip()
    fields = {"summary": after, "reason": "", "expiry": "", "ref": ""}
    # Split on the pipe-delimited key: value segments.
    parts = [p.strip() for p in after.split("|")]
    if parts:
        fields["summary"] = parts[0]
    for p in parts:
        m = _FIELD_RE.match(p)
        if m:
            key = m.group(1).lower()
            fields[key] = p[m.end():].strip()
    return fields


def _is_real_marker(line: str) -> bool:
    """
    Count only genuine comment markers, not prose/docstring mentions of the marker string.
    A real marker line, once stripped, begins with a comment token and contains the marker.
    """
    stripped = line.lstrip()
    if MARKER not in stripped:
        return False
    return stripped.startswith(("#", "//", "*", "<!--"))


def scan(root: str):
    self_file = os.path.abspath(__file__)
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() not in SCAN_EXTS:
                continue
            path = os.path.join(dirpath, fn)
            # The sweep tool itself and the verification module legitimately mention the marker
            # string as documentation — skip them to avoid self-referential false positives.
            if os.path.abspath(path) == self_file or fn == "handoff.py":
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for lineno, line in enumerate(f, 1):
                        if _is_real_marker(line):
                            findings.append((os.path.relpath(path, root), lineno, parse_marker(line)))
            except Exception:
                continue
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
                    help="Root directory to scan (default: the esp_agent package root)")
    ap.add_argument("--strict", action="store_true",
                    help="Exit non-zero if any scaffold markers are found (use as a CI gate).")
    args = ap.parse_args()

    findings = scan(args.root)

    print("=" * 78)
    print(f"MOCK_SCAFFOLD sweep — root: {args.root}")
    print("=" * 78)

    if not findings:
        print("No MOCK_SCAFFOLD markers found. Codebase is scaffold-free.")
        sys.exit(0)

    by_file = {}
    for rel, lineno, fields in findings:
        by_file.setdefault(rel, []).append((lineno, fields))

    for rel in sorted(by_file):
        print(f"\n{rel}")
        for lineno, fields in by_file[rel]:
            print(f"  L{lineno}: {fields['summary']}")
            if fields["reason"]:
                print(f"        reason : {fields['reason']}")
            if fields["expiry"]:
                print(f"        expiry : {fields['expiry']}")
            if fields["ref"]:
                print(f"        ref    : {fields['ref']}")

    print("\n" + "-" * 78)
    print(f"TOTAL: {len(findings)} scaffold marker(s) across {len(by_file)} file(s).")
    print("Each is an explicit, tracked fallback — not a hidden hardcode. Resolve when its")
    print("'expiry' condition is met (e.g. live cced_esp ingestion guaranteed).")

    if args.strict:
        print("\n[STRICT] Failing because unresolved scaffold markers exist.")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
