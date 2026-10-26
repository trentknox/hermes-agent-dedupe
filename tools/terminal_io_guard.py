"""Terminal IO policy guard.

Owner direction 2026-10-26: the box's IO saturation is self-inflicted — whole-home
``du``, whole-tree ``grep``/``rg`` scans, and analytic scans of the live
``state.db``. Enforce it in the terminal pre-execution guard chain so a bad
command is refused *before* it runs, under a bounded wait
(``run_bounded_sync`` / ``guard_timeout``).

Patterns are exact heuristics with bounded false-positive risk. Scoped commands
that legitimately need the home tree are not refused (see the acceptance test).
"""

from __future__ import annotations

import shlex
from typing import Optional

#: First non-option arguments that mean "the whole home tree".
_WHOLE_HOME_ARGS = {"/", "/home", "/home/ubuntu", "~", "$HOME"}
#: First non-option argument meaning "the entire filesystem".
_WHOLE_FS_ARGS = {"/", "~"}

#: Substring that identifies state.db as the live store (path component + file).
_STATE_DB_PATH = ".hermes/state.db"

#: SQL content that turns a sqlite3 read into an analytic scan of the live store.
_DB_ANALYTIC_MARKERS = (
    "dbstat",
    "vacuum",
    "reindex",
    "analyze",
    "pragma",
    ".dump",
    ".fullschema",
    ".schema",
    "from dbstat",
)

#: CLI binaries that take a path argument (as opposed to a SQL argument).
_DB_BINARIES = ("sqlite3", "sqlite")


def _first_non_option(argv: list[str]) -> Optional[str]:
    """Return the first non-option argument of an argv (everything after the binary)."""
    for arg in argv[1:]:
        if arg.startswith("-") and not arg.startswith("--"):
            continue
        return arg
    return None


def _norm_path(arg: str) -> str:
    """Normalize a path for comparison: drop a single trailing slash (keep '/')."""
    if arg == "/":
        return arg
    return arg.rstrip("/") or "/"


def deny_terminal_io(command: str) -> Optional[str]:
    """Return a refusal reason when *command* matches an IO-policy pattern, else None."""
    if not command:
        return None

    try:
        argv = shlex.split(command)
    except ValueError:
        # Unquoteable command: let the shell handle it; no policy opinion.
        return None
    if not argv:
        return None

    binary = argv[0]

    # 1) Whole-home du: argv[1:] == ['-x', '-sh', '/home/ubuntu'] -> first
    #    non-option argument is a whole-home path.
    if binary == "du":
        first = _first_non_option(argv)
        if first is not None:
            norm_first = _norm_path(first)
            if norm_first in _WHOLE_HOME_ARGS:
                return (
                    "io_guard_denied: 'du' of the whole home tree is not allowed; "
                    "scope the scan to the target directory"
                )

    # 2) Whole-tree recursive grep/rg: ANY non-option argument is a whole-home
    #    path or a bare '.' (no basename scope in the command).
    if binary in ("grep", "rg"):
        non_options = [a for a in argv[1:] if not a.startswith("-")]
        if any(a in _WHOLE_HOME_ARGS or a == "." for a in non_options):
            return (
                "io_guard_denied: recursive grep/rg over the whole home tree is "
                "not allowed; scope the pattern to the target directory"
            )

    # 3) Whole-filesystem find.
    if binary == "find":
        first = _first_non_option(argv)
        if first is not None:
            norm_first = _norm_path(first)
            if norm_first in _WHOLE_FS_ARGS:
                return (
                    "io_guard_denied: whole-filesystem 'find' is not allowed; scope 'find' "
                    "to the target directory"
                )

    # 4) Analytic scan of the live state.db: sqlite3 whose first argument resolves
    #    (after ~ / $HOME expansion) to the live store, with an analytic sql verb.
    if binary in _DB_BINARIES:
        db_path = _first_non_option(argv)
        if db_path and db_path.endswith(_STATE_DB_PATH):
            sql = " ".join(argv[2:]).lower()
            if any(marker in sql for marker in _DB_ANALYTIC_MARKERS):
                return (
                    "io_guard_denied: analytic scan of the live state.db is not "
                    "allowed; copy the store and scan the copy"
                )
    return None
