import streamlit as st
import pandas as pd
from collections import Counter

from wasi_analyst.app.run import run_simulation
from wasi_analyst.util.metrics import price_metrics_table, equity_metrics

from dotenv import load_dotenv
load_dotenv()


# --- Config de página debe ir antes de cualquier st.* visible ---
st.set_page_config(page_title="Wasi Analyst", layout="wide")

# --- Presets de símbolos ---
POPULAR   = ["AAPL","MSFT","AMZN","GOOGL","META","TSLA","NVDA","NFLX","AMD","INTC"]
US_TECH   = ["AAPL","MSFT","NVDA","GOOGL","META","AMZN"]
LATAM_ADR = ["MELI","PBR","VALE","ITUB","ABEV","GGAL","BMA","TEO","YPF","DESP"]
ALL_OPTIONS = sorted({*POPULAR, *US_TECH, *LATAM_ADR})

# ----------------- Helpers “conversación de agentes” -----------------
def _extract_day_views(transcript):
    """Agrupa el transcript por día y arma una vista tabular por símbolo."""
    days = sorted({t["day"] for t in transcript})
    views = []
    for d in days:
        steps = [t for t in transcript if t["day"] == d]
        agents_step = next((s for s in steps if s["step"] == "agents_opinion"), None)
        risk_step   = next((s for s in steps if s["step"] == "risk_manager"), None)
        if not agents_step:
            continue

        # símbolos presentes en las acciones de los agentes
        symbols = []
        for msg in agents_step.get("messages", []):
            for a in msg.get("actions", []):
                if "symbol" in a:
                    symbols.append(a["symbol"])
        symbols = sorted(set(symbols))

        rows = []
        for sym in symbols:
            votes, reasons = {}, {}
            for msg in agents_step.get("messages", []):
                agent = msg.get("agent", "?")
                act = next((a for a in msg.get("actions", []) if a.get("symbol") == sym), None)
                if act:
                    votes[agent] = (act.get("action") or "hold").upper()
                    if act.get("reason"):
                        reasons[agent] = act["reason"]

            consenso = Counter(votes.values()).most_common(1)[0][0] if votes else "HOLD"
            final = consenso
            if risk_step:
                post = next((a for a in risk_step.get("actions", []) if a.get("symbol") == sym), None)
                if post:
                    final = (post.get("action") or consenso).upper()

            rows.append({
                "Símbolo": sym,
                "Fundamental": votes.get("fundamental", "-"),
                "Macro": votes.get("macro", "-"),
                "Sentiment": votes.get("sentiment", "-"),
                "Consenso": consenso,
                "Final (post-riesgo)": final,
                "_reasons": reasons,
            })

        # resumen en lenguaje natural
        non_hold = [r for r in rows if r["Final (post-riesgo)"] != "HOLD"]
        if non_hold:
            cambios = ", ".join([f"{r['Símbolo']} → {r['Final (post-riesgo)']}" for r in non_hold])
            summary = f"Acciones: {cambios}."
        else:
            summary = "Sin cambios: todos los símbolos quedaron en HOLD."

        views.append({"day": d, "rows": rows, "summary": summary, "agents_step": agents_step})
    return views

def _compact_reasoning(agents_step):
    """Devuelve lista (agente, reasoning) con textos breves."""
    out = []
    for msg in agents_step.get("messages", []):
        r = msg.get("reasoning") or ""
        if len(r) > 220:
            r = r[:200].rstrip() + "…"
        out.append((msg.get("agent", "?"), r))
    return out

# ----------------- Estado básico -----------------
def _ensure_state():
    st.session_state.setdefault("runs", [])
    st.session_state.setdefault("goal", "")
    st.session_state.setdefault("sel_default", ["AAPL","MSFT"])
    st.session_state.setdefault("exec_logs", [])  # solo textos, no objetos de Streamlit
_ = _ensure_state()

st.title("Wasi Analyst — Investment Analyst Lab")

