# Omnigent Agent Benchmark

This example treats an Omnigent agent directory as the harness being optimized.
The baseline is intentionally incomplete: it has a minimal `config.yaml`,
thin instructions, and a placeholder skill.

Run a deterministic smoke check:

```bash
uv run metaharness run examples/omnigent_agent_benchmark --backend fake --budget 1
```

Run with Omnigent as the proposer:

```bash
uv run metaharness run examples/omnigent_agent_benchmark --backend omnigent --budget 1
```

The objective is to improve the agent specification and support files so the
agent has explicit instructions, safer filesystem scope, an Omnigent policy,
and a reviewer skill.
