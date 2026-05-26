# Python Fixture Benchmark

This is the first real benchmark target for `metaharness`.

It is still small, but it is not a placeholder scaffold:

- `baseline/fixture_repo/` is a real Python package
- `scripts/bootstrap.sh` must create a real virtualenv
- `scripts/test.sh` must run a real `unittest` suite
- `scripts/validate.sh` must enforce concrete coding-agent instruction requirements
- `tasks.json` is search-time feedback
- `test_tasks.json` is held-out feedback, evaluated only after the final frontier is selected

By default this benchmark uses frontier search with batched proposals:

- `search_mode`: `frontier`
- `proposal_batch_size`: `2`
- `selection_policy`: `pareto`
- `default_budget`: `3`

Run it with the fake backend:

```bash
uv run metaharness run examples/python_fixture_benchmark --backend fake --budget 1 --run-name fake-smoke
```

Run it with hosted Codex:

```bash
uv run metaharness run examples/python_fixture_benchmark --backend codex --hosted --budget 3 --run-name codex-hosted-paperlike
```

Run it with local Codex over Ollama:

```bash
uv run metaharness run examples/python_fixture_benchmark --backend codex --oss --local-provider ollama --model gpt-oss:120b --proposal-timeout 420 --budget 3 --run-name codex-local-paperlike
```

Run the checked-in paper-like hosted Codex experiment config:

```bash
uv run metaharness experiment --config examples/experiment_configs/codex-paperlike-fixture.json
```
