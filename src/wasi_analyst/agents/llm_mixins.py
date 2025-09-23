from __future__ import annotations
import os
import json
from typing import Dict, List, Any, Optional

# Tipos de acción esperados por el resto del sistema
_VALID_ACTIONS = {"buy", "sell", "hold"}

def _fmt_num(x: Optional[float]) -> str:
    try:
        return f"{float(x):.4f}"
    except Exception:
        return "NA"

def _obs_to_bulleted_text(obs: Dict[str, Any]) -> str:
    """
    Convierte el dict de observaciones en texto bullet-friendly para el prompt del LLM.
    Es tolerante a claves faltantes (ej: 'avg').
    Espera obs = {"symbols": {SYM: {"price":..,"avg":..,"sma":..,"mom":..,"vol":..,"hi":..,"lo":..}, ...}}
    """
    lines: List[str] = []
    symbols = list((obs or {}).get("symbols", {}).keys())
    for s in symbols:
        info: Dict[str, Any] = obs["symbols"].get(s, {})
        price = info.get("price")
        # 'avg' puede no existir; usamos 'sma' como aproximación si está, o NA
        avg = info.get("avg", info.get("sma"))
        mom = info.get("mom")
        vol = info.get("vol")
        hi  = info.get("hi")
        lo  = info.get("lo")
        parts = [
            f"price={_fmt_num(price)}",
            f"avg={_fmt_num(avg)}",
            f"sma={_fmt_num(info.get('sma'))}",
            f"mom={_fmt_num(mom)}",
            f"vol={_fmt_num(vol)}",
            f"hi={_fmt_num(hi)}",
            f"lo={_fmt_num(lo)}",
        ]
        lines.append(f"- {s}: " + ", ".join(parts))
    return "\n".join(lines) if lines else "(sin símbolos)"

def _safe_actions_from_json(txt: str) -> Optional[List[Dict[str, Any]]]:
    """
    Intenta parsear una respuesta JSON y normaliza acciones.
    Retorna None si falla.
    """
    try:
        data = json.loads(txt)
        acts = data.get("actions", [])
        norm: List[Dict[str, Any]] = []
        for a in acts:
            action = str(a.get("action", "hold")).lower()
            if action not in _VALID_ACTIONS:
                action = "hold"
            symbol = a.get("symbol")
            if not symbol:
                # si falta símbolo, descartamos esa acción
                continue
            try:
                qty = int(a.get("qty", 0))
            except Exception:
                qty = 0
            price = a.get("price", None)
            reason = a.get("reason", "")
            norm.append({"action": action, "symbol": str(symbol).upper(), "qty": qty, "price": price, "reason": reason})
        return norm
    except Exception:
        return None

