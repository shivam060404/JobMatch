from typing import Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.api.exceptions import NotFoundError, ValidationError
from src.models import WeightConfig
from src.ranking import RankingEngine

router = APIRouter()


class WeightConfigResponse(BaseModel):
    skill: float = Field(..., ge=0, le=1, description="Weight for skill match")
    experience: float = Field(..., ge=0, le=1, description="Weight for experience alignment")
    seniority: float = Field(..., ge=0, le=1, description="Weight for seniority match")
    location: float = Field(..., ge=0, le=1, description="Weight for location preference")
    salary: float = Field(..., ge=0, le=1, description="Weight for salary fit")
    is_normalized: bool = Field(..., description="Whether weights sum to 1.0")


class WeightUpdateRequest(BaseModel):
    skill: float = Field(..., ge=0, description="Weight for skill match")
    experience: float = Field(..., ge=0, description="Weight for experience alignment")
    seniority: float = Field(..., ge=0, description="Weight for seniority match")
    location: float = Field(..., ge=0, description="Weight for location preference")
    salary: float = Field(..., ge=0, description="Weight for salary fit")


class WeightsResponse(BaseModel):
    candidate_id: str
    weights: WeightConfigResponse
    preset_name: str | None = Field(None, description="Name of preset if using a preset")
    available_presets: List[str]


class PresetInfo(BaseModel):
    name: str
    description: str
    weights: Dict[str, float]


class PresetsListResponse(BaseModel):
    presets: List[PresetInfo]


def get_db():
    from src.api.main import get_db as main_get_db
    return main_get_db()


def get_preset_name(weights: WeightConfig) -> str | None:
    for preset_name, preset_weights in RankingEngine.PRESETS.items():
        if (
            abs(weights.skill - preset_weights["skill"]) < 0.001
            and abs(weights.experience - preset_weights["experience"]) < 0.001
            and abs(weights.seniority - preset_weights["seniority"]) < 0.001
            and abs(weights.location - preset_weights["location"]) < 0.001
            and abs(weights.salary - preset_weights["salary"]) < 0.001
        ):
            return preset_name
    return None


@router.get(
    "/weights/{candidate_id}",
    response_model=WeightsResponse,
    summary="Get current weights",
    description="Get the current ranking weights for a candidate.",
)
async def get_weights(
    candidate_id: str,
    db=Depends(get_db),
) -> WeightsResponse:
    # Verify candidate exists
    candidate = db.get_candidate(candidate_id)
    if not candidate:
        raise NotFoundError("Candidate", candidate_id)
    
    # Get custom weights or default
    weights = db.get_candidate_weights(candidate_id)
    if weights is None:
        # Return default balanced weights
        weights = WeightConfig()
    
    # Check if weights match a preset
    preset_name = get_preset_name(weights)
    
    # Calculate if normalized
    total = weights.skill + weights.experience + weights.seniority + weights.location + weights.salary
    is_normalized = abs(total - 1.0) < 0.001
    
    return WeightsResponse(
        candidate_id=candidate_id,
        weights=WeightConfigResponse(
            skill=weights.skill,
            experience=weights.experience,
            seniority=weights.seniority,
            location=weights.location,
            salary=weights.salary,
            is_normalized=is_normalized,
        ),
        preset_name=preset_name,
        available_presets=list(RankingEngine.PRESETS.keys()),
    )


@router.put(
    "/weights/{candidate_id}",
    response_model=WeightsResponse,
    summary="Update weights",
    description="Update ranking weights for a candidate (auto-normalizes to sum to 1.0).",
)
async def update_weights(
    candidate_id: str,
    request: WeightUpdateRequest,
    db=Depends(get_db),
) -> WeightsResponse:
    # Verify candidate exists
    candidate = db.get_candidate(candidate_id)
    if not candidate:
        raise NotFoundError("Candidate", candidate_id)
    
    # Validate at least one weight is positive
    total = request.skill + request.experience + request.seniority + request.location + request.salary
    if total == 0:
        raise ValidationError("At least one weight must be greater than zero")
    
    # Create weight config and normalize
    weights = WeightConfig(
        skill=request.skill,
        experience=request.experience,
        seniority=request.seniority,
        location=request.location,
        salary=request.salary,
    ).normalize()
    
    # Store in database
    db.update_candidate_weights(candidate_id, weights)
    
    # Check if weights match a preset
    preset_name = get_preset_name(weights)
    
    return WeightsResponse(
        candidate_id=candidate_id,
        weights=WeightConfigResponse(
            skill=weights.skill,
            experience=weights.experience,
            seniority=weights.seniority,
            location=weights.location,
            salary=weights.salary,
            is_normalized=True,  # Always normalized after update
        ),
        preset_name=preset_name,
        available_presets=list(RankingEngine.PRESETS.keys()),
    )


@router.get(
    "/presets",
    response_model=PresetsListResponse,
    summary="List available presets",
    description="Get a list of all available weight presets with descriptions.",
)
async def list_presets() -> PresetsListResponse:
    preset_descriptions = {
        "skill_focused": "Prioritizes skill match (50% weight on skills)",
        "career_growth": "Emphasizes experience alignment (35% weight on experience)",
        "compensation_first": "Focuses on salary fit (35% weight on salary)",
        "remote_priority": "Prioritizes location/remote match (30% weight on location)",
        "balanced": "Equal consideration of all factors",
    }
    
    presets = []
    for name, weights in RankingEngine.PRESETS.items():
        presets.append(
            PresetInfo(
                name=name,
                description=preset_descriptions.get(name, ""),
                weights=weights,
            )
        )
    
    return PresetsListResponse(presets=presets)
