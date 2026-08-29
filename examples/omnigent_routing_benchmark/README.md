# Omnigent Routing Benchmark

This is a coding-tool project that treats an Omnigent-shaped smart routing
table as the harness being optimized. It is **not** a live `omni` server.

The candidate surface is `routing.json`: a `routes:select`-style table that
picks a harness+model for a task prompt. `route.py` is complete and stable.
It reads the table, applies the first matching rule (case-insensitive
substring), and prints the harness name on stdout:

```bash
python route.py --prompt "Refactor the auth module and add tests"
```

The baseline table only has a default cheap harness (`pi`), so harder prompts
fail until the optimizer writes better rules.

Write scope is single-class middleware (`routing.json` only). The leakage gate
forbids copying search or held-out task IDs into the winning table.

Run a deterministic smoke check:

```bash
uv run metaharness run examples/omnigent_routing_benchmark --backend fake --budget 1
```
