"""Tests for the terminal IO policy guard.

Run (from this repo root):
    .venv/bin/python -m pytest tests/agent/test_terminal_io_guard.py -q
"""

import pytest

from tools.terminal_io_guard import deny_terminal_io
from tools.terminal_tool import _Rejected, _pre_exec_block

#: Commands that must be refused (self-inflicted whole-tree IO, observed on the box).
REFUSED = [
    "du -x -sh /home/ubuntu",
    "du -x -sh /home/ubuntu/",
    "du -x -sh /home",
    "du -x -sh ~",
    "du -x -sh $HOME",
    "du -x -sh /",
    "grep -rl \"test gate\" . --include=*.py",
    "grep -rl 6910f835 .",
    "grep -rIlE SUPABASE_URL /home/ubuntu --include=*.env",
    "rg -l something /home/ubuntu",
    "find / -name \"*.py\"",
    "find ~ -name foo",
    "sqlite3 /home/ubuntu/.hermes/state.db SELECT name, SUM(pgsize) s FROM dbstat GROUP BY name ORDER BY s DESC LIMIT 20;",
    "sqlite3 ~/.hermes/state.db .dump",
]

#: Commands that must be allowed (legit scoped use).
ALLOWED = [
    "du -sm /home/ubuntu/ccm-agents-records",
    "du -sm /home/ubuntu/cybercitymedia",
    "grep -rn \"foo\" /home/ubuntu/cybercitymedia",
    "find /home/ubuntu/ccm-agents-records -name \"*.py\"",
    "sqlite3 /home/ubuntu/.hermes/state.db '.tables'",
    "sqlite3 /home/ubuntu/.hermes/state.db 'SELECT name FROM sqlite_master LIMIT 5'",
]


def test_refused_patterns_are_denied():
    for cmd in REFUSED:
        assert deny_terminal_io(cmd), f"expected refusal for {cmd!r}"


def test_scoped_commands_are_allowed():
    for cmd in ALLOWED:
        assert deny_terminal_io(cmd) is None, f"expected allowance for {cmd!r}"


@pytest.mark.parametrize("cmd", REFUSED)
def test_pre_exec_block_refuses(cmd):
    with pytest.raises(_Rejected):
        _pre_exec_block(
            cmd,
            env=None,
            env_type="local",
            cwd="/tmp",
            workdir=None,
            session_key="",
        )


def test_pre_exec_block_allows_scoped():
    _pre_exec_block(
        "du -sm /home/ubuntu/ccm-agents-records",
        env=None,
        env_type="local",
        cwd="/tmp",
        workdir=None,
        session_key="",
    )