st.markdown(
    """
**Wasi Analyst** es un _laboratorio de estrategias_ con **agentes de inversión** que analizan un set de símbolos,
discuten y proponen órdenes. Podés simular con **datos reales (Yahoo Finance)** o con **datos sintéticos** y elegir
si cada agente usa **reglas** o **LLM**.  
En la barra lateral configurás **símbolos, días, seed, objetivo y tuning**; luego en la pestaña **Resultados** ves
equity, precios, trades y métricas; y en **Conversación de agentes** aparece el **voto de cada agente, consenso y
decisión final**, con un resumen entendible.

- **Agentes**: Fundamental (mean-reversion), Macro (momentum) y Sentiment (breakout).
- **Riesgo y ejecución**: un _risk manager_ limita posiciones y un agente de ejecución envía órdenes.
- **LLM opcional**: si cargás tu `OPENAI_API_KEY`, los agentes pueden razonar con modelos de lenguaje.

> Sugerencia: empezá con 2–3 símbolos y 15–30 días. Si activás LLM, usá **Modo rápido**.
"""
)

# ---- EJECUCIÓN EN VIVO (solo logs, nunca objetos de Streamlit) ----
st.markdown("### Ejecución en vivo")
if st.session_state.exec_logs:
    with st.expander("Logs recientes", expanded=False):
        for line in st.session_state.exec_logs[-50:]:
            st.write(line)
else:
    st.caption("Aún no hay logs.")

