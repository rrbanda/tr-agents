"""Centralized configuration loader.

Reads config.yaml from the project root. Environment variables
can override values via ${VAR_NAME} or ${VAR_NAME:-default} syntax.
"""

import logging
import os
import pathlib
import re
from functools import lru_cache
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_PROJECT_ROOT = pathlib.Path(__file__).parent.parent
_ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)(?::-([^}]*))?\}")


def _resolve_env_vars(value: Any) -> Any:
    if isinstance(value, str):

        def _replace(m: re.Match[str]) -> str:
            var_name = m.group(1)
            default = m.group(2)
            env_val = os.environ.get(var_name)
            if env_val is not None:
                return env_val
            if default is not None:
                return default
            return m.group(0)

        return _ENV_VAR_PATTERN.sub(_replace, value)
    if isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    config_path = _PROJECT_ROOT / "config.yaml"
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise RuntimeError(f"Expected mapping in {config_path}, got {type(raw).__name__}")
    return _resolve_env_vars(raw)


def get_agent_model() -> Any:
    from google.adk.models.lite_llm import LiteLlm

    cfg = load_config()["model"]["agent"]
    kwargs: dict[str, Any] = {"model": cfg["id"]}
    if cfg.get("api_base"):
        kwargs["api_base"] = cfg["api_base"]
    if cfg.get("api_key"):
        kwargs["api_key"] = cfg["api_key"]
    return LiteLlm(**kwargs)


def get_agent_config(agent_name: str) -> dict[str, Any]:
    return load_config()["agents"][agent_name]
