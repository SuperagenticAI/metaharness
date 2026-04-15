# Extensions

`metaharness` supports pluggable proposer backends through `backend_plugins` in `metaharness.json`.

This lets teams use internal or closed-source harnesses without modifying core library code.

## Config Shape

```json
{
  "backend_plugins": {
    "cursor": {
      "factory": "my_harness_plugins.cursor:create_backend",
      "options": {
        "model": "cursor-pro",
        "proposal_timeout_seconds": 180
      }
    }
  }
}
```

- key (`cursor`) becomes backend name used by CLI
- `factory` must be `module:callable`
- `options` are plugin defaults and can be overridden by `backends.<name>` and CLI overrides

## Factory Contract

The factory callable can accept:

- `project`
- `options`
- `backend_name`

It must return a proposer backend object with:

- `name`
- `prepare(request)`
- `invoke(request)`
- `collect(execution)`

## Usage

Run with your plugin backend:

```bash
uv run metaharness run ./my-project --backend cursor --budget 1
```

Run experiments with plugin backend names:

```bash
uv run metaharness experiment ./my-project --backend cursor --trials 3
```

## Recommended Pattern

1. Keep provider-specific command building and parsing inside your plugin module.
2. Normalize events and changed files in your plugin `collect` result.
3. Keep authentication and provider environment setup outside `metaharness`.
