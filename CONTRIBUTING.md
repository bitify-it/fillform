# Contributing to FillForm

Thanks for your interest in improving FillForm! Contributions of all kinds are welcome: bug reports, features, docs, tests and new LLM providers.

## Development setup

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Run the checks before opening a pull request:

```bash
.venv/bin/python -m ruff check app tests
.venv/bin/python -m pytest
```

CI runs the same lint and tests on every pull request.

## Guidelines

- Keep changes focused; one logical change per pull request.
- Match the existing style (ruff enforces formatting and lint rules).
- Add or update tests for behavior changes.
- Update the README when you change configuration, endpoints or payloads.

## Adding an LLM provider

Providers implement the `LLMClient` protocol in [app/llm/base.py](app/llm/base.py)
(`generate_json` and `health_check`) and are wired in
[app/llm/factory.py](app/llm/factory.py). See `app/llm/openai_compatible.py` and
`app/llm/anthropic.py` for examples. Reuse the shared JSON helpers in
`app/llm/json_parsing.py`.

## Reporting bugs

Open an issue with steps to reproduce, the provider/model used, and the relevant
logs. Please do not include documents with sensitive data.

By contributing, you agree that your contributions are licensed under the
project's [Apache 2.0 License](LICENSE).
