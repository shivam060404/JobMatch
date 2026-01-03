from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.api.exceptions import NotFoundError
from src.models import SeniorityLevel

router = APIRouter()

PresetType = Literal[
    "skill_focused",
    "career_growth",
    "compensation_first",
    "remote_priority",
    "balanced",
]


class JobRequirementsResponse(BaseModel):
    skills: List[str]
    experience_min: Optional[int]
    experience_max: Optional[int]
    seniority: Optional[SeniorityLevel]
    location: Optional[str]
    remote: bool
    salary_min: Optional[int]
    salary_max: Optional[int]


class JobSummaryResponse(BaseModel):
    id: str
    title: str
    company: str
    requirements: JobRequirementsResponse
    url: Optional[str]


class ScoreBreakdownResponse(BaseModel):
    skill_score: float = Field(..., ge=0, le=1)
    experience_score: float = Field(..., ge=0, le=1)
    seniority_score: float = Field(..., ge=0, le=1)
    location_score: float = Field(..., ge=0, le=1)
    salary_score: float = Field(..., ge=0, le=1)
    composite_score: float = Field(..., ge=0, le=1)


class SkillAnalysisResponse(BaseModel):
    matched_skills: List[str]
    missing_skills: List[str]
    critical_missing_skills: List[str]
    nice_to_have_skills: List[str]
    match_percentage: float = Field(..., ge=0, le=1)


class RecommendationResponse(BaseModel):
    rank: int
    job: JobSummaryResponse
    scores: ScoreBreakdownResponse
    skill_analysis: SkillAnalysisResponse
    explanation: str
    quick_summary: str


class RecommendationsListResponse(BaseModel):
    candidate_id: str
    preset_used: str
    recommendations: List[RecommendationResponse]
    total_jobs_analyzed: int


def get_db():
    from src.api.main import get_db as main_get_db
    return main_get_db()


def get_ranking_engine():
    from src.api.main import get_ranking_engine as main_get_ranking_engine
    return main_get_ranking_engine()


def get_recommendation_generator():
    from src.api.main import get_recommendation_generator as main_get_recommendation_generator
    return main_get_recommendation_generator()


@router.get(
    "/recommendations/{candidate_id}",
    response_model=RecommendationsListResponse,
    summary="Get job recommendations",
    description="Get personalized job recommendations for a candidate.",
)
async def get_recommendations(
    candidate_id: str,
    preset: PresetType = Query(
        "balanced",
        description="Weight preset profile to use for ranking",
    ),
    limit: int = Query(
        10,
        ge=1,
        le=50,
        description="Maximum number of recommendations to return",
    ),
    db=Depends(get_db),
    ranking_engine=Depends(get_ranking_engine),
    recommendation_generator=Depends(get_recommendation_generator),
) -> RecommendationsListResponse:
    # Get candidate profile
    candidate = db.get_candidate(candidate_id)
    if not candidate:
        raise NotFoundError("Candidate", candidate_id)
    
    # Check for custom weights first
    custom_weights = db.get_candidate_weights(candidate_id)
    if custom_weights:
        ranking_engine.set_weights({
            "skill": custom_weights.skill,
            "experience": custom_weights.experience,
            "seniority": custom_weights.seniority,
            "location": custom_weights.location,
            "salary": custom_weights.salary,
        })
        preset_used = "custom"
    else:
        # Use preset
        ranking_engine.set_preset(preset)
        preset_used = preset
    
    # Get all jobs
    all_jobs = db.get_all_jobs()
    
    # Rank jobs
    ranked_jobs = ranking_engine.rank(candidate, all_jobs)
    
    # Generate recommendations for top N
    top_ranked = ranked_jobs[:limit]
    recommendations = recommendation_generator.generate_batch(
        candidate=candidate,
        ranked_jobs=top_ranked,
        top_n_for_skills=min(10, len(top_ranked)),
    )
    
    # Build response
    response_recommendations = []
    for rec in recommendations:
        quick_summary = recommendation_generator.generate_quick_summary(
            rec.scores,
            rec.skill_analysis,
        )
        
        response_recommendations.append(
            RecommendationResponse(
                rank=rec.rank,
                job=JobSummaryResponse(
                    id=rec.job.id,
                    title=rec.job.title,
                    company=rec.job.company,
                    requirements=JobRequirementsResponse(
                        skills=rec.job.requirements.skills,
                        experience_min=rec.job.requirements.experience_min,
                        experience_max=rec.job.requirements.experience_max,
                        seniority=rec.job.requirements.seniority,
                        location=rec.job.requirements.location,
                        remote=rec.job.requirements.remote,
                        salary_min=rec.job.requirements.salary_min,
                        salary_max=rec.job.requirements.salary_max,
                    ),
                    url=rec.job.url,
                ),
                scores=ScoreBreakdownResponse(
                    skill_score=rec.scores.skill_score,
                    experience_score=rec.scores.experience_score,
                    seniority_score=rec.scores.seniority_score,
                    location_score=rec.scores.location_score,
                    salary_score=rec.scores.salary_score,
                    composite_score=rec.scores.composite_score,
                ),
                skill_analysis=SkillAnalysisResponse(
                    matched_skills=rec.skill_analysis.matched_skills,
                    missing_skills=rec.skill_analysis.missing_skills,
                    critical_missing_skills=rec.skill_analysis.critical_missing_skills,
                    nice_to_have_skills=rec.skill_analysis.nice_to_have_skills,
                    match_percentage=rec.skill_analysis.match_percentage,
                ),
                explanation=rec.explanation,
                quick_summary=quick_summary,
            )
        )
    
    return RecommendationsListResponse(
        candidate_id=candidate_id,
        preset_used=preset_used,
        recommendations=response_recommendations,
        total_jobs_analyzed=len(all_jobs),
    )
