"""Dependency providers for FastAPI DI.

This module exposes singleton instances (cached via `functools.lru_cache`) so
that every request hitting the API receives **the same** objects – most
importantly the `TradingOrchestrator` which must stay unique throughout the
process lifetime.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Dict, Any

import yaml  # PyYAML is already listed in requirements

from .orchestrator import TradingOrchestrator


# ---------------------------------------------------------------------------
# Configuration helper
# ---------------------------------------------------------------------------

def _load_config() -> Dict[str, Any]:
    """Load configuration from a YAML/JSON file path specified in *APP_CONFIG*.

    Fallback order:
    1. Environment variable ``APP_CONFIG`` (absolute or relative path).
    2. ``config/app.yaml`` relative to project root.
    3. Empty dict (the orchestrator will then rely on env vars).
    """
    cfg_path = os.getenv("APP_CONFIG", os.path.join("config", "app.yaml"))

    if not os.path.isfile(cfg_path):
        # Nothing to load – return empty dict so orchestrator falls back to env.
        return {}

    if cfg_path.endswith((".yml", ".yaml")):
        with open(cfg_path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

    if cfg_path.endswith(".json"):
        with open(cfg_path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    # Unsupported extension – ignore.
    return {}


# ---------------------------------------------------------------------------
# FastAPI dependency factories
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_settings() -> Dict[str, Any]:
    """Return the settings dict, cached for the life of the process."""
    return _load_config()


@lru_cache(maxsize=1)
def get_orchestrator() -> TradingOrchestrator:
    """Return a singleton :class:`TradingOrchestrator`.

    The orchestrator **is *not* started here** – this keeps the dependency
    factory synchronous (FastAPI requires sync callables for cached providers).
    Startup / shutdown of the orchestrator should be managed in the FastAPI
    lifespan event *once*.
    """
    return TradingOrchestrator(get_settings())
