# Providers

## Provider Model

`metaharness` separates the optimization loop from the system that edits files.
That editing system is called a proposer backend.

Current backends:

- `CodexExecBackend` (validated)
- `GeminiCliBackend` (experimental)
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

## Practical Guidance

- Use Codex for production benchmark runs.
- Use Gemini when you specifically need Gemini CLI integration and accept experimental behavior.
- Use `backend_plugins` when you need closed-source or internal harness adapters.