def _heuristic_fallback(role: str, obs: Dict[str, Any], user_goal: str) -> Dict[str, Any]:
    """
    Fallback determinista cuando no hay API key o la respuesta del LLM no es usable.
    Usa señales disponibles: 'mom' (momentum), 'sma/avg' (mean-reversion) y 'hi/lo' (breakout).
    """
    actions: List[Dict[str, Any]] = []
    symbols = list((obs or {}).get("symbols", {}).keys())
    for s in symbols:
        f = obs["symbols"].get(s, {})
        price = f.get("price", 0.0)
        sma   = f.get("sma", f.get("avg", price))
        mom   = f.get("mom", 0.0)
        hi    = f.get("hi", price)
        lo    = f.get("lo", price)

        # thresholds suaves
        mom_th  = 0.003  # 0.3%
        dev     = (price / sma - 1.0) if (sma and sma != 0) else 0.0
        dev_th  = 0.002  # 0.2%
        brk_eps = 0.002  # 0.2%

        # heurística según el "rol" pedido
        if role == "fundamental":
            if dev < -dev_th:
                actions.append({"action": "buy",  "symbol": s, "qty": 10, "price": None, "reason": "heuristic: mean-reversion"})
            elif dev >  dev_th:
                actions.append({"action": "sell", "symbol": s, "qty": 10, "price": None, "reason": "heuristic: mean-reversion"})
            else:
                actions.append({"action": "hold", "symbol": s, "qty": 0,  "price": None, "reason": "heuristic: near-average"})
        elif role == "macro":
            if mom >  mom_th:
                actions.append({"action": "buy",  "symbol": s, "qty": 8,  "price": None, "reason": "heuristic: momentum-up"})
            elif mom < -mom_th:
                actions.append({"action": "sell", "symbol": s, "qty": 8,  "price": None, "reason": "heuristic: momentum-down"})
            else:
                actions.append({"action": "hold", "symbol": s, "qty": 0,  "price": None, "reason": "heuristic: flat"})
        else:  # sentiment
            if price >= hi * (1 + brk_eps):
                actions.append({"action": "buy",  "symbol": s, "qty": 6,  "price": None, "reason": "heuristic: breakout-high"})
            elif price <= lo * (1 - brk_eps):
                actions.append({"action": "sell", "symbol": s, "qty": 6,  "price": None, "reason": "heuristic: breakout-low"})
            else:
                actions.append({"action": "hold", "symbol": s, "qty": 0,  "price": None, "reason": "heuristic: range"})

    reasoning = (
        f"LLM no disponible o respuesta no parseable. Se aplicó fallback heurístico para el rol '{role}'. "
        f"Objetivo del usuario: '{user_goal}'." if user_goal else
        f"LLM no disponible o respuesta no parseable. Se aplicó fallback heurístico para el rol '{role}'."
    )
    return {"reasoning": reasoning, "actions": actions}

def llm_actions(role: str, obs: Dict[str, Any], user_goal: str = "") -> Dict[str, Any]:
    """
    Intenta usar un LLM (OpenAI) para decidir acciones. Si falla, aplica heurística.
    Retorna: {"reasoning": str, "actions": List[ActionDict]}
    """
    # Construcción de prompt (robusta a claves faltantes como 'avg')
    bullets = _obs_to_bulleted_text(obs)
    sys_msg = (
        "Sos un analista de inversiones. Tu tarea es proponer acciones por símbolo (buy/sell/hold) con qty y motivo. "
        "Contestá EXCLUSIVAMENTE en JSON con la forma: "
        '{"reasoning": "...", "actions": [{"action":"buy|sell|hold","symbol":"TICKER","qty":int,"price":null,"reason":"texto"}]}'
    )
    user_msg = (
        f"Rol del agente: {role}\n"
        f"Objetivo del usuario: {user_goal or '(no especificado)'}\n"
        f"Observaciones por símbolo:\n{bullets}\n\n"
        "Devolvé JSON válido. No incluyas comentarios ni texto fuera del JSON."
    )

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        # Sin API key → fallback directo
        return _heuristic_fallback(role, obs, user_goal)

    # Intento de llamada al LLM
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user",   "content": user_msg},
            ],
        )
        content = (resp.choices[0].message.content or "").strip()
        # Aceptamos JSON directo; si viniera dentro de ```json ... ``` limpiamos cercos
        if content.startswith("```"):
            content = content.strip("`")
            # a veces viene como "json\n{...}"
            if content.lower().startswith("json"):
                content = content[4:].lstrip()
        acts = _safe_actions_from_json(content)
        if acts is None:
            # Reintento simple: buscar el primer bloque {...} en texto
            import re
            m = re.search(r"\{.*\}", content, flags=re.DOTALL)
            if m:
                acts = _safe_actions_from_json(m.group(0))

        if acts is None:
            # Fallback si no pudimos parsear acciones
            return _heuristic_fallback(role, obs, user_goal)

        # Si el JSON traía reasoning, lo preservamos; si no, ponemos uno genérico
        try:
            parsed = json.loads(content)
            reasoning = parsed.get("reasoning") or f"Respuesta del modelo {model}."
        except Exception:
            reasoning = f"Respuesta del modelo {model}."
        return {"reasoning": reasoning, "actions": acts}

    except Exception as e:
        # Cualquier error en el cliente → fallback
        return _heuristic_fallback(role, obs, user_goal)
