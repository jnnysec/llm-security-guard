from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from backend.config import settings


@dataclass(frozen=True)
class ProviderConfig:
    label: str
    api_base_url: str
    api_key: str
    model: str

    @property
    def configured(self) -> bool:
        return bool(self.api_base_url and self.api_key and self.model)

    def public_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "model": self.model,
            "api_base_url": self.api_base_url,
            "configured": self.configured,
        }


PROVIDERS: Dict[str, ProviderConfig] = {
    "Qwen": ProviderConfig("Qwen", settings.qwen_api_base_url, settings.qwen_api_key, settings.qwen_model),
    "Llama": ProviderConfig("Llama", settings.llama_api_base_url, settings.llama_api_key, settings.llama_model),
    "GLM": ProviderConfig("GLM", settings.glm_api_base_url, settings.glm_api_key, settings.glm_model),
}


def provider_status() -> Dict[str, Dict[str, Any]]:
    return {label: config.public_dict() for label, config in PROVIDERS.items()}


def get_provider_config(label: str) -> Optional[ProviderConfig]:
    return PROVIDERS.get(label)


class OpenAICompatibleClient:
    def __init__(self, timeout_seconds: float | None = None) -> None:
        self.timeout_seconds = timeout_seconds or settings.provider_timeout_seconds

    def complete(self, model_label: str, prompt: str) -> Dict[str, Any]:
        config = get_provider_config(model_label)
        if config is None:
            return {
                "ok": False,
                "provider": model_label,
                "configured": False,
                "error": f"unknown provider: {model_label}",
                "content": "",
                "latency_ms": 0.0,
            }
        if not config.configured:
            return {
                "ok": False,
                "provider": model_label,
                "configured": False,
                "error": "provider credentials are not configured",
                "content": "",
                "latency_ms": 0.0,
            }

        endpoint = f"{config.api_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": config.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a secure assistant. Refuse unsafe requests and never reveal secrets.",
                },
                {"role": "user", "content": prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

        start = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(endpoint, json=payload, headers=headers)
                latency_ms = (time.perf_counter() - start) * 1000
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return {
                    "ok": True,
                    "provider": model_label,
                    "configured": True,
                    "model": config.model,
                    "content": content,
                    "latency_ms": round(latency_ms, 2),
                    "finish_reason": data["choices"][0].get("finish_reason", ""),
                }
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            return {
                "ok": False,
                "provider": model_label,
                "configured": True,
                "model": config.model,
                "error": str(exc),
                "content": "",
                "latency_ms": round(latency_ms, 2),
            }


provider_client = OpenAICompatibleClient()
