import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.api.exceptions import NotFoundError, ValidationError
from src.models import CandidateProfile, SeniorityLevel

router = APIRouter()


class CandidateCreateRequest(BaseModel):
    skills: List[str] = Field(
        ...,
        min_length=1,
        description="List of candidate's skills",
        examples=[["Python", "FastAPI", "PostgreSQL", "Docker"]],
    )
    experience_years: int = Field(
        ...,
        ge=0,
        le=50,
        description="Years of professional experience",
        examples=[5],
    )
    seniority: Optional[SeniorityLevel] = Field(
        None,
        description="Seniority level (entry, mid, senior, lead, executive)",
        examples=["senior"],
    )
    location_preference: Optional[str] = Field(
        None,
        description="Preferred work location or 'remote'",
        examples=["San Francisco, CA", "Remote"],
    )
    remote_preferred: bool = Field(
        False,
        description="Whether remote work is preferred",
    )
    salary_expected: Optional[int] = Field(
        None,
        ge=0,
        description="Expected annual salary in USD",
        examples=[150000],
    )


class CandidateResponse(BaseModel):
    id: str
    skills: List[str]
    experience_years: int
    seniority: Optional[SeniorityLevel]
    location_preference: Optional[str]
    remote_preferred: bool
    salary_expected: Optional[int]


def get_db():
    from src.api.main import get_db as main_get_db
    return main_get_db()


@router.post(
    "/candidates",
    response_model=CandidateResponse,
    status_code=201,
    summary="Create candidate profile",
    description="Create a new candidate profile for job matching.",
)
async def create_candidate(
    request: CandidateCreateRequest,
    db=Depends(get_db),
) -> CandidateResponse:
    # Validate skills
    if not request.skills:
        raise ValidationError("At least one skill is required")
    
    # Clean and normalize skills
    cleaned_skills = [s.strip() for s in request.skills if s.strip()]
    if not cleaned_skills:
        raise ValidationError("At least one non-empty skill is required")
    
    # Generate unique ID
    candidate_id = str(uuid.uuid4())
    
    # Create candidate profile
    candidate = CandidateProfile(
        id=candidate_id,
        skills=cleaned_skills,
        experience_years=request.experience_years,
        seniority=request.seniority,
        location_preference=request.location_preference,
        remote_preferred=request.remote_preferred,
        salary_expected=request.salary_expected,
    )
    
    # Store in database
    db.insert_candidate(candidate)
    
    return CandidateResponse(
        id=candidate.id,
        skills=candidate.skills,
        experience_years=candidate.experience_years,
        seniority=candidate.seniority,
        location_preference=candidate.location_preference,
        remote_preferred=candidate.remote_preferred,
        salary_expected=candidate.salary_expected,
    )


@router.get(
    "/candidates/{candidate_id}",
    response_model=CandidateResponse,
    summary="Get candidate profile",
    description="Retrieve a candidate profile by ID.",
)
async def get_candidate(
    candidate_id: str,
    db=Depends(get_db),
) -> CandidateResponse:
    candidate = db.get_candidate(candidate_id)
    
    if not candidate:
        raise NotFoundError("Candidate", candidate_id)
    
    return CandidateResponse(
        id=candidate.id,
        skills=candidate.skills,
        experience_years=candidate.experience_years,
        seniority=candidate.seniority,
        location_preference=candidate.location_preference,
        remote_preferred=candidate.remote_preferred,
        salary_expected=candidate.salary_expected,
    )
