# Security Policy

## Reporting a vulnerability

Please report security issues privately via GitHub's "Report a vulnerability"
(Security advisories) or by email to the maintainers. Do not open a public issue
for security problems.

We aim to acknowledge reports within a few business days.

## Operational notes

FillForm is an unauthenticated API by default. Do not expose it directly to the
public internet:

- Put it behind an authenticating reverse proxy or API gateway.
- Restrict access to the LLM backend (e.g. Ollama) to trusted networks only;
  see [scripts/harden-ollama.sh](scripts/harden-ollama.sh).
- Treat uploaded documents as sensitive; storage under `STORAGE_DIR` is not
  encrypted by the application.
- API keys for hosted providers are read from environment variables — never
  commit them.
