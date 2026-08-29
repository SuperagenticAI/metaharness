---
name: metaharness-optimize
description: Run metaharness from an Omnigent agent to optimize harness files in the current workspace. Use when a host wants the metaharness kernel without wrapping a proprietary proposer.
---

# Optimize With metaharness

Call the packaged CLI from the host agent working directory. The kernel is
`optimize_harness`; this skill is only a wrapper around `metaharness run`.

```bash
metaharness run . --backend fake --budget 1
```

For a live proposer, pass `--backend codex` or `--backend omnigent` according
to the project's `metaharness.json`. Do not add an AgentSky or HarnessRouter
proposer backend; those hosts should embed the same Python or UHP contract.

Expected artifacts after a run:

- `runs/<name>/` with candidate workspaces and diffs
- `best_candidate_id` and `best_objective` on stdout
- ledger via `metaharness ledger runs/<name>`
