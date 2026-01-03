from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.api.exceptions import NotFoundError
from src.models import ExtractedRequirements, SeniorityLevel, StructuredJob

router = APIRouter()


class JobRequirementsResponse(BaseModel):
    skills: List[str]
    experience_min: Optional[int]
    experience_max: Optional[int]
    seniority: Optional[SeniorityLevel]
    location: Optional[str]
    remote: bool
    salary_min: Optional[int]
    salary_max: Optional[int]


class JobResponse(BaseModel):
    id: str
    source: str
    title: str
    company: str
    description: str
    requirements: JobRequirementsResponse
    url: Optional[str]
    posted_date: Optional[str]


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


def get_db():
    from src.api.main import get_db as main_get_db
    return main_get_db()


def job_to_response(job: StructuredJob) -> JobResponse:
    return JobResponse(
        id=job.id,
        source=job.source,
        title=job.title,
        company=job.company,
        description=job.description[:500] + "..." if len(job.description) > 500 else job.description,
        requirements=JobRequirementsResponse(
            skills=job.requirements.skills,
            experience_min=job.requirements.experience_min,
            experience_max=job.requirements.experience_max,
            seniority=job.requirements.seniority,
            location=job.requirements.location,
            remote=job.requirements.remote,
            salary_min=job.requirements.salary_min,
            salary_max=job.requirements.salary_max,
        ),
        url=job.url,
        posted_date=job.posted_date.isoformat() if job.posted_date else None,
    )


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="List jobs",
    description="Get a paginated list of jobs with optional filtering.",
)
async def list_jobs(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of jobs to return"),
    offset: int = Query(0, ge=0, description="Number of jobs to skip"),
    seniority: Optional[SeniorityLevel] = Query(None, description="Filter by seniority level"),
    remote: Optional[bool] = Query(None, description="Filter by remote availability"),
    min_salary: Optional[int] = Query(None, ge=0, description="Filter by minimum salary"),
    max_experience: Optional[int] = Query(None, ge=0, description="Filter by maximum experience required"),
    db=Depends(get_db),
) -> JobListResponse:
    # Get filtered jobs
    jobs = db.get_jobs(
        limit=limit,
        offset=offset,
        seniority=seniority.value if seniority else None,
        remote=remote,
        min_salary=min_salary,
        max_experience=max_experience,
    )
    
    # Get total count for pagination
    total = db.count_jobs()
    
    return JobListResponse(
        jobs=[job_to_response(job) for job in jobs],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(jobs) < total,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get job details",
    description="Get detailed information about a specific job.",
)
async def get_job(
    job_id: str,
    db=Depends(get_db),
) -> JobResponse:
    job = db.get_job(job_id)
    
    if not job:
        raise NotFoundError("Job", job_id)
    
    # Return full description for detail view
    return JobResponse(
        id=job.id,
        source=job.source,
        title=job.title,
        company=job.company,
        description=job.description,  # Full description
        requirements=JobRequirementsResponse(
            skills=job.requirements.skills,
            experience_min=job.requirements.experience_min,
            experience_max=job.requirements.experience_max,
            seniority=job.requirements.seniority,
            location=job.requirements.location,
            remote=job.requirements.remote,
            salary_min=job.requirements.salary_min,
            salary_max=job.requirements.salary_max,
        ),
        url=job.url,
        posted_date=job.posted_date.isoformat() if job.posted_date else None,
    )
