"""
Provider Router — Single entry point for all LLM calls.

Implements tier-based routing:
- core: NVIDIA Build (primary) -> OpenRouter (fallback)
- planning: Gemini Flash (primary) -> OpenRouter (fallback)

Round-robin key rotation per provider. Immediate fallback on 429/5xx.
Loads API keys from .env file via python-dotenv.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

import httpx
from dotenv import load_dotenv

# Load .env file
load_dotenv()

logger = logging.getLogger(__name__)


class Tier(StrEnum):
    """LLM tier for routing."""
    CORE = "core"
    PLANNING = "planning"


class Provider(StrEnum):
    """LLM provider names."""
    NVIDIA = "nvidia"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"


@dataclass
class ProviderConfig:
    """Configuration for a single provider."""
    name: Provider
    api_keys: list[str] = field(default_factory=list)
    base_url: str = ""
    model: str = ""
    headers: dict = field(default_factory=dict)
    key_index: int = 0

    def get_next_key(self) -> str | None:
        """Get next API key in round-robin fashion."""
        if not self.api_keys:
            return None
        key = self.api_keys[self.key_index]
        self.key_index = (self.key_index + 1) % len(self.api_keys)
        return key


def _load_keys(env_var: str, fallback_env_var: str = "") -> list[str]:
    """Load API keys from environment variables."""
    keys = []
    # Check for comma-separated multi-key format first
    multi_key = os.getenv(env_var + "S") or os.getenv(fallback_env_var)
    if multi_key:
        keys.extend([k.strip() for k in multi_key.split(",") if k.strip()])
    # Check for single key format
    single_key = os.getenv(env_var)
    if single_key and single_key not in keys:
        keys.append(single_key)
    return keys


# Provider configurations
PROVIDERS: dict[Provider, ProviderConfig] = {
    Provider.NVIDIA: ProviderConfig(
        name=Provider.NVIDIA,
        api_keys=_load_keys("NVIDIA_API_KEY"),
        base_url="https://integrate.api.nvidia.com/v1",
        model="meta/llama-3.1-405b-instruct",
        headers={"Authorization": "Bearer {key}"},
    ),
    Provider.GEMINI: ProviderConfig(
        name=Provider.GEMINI,
        api_keys=_load_keys("GEMINI_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta",
        model="gemini-1.5-flash",
        headers={"x-goog-api-key": "{key}"},
    ),
    Provider.OPENROUTER: ProviderConfig(
        name=Provider.OPENROUTER,
        api_keys=_load_keys("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="meta-llama/llama-3.1-405b-instruct",
        headers={"Authorization": "Bearer {key}", "HTTP-Referer": "https://github.com/auto-scaffold", "X-Title": "Auto-Scaffold"},
    ),
}


# Tier routing configuration
TIER_ROUTES: dict[Tier, list[Provider]] = {
    Tier.CORE: [Provider.NVIDIA, Provider.OPENROUTER],
    Tier.PLANNING: [Provider.GEMINI, Provider.OPENROUTER],
}


async def _call_provider(
    provider: ProviderConfig,
    prompt: str,
    max_tokens: int = 4096,
    temperature: float = 0.1,
) -> str | None:
    """Call a single provider with the given prompt."""
    key = provider.get_next_key()
    if not key:
        logger.warning("No API key available for %s", provider.name)
        return None

    headers = {k: v.format(key=key) for k, v in provider.headers.items()}

    if provider.name == Provider.GEMINI:
        url = f"{provider.base_url}/models/{provider.model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
        }
    else:
        url = f"{provider.base_url}/chat/completions"
        payload = {
            "model": provider.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code in (429, 500, 502, 503, 504):
                logger.warning("Provider %s returned %d, will fallback", provider.name, response.status_code)
                return None

            response.raise_for_status()
            data = response.json()

            if provider.name == Provider.GEMINI:
                candidates = data.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
            else:
                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return message.get("content", "")

    except (httpx.TimeoutException, Exception) as e:
        logger.warning("Provider %s error: %s", provider.name, e)

    return None


async def call_llm(prompt: str, tier: Literal["core", "planning"]) -> str:
    """
    Call LLM with tier-based routing and fallback.

    Args:
        prompt: The prompt to send to the LLM
        tier: Either "core" or "planning"

    Returns:
        The LLM response text

    Raises:
        RuntimeError: If all providers for the tier fail
    """
    tier_enum = Tier(tier)
    providers = TIER_ROUTES.get(tier_enum, [])

    if not providers:
        raise ValueError(f"Unknown tier: {tier}")

    last_error = None
    for provider_name in providers:
        provider = PROVIDERS[provider_name]
        logger.debug("Trying provider %s for tier %s", provider_name, tier)

        result = await _call_provider(provider, prompt)
        if result is not None:
            logger.info("Successfully got response from %s", provider_name)
            return result

        last_error = f"Provider {provider_name} failed"
        logger.warning("Provider %s failed, trying next", provider_name)

    raise RuntimeError(f"All providers failed for tier {tier}: {last_error}")
