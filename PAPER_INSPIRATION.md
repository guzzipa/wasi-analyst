# 📑 Paper Inspiration: StockAgent (arXiv:2407.18957)

Este proyecto se inspira en el paper:  
**“When AI Meets Finance (StockAgent): Large Language Model-based Stock Trading in Simulated Real-world Environments”**  
👉 [Link al paper en arXiv](https://arxiv.org/pdf/2407.18957)

## 🌍 Contexto
Los enfoques clásicos de backtesting con datos históricos tienen limitaciones:  
- Sesgo retrospectivo (los modelos “saben” el futuro).  
- Incapacidad de capturar dinámicas emergentes.  
- Poca representación del comportamiento real de inversores frente a noticias o shocks externos.  

StockAgent propone un **laboratorio de simulación con agentes LLM** que actúan como traders, integrando factores financieros y extrafinancieros.

---

## 🏗 Arquitectura de StockAgent
- **Agentes de inversión**: cada uno con personalidad (conservador, agresivo, balanceado), capital y reglas de riesgo.  
- **Libro de órdenes (Orderbook)**: procesamiento de órdenes de compra/venta, ejecución y precios.  
- **Módulo BBS (foro interno)**: los agentes publican “tips” diarios que influyen a otros.  
- **Condiciones externas**: tasas de interés, noticias, reportes financieros, política monetaria.  

📈 El ciclo diario incluye: preparación (intereses, deuda, eventos), sesiones de trading y publicación de expectativas.

---

## 🔍 Preguntas de investigación (RQ)
1. **Simulación efectiva**: ¿los LLMs se comportan de manera creíble al tradear?  
2. **Fiabilidad de los LLMs**: ¿cómo impactan sus sesgos en las decisiones?  
3. **Efecto de factores externos**: ¿qué cambia si quitamos tasas, comunicación en foros, o noticias?  

---

## 🎯 Contribuciones
- Sistema multi-agente con LLMs simulando un mercado realista.  
- Inclusión de factores “no-precio” (macro, foros, noticias) en la toma de decisiones.  
- Evaluación comparativa de diferentes LLMs (ej. GPT-3.5 vs Gemini) en escenarios de 10 días.  
- Análisis de qué inputs externos impactan más en los precios simulados.  

---

## ⚠️ Limitaciones
- Simulación, no trading real.  
- Las configuraciones (perfiles de agentes, reglas de BBS, costos) pueden sesgar resultados.  
- Alto costo computacional al escalar con muchos agentes.  
- Generalización limitada: los sesgos del LLM no necesariamente reflejan la dinámica real del mercado.  

---

👉 **En este proyecto (Wasi Analyst)**, tomamos inspiración de StockAgent, adaptando la idea de agentes LLM y reglas heurísticas, pero con foco en:  
- Integración práctica con datos financieros (ej. Yahoo Finance).  
- Visualización clara de equity, posiciones y precios.  
- Posibilidad de extender con agentes de riesgo, ejecución y lógica configurable.  