# ========================== SIDEBAR ==========================
with st.sidebar:
    st.header("Simulación")

    data_source = st.selectbox(
        "Fuente de datos",
        ["Random Walk (demo)", "Yahoo Finance (daily)"],
        index=0
    )
    data_source_value = "Random Walk" if data_source.startswith("Random Walk") else "Yahoo Finance (daily)"

    st.markdown("**Presets de símbolos**")
    c1, c2, c3 = st.columns(3)
    if c1.button("US Tech", use_container_width=True):
        st.session_state.sel_default = US_TECH
        st.session_state.exec_logs = []
    if c2.button("LATAM (ADR)", use_container_width=True):
        st.session_state.sel_default = LATAM_ADR
        st.session_state.exec_logs = []
    if c3.button("Populares", use_container_width=True):
        st.session_state.sel_default = ["AAPL","MSFT"]
        st.session_state.exec_logs = []

    sel_default = st.session_state.get("sel_default", ["AAPL","MSFT"])
    default_safe = [s for s in sel_default if s in ALL_OPTIONS]  # intersección
    sel = st.multiselect("Símbolos", ALL_OPTIONS, default=default_safe)
    extra = st.text_input("Sumar símbolos (coma)", value="")
    symbols = [s.strip().upper() for s in sel]
    if extra.strip():
        symbols += [s.strip().upper() for s in extra.split(",") if s.strip()]

    colA, colB = st.columns(2)
    with colA:
        days = st.number_input("Días", 5, 365, 20, 1)
    with colB:
        seed = st.number_input("Seed", 0, 10_000, 42, 1)

    st.markdown("### Objetivo (presets)")
    preset_cols = st.columns(4)
    presets = ["Comparar performance entre símbolos", "Minimizar drawdown", "Maximizar Sharpe", "Estrategia conservadora"]
    for i, p in enumerate(presets):
        if preset_cols[i].button(p, use_container_width=True):
            st.session_state.goal = p
    goal = st.text_area("¿Qué querés que haga el agente?", value=st.session_state.get("goal",""))

    st.markdown("### Modo de cada agente")
    col1, col2, col3 = st.columns(3)
    fundamental_mode = "llm" if col1.toggle("Fundamental LLM", value=False) else "rule"
    macro_mode       = "llm" if col2.toggle("Macro LLM", value=False) else "rule"
    sentiment_mode   = "llm" if col3.toggle("Sentiment LLM", value=False) else "rule"

    with st.expander("⚙️ Tuning avanzado (fallbacks de reglas)", expanded=False):
        st.caption("Afecta a los agentes cuando están en modo *rule*. Los valores están en días o en % (bps).")

        st.subheader("Fundamental · Mean-Reversion")
        cfa, cfb, cfc = st.columns(3)
        fundamental_sma_window   = cfa.number_input("SMA window (días)", 1, 60, 5, 1)
        fundamental_base_bps     = cfb.number_input("Umbral base (bps)", 0, 200, 20, 1)
        fundamental_qty_cap      = cfc.number_input("Qty cap", 1, 100, 20, 1)

        st.subheader("Macro · Momentum")
        cma, cmb, cmc = st.columns(3)
        macro_mom_window         = cma.number_input("Momentum window (días)", 1, 60, 3, 1)
        macro_thresh_bps         = cmb.number_input("Umbral momentum (bps)", 0, 200, 30, 1)
        macro_qty_cap            = cmc.number_input("Qty cap", 1, 100, 15, 1)

        st.subheader("Sentiment · Breakout")
        csa, csb, csc = st.columns(3)
        sentiment_break_window   = csa.number_input("Ventana hi/lo (días)", 2, 120, 10, 1)
        sentiment_eps_bps        = csb.number_input("Epsilon breakout (bps)", 0, 200, 20, 1)
        sentiment_qty            = csc.number_input("Qty fija", 1, 100, 8, 1)

    fast = st.toggle("Modo rápido (recomendado con LLM)", value=True,
                     help="Reduce días si usás LLM para que responda más rápido.")
    st.caption("Para usar LLM necesitás `.env` con `OPENAI_API_KEY` (opcional `OPENAI_MODEL`).")

    if st.button("Run", use_container_width=True):
        # cap de días si hay LLM y modo rápido
        if fast and ("llm" in (fundamental_mode, macro_mode, sentiment_mode)):
            days = min(days, 15)

        # reiniciar logs (solo texto)
        st.session_state.exec_logs = []

        # Placeholders locales (no guardar objetos de UI en session_state)
        status = st.status("Preparando…", expanded=True)
        prog = st.progress(0.0)

        def reporter(msg, p):
            if p is not None:
                prog.progress(float(p))
            status.write(msg)
            st.session_state.exec_logs.append(msg)

        try:
            status.update(label="Descargando datos / inicializando…", state="running")
            res = run_simulation(
                days=int(days),
                symbols=symbols,
                seed=int(seed),
                user_goal=goal,
                data_source=data_source_value,
                fundamental_mode=fundamental_mode,
                macro_mode=macro_mode,
                sentiment_mode=sentiment_mode,
                # --- tuning ---
                fundamental_sma_window=int(fundamental_sma_window),
                fundamental_base_thresh=float(fundamental_base_bps) / 10_000.0,
                fundamental_qty_cap=int(fundamental_qty_cap),
                macro_mom_window=int(macro_mom_window),
                macro_thresh=float(macro_thresh_bps) / 10_000.0,
                macro_qty_cap=int(macro_qty_cap),
                sentiment_break_window=int(sentiment_break_window),
                sentiment_eps=float(sentiment_eps_bps) / 10_000.0,
                sentiment_qty=int(sentiment_qty),
                report=reporter,
            )
            st.session_state.runs.append({
                "goal": goal or "(sin objetivo)",
                "symbols": symbols,
                "days": int(days),
                "seed": int(seed),
                "data_source": data_source_value,
                "fundamental_mode": fundamental_mode,
                "macro_mode": macro_mode,
                "sentiment_mode": sentiment_mode,
                **res
            })
            status.update(label="Completado ✅", state="complete")
            st.toast("Simulación completada", icon="✅")
        except Exception as e:
            status.update(label=f"Error: {e}", state="error")
            st.exception(e)

# ========================== TABS ==========================
tab1, tab2 = st.tabs(["📈 Resultados", "🧠 Conversación de agentes"])

