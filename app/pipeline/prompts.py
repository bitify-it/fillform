from functools import lru_cache
from importlib.resources import files

DEFAULT_PROMPT_LANGUAGE = "en"


@lru_cache
def load_prompt(name: str, language: str = DEFAULT_PROMPT_LANGUAGE) -> str:
    """Load a prompt by base name and language.

    Files are named ``<name>.<language>.md`` (e.g. ``extraction.it.md``). When a
    translation is missing, it falls back to the English version so every
    language keeps working.
    """
    lang = (language or DEFAULT_PROMPT_LANGUAGE).lower()
    for candidate in (f"{name}.{lang}.md", f"{name}.{DEFAULT_PROMPT_LANGUAGE}.md"):
        path = files("app.llm.prompts").joinpath(candidate)
        if path.is_file():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"No prompt file found for '{name}' (language '{lang}').")
