from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.api.exceptions import NotFoundError, ValidationError
from src.models import FeedbackRecord, WeightConfig

router = APIRouter()

FeedbackType = Literal["like", "dislike"]


class FeedbackRequest(BaseModel):
    candidate_id: str = Field(..., description="ID of the candidate providing feedback")
    job_id: str = Field(..., description="ID of the job being rated")
    feedback_type: FeedbackType = Field(..., description="Type of feedback: 'like' or 'dislike'")
    preset_used: Optional[str] = Field(None, description="Name of preset used when viewing this job")


class FeedbackResponse(BaseModel):
    id: int
    candidate_id: str
    job_id: str
    feedback_type: str
    preset_used: Optional[str]
    timestamp: str
    message: str


def get_db():
    from src.api.main import get_db as main_get_db
    return main_get_db()


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=201,
    summary="Submit feedback",
    description="Submit like/dislike feedback for a job recommendation.",
)
async def submit_feedback(
    request: FeedbackRequest,
    db=Depends(get_db),
) -> FeedbackResponse:
    # Verify candidate exists
    candidate = db.get_candidate(request.candidate_id)
    if not candidate:
        raise NotFoundError("Candidate", request.candidate_id)
    
    # Verify job exists
    job = db.get_job(request.job_id)
    if not job:
        raise NotFoundError("Job", request.job_id)
    
    # Get current weights for the candidate
    weights = db.get_candidate_weights(request.candidate_id)
    
    # Create feedback record
    timestamp = datetime.utcnow()
    feedback = FeedbackRecord(
        candidate_id=request.candidate_id,
        job_id=request.job_id,
        feedback_type=request.feedback_type,
        preset_used=request.preset_used,
        weights_used=weights,
        timestamp=timestamp,
    )
    
    # Store feedback
    feedback_id = db.insert_feedback(feedback)
    
    return FeedbackResponse(
        id=feedback_id,
        candidate_id=request.candidate_id,
        job_id=request.job_id,
        feedback_type=request.feedback_type,
        preset_used=request.preset_used,
        timestamp=timestamp.isoformat(),
        message=f"Feedback recorded: {request.feedback_type} for job {job.title} at {job.company}",
    )
