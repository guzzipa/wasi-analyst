from __future__ import annotations
import json
from typing import Any, Dict
from openai import OpenAI
from wasi_analyst.util.settings import get_llm_settings

def _client() -> OpenAI | None:
    st = get_llm_settings()
    if not st.enabled or not st.api_key:
        return None
    return OpenAI(api_key=st.api_key)

def chat_json(system: str, user: str) -> Dict[str, Any]:
    cli = _client()
    if cli is None:
        return {"disabled": True}

    st = get_llm_settings()
    try:
        resp = cli.chat.completions.create(
            model=st.model,
            temperature=st.temperature,
            response_format={"type": "json_object"},
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            timeout=30,  # segundos
            max_tokens=400,
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(content)
    except Exception as e:
        return {"error": str(e), "actions": [], "reasoning":"llm_error"}
