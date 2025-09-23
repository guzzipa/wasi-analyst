from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class LLMSettings:
    enabled: bool
    api_key: str | None
    model: str = "gpt-4o-mini"
    temperature: float = 0.2

def get_llm_settings() -> LLMSettings:
    key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temp = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
    return LLMSettings(enabled=bool(key), api_key=key, model=model, temperature=temp)
