from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SeniorityLevel(str, Enum):
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"


class RawJobPosting(BaseModel):
    source: str
    external_id: str
    title: str
    company: str
    description: str
    location: Optional[str] = None
    posted_date: Optional[datetime] = None
    url: Optional[str] = None


class ExtractedRequirements(BaseModel):
    skills: List[str] = Field(default_factory=list)
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    seniority: Optional[SeniorityLevel] = None
    location: Optional[str] = None
    remote: bool = False
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    needs_review: bool = False


class StructuredJob(BaseModel):
    id: str
    source: str
    external_id: str
    title: str
    company: str
    description: str
    requirements: ExtractedRequirements
    posted_date: Optional[datetime] = None
    url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CandidateProfile(BaseModel):
    id: str
    skills: List[str]
    experience_years: int
    seniority: Optional[SeniorityLevel] = None
    location_preference: Optional[str] = None
    remote_preferred: bool = False
    salary_expected: Optional[int] = None


class WeightConfig(BaseModel):
    skill: float = 0.30
    experience: float = 0.25
    seniority: float = 0.15
    location: float = 0.15
    salary: float = 0.15

    def normalize(self) -> "WeightConfig":
        total = self.skill + self.experience + self.seniority + self.location + self.salary
        
        if total == 0:
            # Return balanced weights if all are zero
            return WeightConfig(
                skill=0.2,
                experience=0.2,
                seniority=0.2,
                location=0.2,
                salary=0.2,
            )
        
        return WeightConfig(
            skill=self.skill / total,
            experience=self.experience / total,
            seniority=self.seniority / total,
            location=self.location / total,
            salary=self.salary / total,
        )


class ScoreBreakdown(BaseModel):
    skill_score: float
    experience_score: float
    seniority_score: float
    location_score: float
    salary_score: float
    composite_score: float


class SkillAnalysis(BaseModel):
    matched_skills: List[str]
    missing_skills: List[str]
    critical_missing_skills: List[str] = Field(default_factory=list)  # >50% frequency in top jobs
    nice_to_have_skills: List[str] = Field(default_factory=list)  # <50% frequency in top jobs
    match_percentage: float


class Recommendation(BaseModel):
    job: StructuredJob
    scores: ScoreBreakdown
    skill_analysis: SkillAnalysis
    explanation: str
    rank: int


class FeedbackRecord(BaseModel):
    candidate_id: str
    job_id: str
    feedback_type: str  # "like" or "dislike"
    preset_used: Optional[str] = None
    weights_used: Optional[WeightConfig] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RankedJob(BaseModel):
    job: StructuredJob
    scores: ScoreBreakdown
