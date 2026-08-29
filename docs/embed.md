# Embedding metaharness In A Host Runtime

The optimization kernel is already `optimize_harness(...)` in `metaharness.api`.
Host agent runtimes should call that kernel. They should not grow a proprietary
proposer backend inside this repository.

## Three Host Adapters, One Kernel

1. **Python import.** An in-process host (Omnigent worker, AgentSky runner, or a
   custom loop) imports `optimize_harness`, points it at a baseline workspace,
   and reads `OptimizeResult`.
2. **Omnigent skill.** An Omnigent agent wraps `metaharness run` as a skill.
   See `examples/embed_runtime/omnigent_skill/SKILL.md`.
3. **UHP harness `metaharness.optimize`.** HarnessRouter-style hosts should
   expose a UHP method that forwards the same request shape into
   `optimize_harness` or `metaharness run`.

AgentSky should call the same Python or UHP contract. This repository does
**not** wrap AgentSky's cloud API as a proposer, and it does not add a
first-class HarnessRouter proposer backend.

A tiny host that already has agent files and calls the kernel is
`examples/embed_runtime/optimize_host.py`.

## Request / Response Sketch

This is a documentation sketch, not a new wire protocol. Hosts can map it onto
Python kwargs, a UHP method, or `metaharness run` plus a project directory.

```json
{
  "request": {
    "baseline_files": {
      "routing.json": "{\"default\": {\"harness\": \"pi\"}, \"rules\": []}",
      "route.py": "# stable router"
    },
    "tasks": [
      {
        "id": "route-simple",
        "type": "command",
        "command": "python route.py --prompt \"say hello and list files\""
      }
    ],
    "budget": 1,
    "write_scope": {
      "allowed_write_paths": [{"path": "routing.json", "class": "middleware"}],
      "write_scope_mode": "single-class"
    },
    "leakage_gate": true
  },
  "response": {
    "best_candidate_id": "c0001",
    "best_objective": 1.0,
    "diffs": ["routing.json"],
    "ledger_path": "runs/host-run/indexes/leaderboard.json"
  }
}
```

The coding-tool project layout (`metaharness.json`, `tasks.json`, `baseline/`)
is the usual way to supply those fields on disk. `OptimizeResult` returns the
winning candidate id, objective, workspace, and run directory; diffs and the
ledger live under that run directory.

## What This Repo Does Not Do

- No AgentSky cloud proposer.
- No HarnessRouter / UHP proposer backend in-tree.
- Omnigent remains an experimental *proposer* (`OmnigentCliBackend`) **and**
  can be a *target* (routing tables, agent configs). Those are different roles.
