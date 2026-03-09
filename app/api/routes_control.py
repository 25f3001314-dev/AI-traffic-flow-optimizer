from __future__ import annotations

from fastapi import APIRouter

from app.core.decision_engine import DecisionEngine
from app.core.schemas import DecisionRequest, DecisionResponse

router = APIRouter(prefix="/api/control", tags=["control"])


@router.post("/decide", response_model=DecisionResponse)
def decide(request: DecisionRequest) -> DecisionResponse:
    engine = DecisionEngine(weights=request.weights)
    return engine.decide(state=request.junction_state, history=request.history)
