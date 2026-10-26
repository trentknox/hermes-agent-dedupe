# Take

## Live evidence (verified this turn)
- Swap 6.2/8G used, load ~12.7/14.4, wa spiking, disk 83% (34G free) — IO thrashing, not disk-full.
- Cause confirmed live: `du -x -sh /home/ubuntu` (whole-home, child of the Hermes gateway) and `sqlite3 /home/ubuntu/.hermes/state.db ... dbstat` (analytic scan of the live store, ~3h+). Both `timeout 300` wrappers, children of the gateway PID.
- Killed both (SIGTERM, exit -15); verified gone. No whole-home du / state.db analytic scan may run again on this box.

## Owned-code fix (Hermes tool policy)
Guard wired into the terminal pre-execution chain (`tools/terminal_tool.py::_pre_exec_block`), before any command runs; refuses with `_Rejected` under the existing bounded `run_bounded_sync` guard:
- `tools/terminal_io_guard.py`: `deny_terminal_io()` rejects whole-home `du`, recursive `grep`/`rg` over the home tree, whole-filesystem `find /`, `find ~`, and analytic reads of the live `state.db`.
- Unit coverage: 14 refused patterns + 6 allowlisted scoped commands → **17 passed**; ruff clean.

Deliverables (remote pull-only — delivered via branch + head + file state):
Branch: fix/terminal-io-policy-guard-20261026
Head:   a91f8abb4fcf3819aa07678a4a7bd77f93fbf40c
Files:  tools/terminal_io_guard.py, tools/terminal_tool.py (+10 wired), tests/agent/test_terminal_io_guard.py

## Verification status
- Guard logic: verified (17/17 tests; no false positives on scoped du/grep/find/sqlite).
- Live effect: verification_pending — the running gateway still has the old code in memory (`sys.modules` frozen at boot); requires a gateway restart, which is owner-gated. No restart performed.

## Next owned slice
<@U0C7QD2HN03> — no mergeable PR is open in the CCM loop right now (digest shows #4975/#4965/#4966 drafts, #4967 Vercel-unstable). Give me one concrete owned CCM slice with verified capabilities and I'll start it on the next tick.
