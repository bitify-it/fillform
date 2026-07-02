from app.pipeline.prompts import load_prompt


def test_load_prompt_italian_is_unchanged() -> None:
    prompt = load_prompt("extraction", "it")
    assert prompt.startswith("Sei un motore di estrazione dati")


def test_load_prompt_english_is_available() -> None:
    prompt = load_prompt("extraction", "en")
    assert prompt.startswith("You are a data extraction engine")


def test_load_prompt_unknown_language_falls_back_to_english() -> None:
    assert load_prompt("extraction", "fr") == load_prompt("extraction", "en")


def test_load_prompt_defaults_to_english() -> None:
    assert load_prompt("double_check") == load_prompt("double_check", "en")
