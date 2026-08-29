# Embed Runtime

Tiny host example: an Omnigent / UHP-like process that already has a workspace
of agent files and calls `optimize_harness` in-process.

This is not a new proposer backend. AgentSky and HarnessRouter should use the
same Python import or UHP `metaharness.optimize` contract. See
[docs/embed.md](../../docs/embed.md).

```bash
PYTHONPATH=src python examples/embed_runtime/optimize_host.py
```
