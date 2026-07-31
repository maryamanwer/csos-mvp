"""Pluggable model-provider adapters.

Agents depend on ``ModelProvider`` rather than an individual model or vendor.
Ollama is registered as the local runtime today; another compatible provider
can be added by registering a factory without changing any agent code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

import ollama

from app.core.config import settings


class ModelSelectionError(ValueError):
    """Raised when a requested provider or model is not configured."""


class ModelProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, model: str | None = None) -> str:
        """Return one text response for ``prompt`` using the selected model."""


class OllamaModelProvider(ModelProvider):
    """Local Ollama adapter supporting any configured compatible model."""

    def __init__(self, base_url: str | None = None):
        self._client = ollama.Client(host=base_url or settings.OLLAMA_BASE_URL)

    def generate(self, prompt: str, model: str | None = None) -> str:
        selected_model = resolve_model(model)
        response = self._client.chat(
            model=selected_model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response["message"]["content"]


ProviderFactory = Callable[[], ModelProvider]
_provider_factories: dict[str, ProviderFactory] = {
    "ollama": OllamaModelProvider,
}


def register_model_provider(name: str, factory: ProviderFactory) -> None:
    """Register an additional provider adapter at the application boundary."""
    _provider_factories[name.strip().lower()] = factory


def get_model_provider(name: str | None = None) -> ModelProvider:
    provider_name = (name or settings.AI_PROVIDER).strip().lower()
    try:
        return _provider_factories[provider_name]()
    except KeyError as exc:
        supported = ", ".join(sorted(_provider_factories))
        raise ModelSelectionError(
            f"Unknown AI provider '{provider_name}'. Configured providers: {supported}"
        ) from exc


def resolve_model(model: str | None = None) -> str:
    selected_model = (model or settings.AI_DEFAULT_MODEL).strip()
    if selected_model not in settings.available_ai_models:
        supported = ", ".join(settings.available_ai_models)
        raise ModelSelectionError(
            f"Model '{selected_model}' is not enabled. Configured models: {supported}"
        )
    return selected_model
