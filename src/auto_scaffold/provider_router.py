"""
Provider Router — Single entry point for all LLM calls.

Implements tier-based routing:
- core: NVIDIA Build (primary) -> OpenRouter (fallback)
- planning: Gemini Flash (primary) -> OpenRouter (fallback)

Round-robin key rotation per provider. Immediate fallback on 429/5xx.
Loads API keys from .env file via python-dotenv.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional

import httpx
from dotenv import load_dotenv

# Load .env file
load_dotenv()

logger = logging.getLogger(__name__)