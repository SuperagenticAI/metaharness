# Providers

## Provider Model

`metaharness` separates the optimization loop from the system that edits files.
That editing system is called a proposer backend.

Current backends:

- `CodexExecBackend` (validated)
- `GeminiCliBackend` (experimental)
- `OmnigentCliBackend` (experimental)
- `FakeBackend` (deterministic testing backend)
- extension backends via `backend_plugins` (`module:callable` factories)

## Codex

Codex is the primary backend in this repository.
Documented benchmark results are centered on hosted Codex and local Codex over Ollama.

Hosted probe:

```bash
uv run metaharness smoke codex ./my-coding-tool-optimizer --probe-only
```

Hosted run:

```bash
uv run metaharness run \
  ./my-coding-tool-optimizer \
  --backend codex \
  --hosted \
  --budget 1
```

Local Ollama probe:

```bash
uv run metaharness smoke codex \
  ./my-coding-tool-optimizer \
  --probe-only \
  --oss \
  --local-provider ollama \
  --model gpt-oss:20b
```

Local Ollama run:

```bash
uv run metaharness run \
  ./my-coding-tool-optimizer \
  --backend codex \
  --oss \
  --local-provider ollama \
  --model gpt-oss:20b \
  --proposal-timeout 240 \
  --budget 1
```

## Gemini CLI

Gemini remains available as an experimental backend.

Probe:

```bash
uv run metaharness smoke gemini ./my-coding-tool-optimizer --probe-only
```

Run:

```bash
uv run metaharness run \
  ./my-coding-tool-optimizer \
  --backend gemini \
  --model gemini-2.5-pro \
  --proposal-timeout 180 \
  --budget 1
```

## Omnigent

Omnigent is available as an experimental proposer backend for running a
candidate proposal through `omni run`.

Configure it in `metaharness.json`:

```json
{
  "backends": {
    "omnigent": {
      "omnigent_binary": "omni",
      "harness": "codex",
      "model": "gpt-5.3-codex",
      "sandbox_type": "darwin_seatbelt",
      "allow_network": true,
      "event_log_path": ".metaharness/omnigent-events.jsonl",
      "no_session": false,
      "proposal_timeout_seconds": 300
    }
  }
}
```

Run:

```bash
uv run metaharness run \
  ./my-coding-tool-optimizer \
  --backend omnigent \
  --budget 1
```

By default, `metaharness` generates a per-candidate Omnigent agent bundle at
`.metaharness/omnigent_agent/config.yaml` inside the candidate workspace and
copies the config to `proposal/omnigent_agent.yaml` for review. The generated
config uses:

```yaml
instructions: .metaharness/AGENTS.md
os_env:
  type: caller_process
  cwd: /absolute/path/to/candidate/workspace
  sandbox:
    type: darwin_seatbelt
    write_paths:
      - AGENTS.md
```

When a project declares `allowed_write_paths`, those paths are mapped into the
Omnigent sandbox and a generated `metaharness_enforce_sandbox` policy. Trace
evidence, when supplied, is copied to `.metaharness/evidence/trace_evidence.md`
and referenced in the one-shot user prompt passed with `omni run -p`.

Set `agent_config` in the backend config if you want to use your own Omnigent
agent YAML instead of the generated one.

If `event_log_path` is set, `metaharness` reads that JSON, JSONL, or SSE-style
event file after `omni run` completes, copies it to
`proposal/omnigent_events.jsonl`, and normalizes the events into
`proposal/events.json`. Imported telemetry can populate final text, changed
files, token usage, tool-call count, cost, and file read/write summaries in
`proposal/result.json`.

## Practical Guidance

- Use Codex for production benchmark runs.
- Use Gemini when you specifically need Gemini CLI integration and accept experimental behavior.
- Use Omnigent when you want Omnigent's harness routing, policies, or custom
  agent YAML around a `metaharness` proposal run.
- Use `backend_plugins` when you need closed-source or internal harness adapters.

Verified smoke result:

- backend: `omnigent`
- benchmark: `examples/omnigent_agent_benchmark`
- result: `best_candidate_id=c0001`
- objective: `0.875`
- scope violations: none
