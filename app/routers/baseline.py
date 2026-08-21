"""Router for the baseline agent."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.models.user import User
from app.core.deps import get_current_user
from app.baseline.dumb_baseline import answer_question_baseline

router = APIRouter(prefix="/baseline", tags=["baseline"])

class BaselineAskRequest(BaseModel):
    question: str

@router.post("/ask")
def ask_baseline(
    req: BaselineAskRequest,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Ask a question to the dumb baseline RAG implementation."""
    try:
        result = answer_question_baseline(user_id=current_user.id, question=req.question)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Baseline query failed: {str(e)}",
        )
        
    return {
        "status": "success",
        "data": result
    }
