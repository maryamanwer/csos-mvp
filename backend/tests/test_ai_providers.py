import pytest

from app.ai.providers import ModelSelectionError, get_model_provider, resolve_model
from app.core.config import settings


def test_default_model_is_resolved_from_configuration(monkeypatch):
    monkeypatch.setattr(settings, "AI_DEFAULT_MODEL", "qwen2.5")
    monkeypatch.setattr(settings, "AI_AVAILABLE_MODELS", "llama3.1,qwen2.5,mistral")

    assert resolve_model() == "qwen2.5"
    assert resolve_model("mistral") == "mistral"


def test_unconfigured_model_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "AI_AVAILABLE_MODELS", "llama3.1,qwen2.5")

    with pytest.raises(ModelSelectionError):
        resolve_model("unknown-model")


def test_unknown_provider_is_rejected():
    with pytest.raises(ModelSelectionError):
        get_model_provider("unknown-provider")
