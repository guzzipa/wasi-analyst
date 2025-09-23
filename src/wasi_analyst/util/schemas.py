from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional

class Action(BaseModel):
    action: Literal["buy","sell","hold"]
    symbol: str
    qty: int = Field(ge=0)
    price: Optional[float] = None   # None => market order
    reason: str = ""

    @field_validator("qty")
    @classmethod
    def _q(cls, v):
        if v is None: return 0
        return v

class LoanDecision(BaseModel):
    take_loan: bool = False
    amount: float = 0.0
    reason: str = ""

class Estimate(BaseModel):
    symbol: str
    target_price: float
    horizon_days: int = 30
    rationale: str = ""
