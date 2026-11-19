#!/usr/bin/env python3
"""Find URLs and common public hosts that need an airgap review explanation."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys

URL_RE = re.compile(r"(?:https?|wss?)://[^\s<>\"'`]+", re.IGNORECASE)
HOST_RE = re.compile(
    r"(?i)(?<![\w.-])(?:"
    r"(?:[a-z0-9-]+\.)*cdn(?:[a-z0-9-]*)\.[a-z0-9.-]+|"
    r"(?:[a-z0-9-]+\.)*(?:googleapis|unpkg|jsdelivr|cloudflare|"
    r"npmjs|pythonhosted)\.[a-z0-9.-]+|"
    r"(?:deb\.debian\.org|archive\.ubuntu\.com|registry\.npmjs\.org|"
    r"pypi\.org|files\.pythonhosted\.org)"
    r")"
)
ALLOW_RE = re.compile(r"\bairgap-ok\s*:\s*(\S.*?)\s*(?:-->|\*/)?\s*$", re.IGNORECASE)
# XML namespace URIs (xmlns="http://www.w3.org/2000/svg") are identifiers, never fetched.
XMLNS_RE = re.compile(r"xmlns(?::[\w.-]+)?\s*=\s*[\"']$")
SKIPPED_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules",
    "__pycache__", ".tox", ".mypy_cache", ".pytest_cache", ".cache",
    ".next", ".turbo", "coverage", "test-results", "playwright-report",
}


def matches_for(line: str) -> list[str]:
    all_urls = list(URL_RE.finditer(line))
    is_ns = lambda m: bool(XMLNS_RE.search(line[max(0, m.start() - 40):m.start()]))
    urls = [m for m in all_urls if not is_ns(m)]
    found = [match.group(0).rstrip(").,;]}") for match in urls]
    for match in HOST_RE.finditer(line):
        # Report a host inside an already matched URL once, not twice.
        if any(
            url.start() <= match.start() and match.end() <= url.end()
            for url in all_urls  # includes xmlns identifiers, so their hosts aren't re-reported
        ):
            continue
        found.append(match.group(0))
    return list(dict.fromkeys(found))


def iter_files(roots: list[Path], errors: list[str]):
    for root in roots:
        if not root.exists():
            errors.append(f"path does not exist: {root}")
            continue
        if root.is_file():
            yield root
            continue
        for directory, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(
                name for name in dirnames if name not in SKIPPED_DIRS
            )
            for filename in sorted(filenames):
                path = Path(directory) / filename
                if not path.is_symlink():
                    yield path


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def scan(paths: list[Path]) -> tuple[int, int, int]:
    unexplained = 0
    explained = 0
    scanned = 0
    errors: list[str] = []

    for path in iter_files(paths, errors):
        try:
            data = path.read_bytes()
        except OSError as error:
            errors.append(f"{display_path(path)}: {error}")
            continue
        if b"\0" in data[:8192]:  # binary
            continue
        text = data.decode("utf-8", errors="replace")
        scanned += 1
        for number, line in enumerate(text.splitlines(), start=1):
            found = matches_for(line)
            if not found:
                continue
            allow = ALLOW_RE.search(line)
            if allow:
                explained += len(found)
                verdict = f"EXPLAINED: {allow.group(1).strip()}"
            else:
                unexplained += len(found)
                verdict = "UNEXPLAINED"
            for match in found:
                print(f"{display_path(path)}:{number}: {match} [{verdict}]")

    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    print(
        f"Scanned {scanned} text files: {unexplained} unexplained, "
        f"{explained} explained, {len(errors)} read/path errors.",
        file=sys.stderr,
    )
    return unexplained, explained, len(errors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    unexplained, _explained, errors = scan(args.paths)
    if errors:
        return 2
    return 1 if unexplained else 0


if __name__ == "__main__":
    raise SystemExit(main())
