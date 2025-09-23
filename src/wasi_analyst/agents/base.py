from dataclasses import dataclass
from typing import Dict, Literal
from wasi_analyst.util.config import WasiConfig

AgentMode = Literal["rule", "llm"]

@dataclass
class AgentState:
    cash: float
    positions: Dict[str, int]

@dataclass
class BaseAgent:
    agent_id: str
    cfg: WasiConfig
    state: AgentState
    mode: AgentMode = "rule"  # "llm" para usar LLM

    def decide(self, obs: Dict) -> Dict:
        raise NotImplementedError
