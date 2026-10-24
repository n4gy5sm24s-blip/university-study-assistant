from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv, set_key


DEFAULT_MODEL = "gpt-6-luna"


@dataclass(frozen=True)
class ModelStatus:
    configured: bool
    model: str
    provider: str = "OpenAI"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class ModelConfigurationError(ValueError):
    pass


def model_status() -> ModelStatus:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "").strip()
    return ModelStatus(bool(api_key and model), model or DEFAULT_MODEL)


def save_model_configuration(env_path: Path, api_key: str, model: str) -> ModelStatus:
    clean_key = api_key.strip()
    clean_model = model.strip()
    if not clean_model:
        raise ModelConfigurationError("请填写模型 ID")
    if not clean_key and not os.environ.get("OPENAI_API_KEY", "").strip():
        raise ModelConfigurationError("首次接入需要填写 OpenAI API Key")

    env_path.touch(exist_ok=True)
    if clean_key:
        set_key(str(env_path), "OPENAI_API_KEY", clean_key)
    set_key(str(env_path), "OPENAI_MODEL", clean_model)
    load_dotenv(env_path, override=True)
    return model_status()
