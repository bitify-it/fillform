# FillForm

[![CI](https://github.com/bitify-it/fillform/actions/workflows/ci.yml/badge.svg)](https://github.com/bitify-it/fillform/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)

**Evidence-based form-field extraction from documents — it only answers when the document proves it.**

FillForm is a FastAPI service that extracts structured field values from documents to fill forms. Its defining property is **anti-hallucination**: every answer must be backed by an explicit quote from the source document. If the evidence is not there, the field is returned as `not_found` instead of a made-up value.

Give it a document and a list of questions; get back structured JSON answers, each with the supporting quote, a confidence score, deterministic validation and an optional LLM double-check.

## Why FillForm

- **Evidence or nothing.** Answers require a textual quote from the document; unsupported values become `not_found`, `ambiguous` or `needs_review`.
- **Deterministic validation.** Type checks, regex patterns and dropdown (`allowedValues`) normalization run in code, not in the model.
- **Optional double-check.** A second LLM pass can verify low-confidence answers.
- **Runs locally.** Default provider is [Ollama](https://ollama.com) — no data leaves your machine. Any OpenAI-compatible endpoint also works.
- **Sync or async.** Small documents inline, larger ones as background jobs with progress tracking.

## Demo

Real, unedited output from a local run against `gemma4:12b-mlx` on Ollama. The
document only states the legal name, VAT number and sector — nothing about a
Data Protection Officer:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/form-extraction/run \
  -F 'file=@company.html' \
  -F 'payload={
    "formName": "Company Registration",
    "fields": [
      {"fieldId": "legal_name", "question": "What is the company legal name?", "expectedType": "string"},
      {"fieldId": "vat_number", "question": "What is the VAT number?", "expectedType": "vat_number"},
      {"fieldId": "dpo_appointed", "question": "Has the company appointed a Data Protection Officer?", "expectedType": "boolean"}
    ],
    "options": {"strictEvidence": true, "language": "en"}
  }'
```

```json
{
  "status": "completed_with_gaps",
  "answers": [
    {
      "fieldId": "legal_name",
      "status": "answered",
      "value": "Acme Robotics S.p.A.",
      "confidence": 1.0,
      "evidence": [{ "quote": "Legal name: Acme Robotics S.p.A." }]
    },
    {
      "fieldId": "vat_number",
      "status": "answered",
      "value": "12345678901",
      "confidence": 1.0,
      "evidence": [{ "quote": "VAT number: 12345678901" }]
    },
    {
      "fieldId": "dpo_appointed",
      "status": "not_found",
      "value": null,
      "confidence": 0.0
    }
  ]
}
```

The two facts present in the document are extracted with evidence. The DPO
question — not mentioned anywhere — comes back `not_found` instead of a
guessed `true`/`false`. That's the anti-hallucination guarantee in practice.

## How it works

```
document ──▶ MarkItDown ──▶ chunking ──▶ per-field LLM extraction ──▶ validation ──▶ (optional) double-check ──▶ JSON
```

The document is converted to Markdown with [Microsoft MarkItDown](https://github.com/microsoft/markitdown), chunked, and each field is extracted independently to maximize quality.

## Stack

Python 3.12+ · FastAPI · Pydantic v2 · MarkItDown · HTTPX · Ollama / OpenAI-compatible LLMs · Docker · pytest & ruff.

Supported input formats: PDF, Word, Excel, HTML.

## Quickstart

### Docker Compose

```bash
docker compose up --build
```

Then open Swagger at http://127.0.0.1:8000/docs.

The default provider is Ollama running on the host. On Docker Desktop the API reaches it via `host.docker.internal`; make sure you have pulled a model (`ollama pull gemma2:9b`).

### Local

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/uvicorn app.main:app --reload
```

- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

## Configuration

Settings come from environment variables ([app/core/config.py](app/core/config.py)):

```env
APP_ENV=development
LOG_LEVEL=INFO

MAX_UPLOAD_BYTES=26214400
STORAGE_DIR=storage

LLM_PROVIDER=ollama
LLM_MODEL=gemma2:9b
LLM_ENDPOINT=http://localhost:11434
LLM_API_KEY=
LLM_TEMPERATURE=0
LLM_TIMEOUT_SECONDS=120
LLM_JSON_REPAIR_ATTEMPTS=2
LLM_NUM_CTX=16384
LLM_MAX_TOKENS=4096

DOUBLE_CHECK_MODE=low_confidence
DOUBLE_CHECK_CONFIDENCE_THRESHOLD=0.6
```

### LLM providers

| `LLM_PROVIDER` | Backend | Notes |
| --- | --- | --- |
| `ollama` (default) | Ollama | Local models. `LLM_ENDPOINT` points to the Ollama server. `LLM_NUM_CTX` forces the context window. |
| `openai`, `openai_compatible`, `vllm`, `lmstudio`, `together`, `groq` | Any OpenAI-compatible Chat Completions API | Set `LLM_ENDPOINT` to the base URL (e.g. `https://api.openai.com/v1`) and `LLM_API_KEY`. Uses `response_format: json_object`. |
| `anthropic`, `claude` | Anthropic Messages API | Set `LLM_API_KEY`. Uses the official endpoint and an assistant prefill to force JSON. `LLM_MAX_TOKENS` caps the response. |

Example — OpenAI:

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_ENDPOINT=https://api.openai.com/v1
LLM_API_KEY=sk-...
```

Example — vLLM / LM Studio (self-hosted):

```env
LLM_PROVIDER=vllm
LLM_MODEL=your-model
LLM_ENDPOINT=http://localhost:8000/v1
```

Example — Anthropic (Claude):

```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-haiku-4-5
LLM_API_KEY=sk-ant-...
LLM_MAX_TOKENS=4096
```

### Double-check modes

- `low_confidence`: verify only `answered` values below the confidence threshold.
- `answered`: verify every `answered` value.
- `always`: verify every field, including `not_found`.
- `disabled`: no LLM double-check.

### Language

`options.language` (per request) selects the prompt language and the language of short notes. Prompts ship for `it` and `en`; unknown languages fall back to English. Document content can be in any language regardless of this setting.

## API

Base path: `/api/v1/form-extraction`.

### `POST /run` — synchronous extraction

`multipart/form-data` with:

- `file`: the document to analyze.
- `payload`: the form request as a JSON string.

Runs the whole pipeline in the request. Best for small documents, Swagger and local testing.

### `POST /jobs` — create an async job

Same input; returns a `jobId` immediately. Jobs are persisted under `STORAGE_DIR/jobs`.

### `GET /jobs/{jobId}` — job status

```json
{
  "jobId": "job_123",
  "status": "running",
  "progressPercent": 42,
  "progressMessage": "Processed field 3/12.",
  "result": null,
  "error": null
}
```

### `GET /llm/health` — provider health

Checks whether the configured provider responds and whether the model is available.

```json
{
  "provider": "ollama",
  "model": "gemma2:9b",
  "endpoint": "http://localhost:11434",
  "available": true,
  "modelAvailable": true,
  "error": null
}
```

## Request payload

Minimal — each field only needs `question` and `expectedType`:

```json
{
  "formName": "Company profile",
  "fields": [
    { "question": "What is the company legal name?", "expectedType": "string" }
  ],
  "options": { "strictEvidence": true, "language": "en" }
}
```

With optional fields and validation:

```json
{
  "formName": "Company profile",
  "fields": [
    {
      "fieldId": "company_name",
      "targetRef": "html:company_name",
      "label": "Legal name",
      "question": "What is the company legal name?",
      "expectedType": "string",
      "validationRules": { "pattern": "^.{2,}$" }
    },
    {
      "fieldId": "sector",
      "question": "What is the company sector?",
      "expectedType": "enum",
      "validationRules": {
        "allowedValues": [
          { "value": "IT_CONSULTING", "label": "IT consulting" },
          { "value": "FINANCE", "label": "Finance" }
        ]
      }
    },
    {
      "fieldId": "operating_countries",
      "question": "In which countries does the company operate?",
      "expectedType": "array",
      "validationRules": {
        "multiple": true,
        "allowedValues": [
          { "value": "IT", "label": "Italy" },
          { "value": "DE", "label": "Germany" }
        ]
      }
    }
  ],
  "options": { "strictEvidence": true, "language": "en" }
}
```

- If `fieldId` is missing it is generated as `field_001`, `field_002`, …
- `targetRef` and `label` are optional (default `null` / empty string).
- `validationRules` supports `pattern`, `allowedValues`, `multiple` and `caseSensitive`.
- For `allowedValues`, `normalizedValue` returns the technical `value` (not the `label`), so it is ready for form filling.

Supported `expectedType`: `string`, `number`, `integer`, `boolean`, `date`, `email`, `phone`, `vat_number`, `tax_code`, `iban`, `address`, `enum`, `array`.

### curl example

```bash
printf '<html><body><p>Legal name: ACME Inc.</p></body></html>' > /tmp/test.html

curl -X POST http://127.0.0.1:8000/api/v1/form-extraction/run \
  -F 'file=@/tmp/test.html' \
  -F 'payload={"formName":"Test","fields":[{"question":"What is the legal name?","expectedType":"string"}],"options":{"strictEvidence":true,"language":"en"}}'
```

## Response

```json
{
  "formName": "Company profile",
  "status": "completed_with_gaps",
  "answers": [
    {
      "fieldId": "field_001",
      "question": "What is the company legal name?",
      "status": "answered",
      "value": "ACME Inc.",
      "normalizedValue": "ACME Inc.",
      "confidence": 0.91,
      "evidence": [
        { "page": null, "section": null, "lineStart": 1, "lineEnd": 1, "quote": "Legal name: ACME Inc." }
      ],
      "validation": { "status": "skipped", "errors": [] },
      "doubleCheck": { "status": "skipped", "notes": "..." }
    }
  ],
  "metadata": {
    "llmProvider": "ollama",
    "llmModel": "gemma2:9b",
    "strictEvidence": true
  }
}
```

Form status: `completed`, `completed_with_gaps`, `failed` (async also `queued`, `running`).
Field status: `answered`, `not_found`, `ambiguous`, `validation_failed`, `needs_review`, `error`.

## Development

```bash
.venv/bin/python -m ruff check app tests
.venv/bin/python -m pytest
```

## Deployment

A GPU host is strongly recommended for real workloads: CPU inference works but is memory-bandwidth bound and slow. Keep the API where it is and point `LLM_ENDPOINT` at your inference host.

### Running Ollama on a Linux host

By default Ollama listens on `127.0.0.1` only, so it is unreachable from a Docker network (`Connection refused`). Make it listen on all interfaces:

```bash
sudo systemctl edit ollama
```

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

```bash
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

⚠️ On a public host this exposes Ollama to the internet. Restrict it to your Docker/inference network with a firewall — see [scripts/harden-ollama.sh](scripts/harden-ollama.sh).

## License

Licensed under the [Apache License 2.0](LICENSE).