# === TAB 1: RESULTADOS ===
with tab1:
    if not st.session_state.runs:
        st.info("Ejecutá al menos una simulación desde la barra lateral.")
    else:
        for idx, run in enumerate(reversed(st.session_state.runs), start=1):
            st.markdown("---")
            st.subheader(f"Run #{len(st.session_state.runs)-idx+1}")
            st.caption(
                f"Objetivo: {run['goal']} | Símbolos: {', '.join(run['symbols'])} "
                f"| Días: {run['days']} | Seed: {run['seed']} | Datos: {run['data_source']}"
            )

            hist = run["history"]; trades = run["trades"]; notes = run["notes"]
            col1, col2 = st.columns([1,2])
            with col1:
                st.markdown("**Equity**")
                st.line_chart(hist.set_index("day")[["equity"]])
                price_cols = [c for c in hist.columns if c.startswith("px_")]
                if price_cols:
                    st.markdown("**Precios**")
                    st.line_chart(hist.set_index("day")[price_cols])
            with col2:
                st.markdown("**Tabla de estados (últimos 10)**")
                st.dataframe(hist.tail(10), use_container_width=True)

            st.markdown("**Trades (últimos 20)**")
            st.dataframe(trades.tail(20), use_container_width=True)

            with st.expander("📊 Comparativa por símbolo (CAGR, Sharpe, MaxDD, Return)"):
                mt = price_metrics_table(hist)
                st.dataframe(mt.style.format({
                    "period_return": "{:.2%}",
                    "cagr": "{:.2%}",
                    "sharpe": "{:.2f}",
                    "max_drawdown": "{:.2%}",
                }))

            with st.expander("🤖 Métricas del agente (Equity)"):
                eq = hist["equity"]
                em = equity_metrics(eq)
                st.table({
                    "metric": ["period_return", "cagr", "sharpe", "max_drawdown"],
                    "value": [
                        f"{em['period_return']:.2%}" if em['period_return'] == em['period_return'] else "NA",
                        f"{em['cagr']:.2%}" if em['cagr'] == em['cagr'] else "NA",
                        f"{em['sharpe']:.2f}" if em['sharpe'] == em['sharpe'] else "NA",
                        f"{em['max_drawdown']:.2%}" if em['max_drawdown'] == em['max_drawdown'] else "NA",
                    ],
                })

            with st.expander("Notas del run"):
                for n in notes:
                    st.write("- " + n)

# === TAB 2: CONVERSACIÓN DE AGENTES ===
with tab2:
    if not st.session_state.runs:
        st.info("Todavía no hay runs.")
    else:
        run = st.session_state.runs[-1]  # muestra el último run
        st.caption("Mostrando el último run. Volvé a 'Resultados' para cambiarlo.")
        transcript = run.get("transcript", [])

        views = _extract_day_views(transcript)
        if not views:
            st.info("No hay eventos para mostrar todavía.")
        for v in views:
            with st.expander(f"Día {v['day']} — decisión del comité", expanded=False):
                st.markdown(f"**Resumen:** {v['summary']}")

                # Tabla clara por símbolo: votos y decisión final
                df = pd.DataFrame([
                    {k: r[k] for k in ["Símbolo","Fundamental","Macro","Sentiment","Consenso","Final (post-riesgo)"]}
                    for r in v["rows"]
                ])
                st.dataframe(df, use_container_width=True)

                # Razonamientos cortos (si hubo LLM)
                raz = _compact_reasoning(v["agents_step"])
                if any(text for _, text in raz):
                    st.markdown("**¿Por qué? (resumen por agente)**")
                    cols = st.columns(3)
                    for i, (agent, text) in enumerate(raz):
                        with cols[i % 3]:
                            st.markdown(f"🧠 **{agent.capitalize()}**")
                            st.caption(text if text else "sin comentario")

                # Detalle opcional por símbolo (razones breves por agente)
                with st.expander("Ver detalle por símbolo"):
                    for r in v["rows"]:
                        st.markdown(f"- **{r['Símbolo']}** → Final: `{r['Final (post-riesgo)']}` | Consenso: `{r['Consenso']}`")
                        reasons = r.get("_reasons", {})
                        if reasons:
                            bullets = " · ".join([f"{k}: {v}" for k, v in reasons.items() if v])
                            if bullets:
                                st.caption(f"  ↳ {bullets}")
