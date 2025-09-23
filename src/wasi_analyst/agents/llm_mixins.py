from __future__ import annotations
import json
from typing import Dict, List
from wasi_analyst.providers.llm import chat_json
from wasi_analyst.util.schemas import Action

JSON_GUIDE = """
Devuelve SOLO JSON con este formato:
{
  "reasoning": "breve explicación de la decisión",
  "actions": [
    {"action":"buy|sell|hold","symbol":"<TICKER>","qty":<int>,"price":null,"reason":"texto corto"}
  ]
}
- Limitarse a símbolos dados por el contexto.
- qty entero (0..100 recomendado).
- Preferí 'hold' si no hay señal clara.
"""

def llm_actions(role: str, obs: Dict, user_goal: str) -> Dict:
    sys = f"Eres un analista {role}. Tu salida debe ser JSON estricto."
    # contexto pequeño y estable
    sym_lines = []
    for s, info in obs["symbols"].items():
        sym_lines.append(f"- {s}: price={info['price']:.2f}, avg={info['avg']:.2f}")
    context = "\n".join(sym_lines)

    user = f"""
Objetivo del usuario: {user_goal or "(no especificado)"}

Símbolos y precios actuales:
{context}

{JSON_GUIDE}
"""
    resp = chat_json(system=sys, user=user)
    if resp.get("disabled"):
        # LLM apagado -> sin decisión
        return {"reasoning": "LLM disabled", "actions": []}

    # Normalizar salida
    actions = []
    for a in resp.get("actions", []):
        try:
            actions.append(Action(
                action=a.get("action","hold"),
                symbol=a.get("symbol","WASI"),
                qty=int(a.get("qty", 0)),
                price=None,
                reason=a.get("reason","")
            ).model_dump())
        except Exception:
            continue
    return {
        "reasoning": resp.get("reasoning",""),
        "actions": actions
    }
