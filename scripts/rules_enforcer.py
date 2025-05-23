#!/usr/bin/env python3
"""Lightweight static checks to enforce critical repository rules.

Intended to run in CI *and* as a local pre-commit hook.

Current checks:
1. No direct calls to os.getenv outside src/config.py
2. All async tool functions accept `ctx` as first param
3. Every rules README is listed in .cursor/rules/00_index.mdc
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
RULES_DIR = REPO_ROOT / ".cursor" / "rules"
INDEX_FILE = RULES_DIR / "00_index.mdc"


class Violation(Exception):
    """Simple wrapper so we can raise violations easily."""


def fail(msg: str) -> None:
    raise Violation(msg)


# ---------------------------------------------------------------------------
# 1. getenv usage check
# ---------------------------------------------------------------------------
GETENV_PATTERN = re.compile(r"\bos\.getenv\(")


def check_getenv_usage() -> None:
    """Disallow os.getenv outside src/config.py."""
    for py_file in SRC_DIR.rglob("*.py"):
        if py_file == SRC_DIR / "config.py":
            continue
        txt = py_file.read_text(encoding="utf-8")
        if GETENV_PATTERN.search(txt):
            fail(f"os.getenv found in {py_file.relative_to(REPO_ROOT)} – use src.config.settings instead.")


# ---------------------------------------------------------------------------
# 2. Tool function signature check
# ---------------------------------------------------------------------------


def is_tool_module(path: Path) -> bool:
    """Identify modules that belong to tools package and are named tool.py."""
    try:
        parts = path.relative_to(SRC_DIR).parts
    except ValueError:
        return False
    return len(parts) >= 3 and parts[0] == "tools" and parts[-1] == "tool.py"


async_kw = {"async"}

def check_tool_signatures() -> None:
    for tool_file in SRC_DIR.rglob("tool.py"):
        if not is_tool_module(tool_file):
            continue
        mod = ast.parse(tool_file.read_text(encoding="utf-8"), filename=str(tool_file))
        for node in mod.body:
            if isinstance(node, ast.AsyncFunctionDef):
                # Skip dunder methods
                if node.name.startswith("__"):
                    continue
                if not node.args.args:
                    fail(
                        f"{tool_file.relative_to(REPO_ROOT)} – async function {node.name} missing arguments, expected ctx."
                    )
                first_arg = node.args.args[0].arg
                if first_arg != "ctx":
                    fail(
                        f"{tool_file.relative_to(REPO_ROOT)} – async function {node.name} must take 'ctx' as first parameter."
                    )


# ---------------------------------------------------------------------------
# 3. Rules index completeness
# ---------------------------------------------------------------------------


RULE_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def extract_index_paths() -> List[Path]:
    links: List[Path] = []
    for line in INDEX_FILE.read_text(encoding="utf-8").splitlines():
        match = RULE_LINK_PATTERN.search(line)
        if match:
            link_path = match.group(2)
            links.append((INDEX_FILE.parent / link_path).resolve())
    return links


def check_rules_index() -> None:
    declared = set(p.resolve() for p in extract_index_paths())
    # We only care about README.mdc files under rules/*/*
    actual = set(p.resolve() for p in RULES_DIR.glob("*/*/README.mdc"))
    missing = actual - declared
    if missing:
        rel = ", ".join(str(p.relative_to(RULES_DIR)) for p in sorted(missing))
        fail(f"00_index.mdc is missing links to: {rel}")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        check_getenv_usage()
        check_tool_signatures()
        check_rules_index()
    except Violation as e:
        print(f"Rule violation: {e}", file=sys.stderr)
        sys.exit(1)
    print("All rule checks passed ✅")


if __name__ == "__main__":
    main() 