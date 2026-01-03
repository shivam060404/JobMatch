from collections import Counter
from typing import Dict, List, Optional, Set

from pydantic import BaseModel

from src.database import Database
from src.models import StructuredJob
from src.ranking import RankingEngine


class UserPatterns(BaseModel):
    remote_preference: bool
    min_preferred_salary: Optional[int] = None
    preferred_seniority: Optional[str] = None
    top_skills: List[str]
    sample_size: int
    # Enhanced patterns
    tech_stack_preference: Optional[str] = None  # "python", "javascript", "go", etc.
    role_type_preference: Optional[str] = None  # "backend", "frontend", "fullstack", "data", "ml", "devops"
    company_type_preference: Optional[str] = None  # "startup", "enterprise", "mid-size"
    geographic_preference: Optional[str] = None  # "us", "europe", "asia", "remote-global"


class PresetStats(BaseModel):
    total_interactions: int
    like_rate: float


class AnalyticsService:

    # Tech stack classification
    TECH_STACKS: Dict[str, Set[str]] = {
        "python": {"python", "django", "flask", "fastapi", "pandas", "numpy"},
        "javascript": {"javascript", "react", "vue", "angular", "node", "typescript"},
        "go": {"go", "golang"},
        "java": {"java", "spring", "kotlin"},
        "rust": {"rust"},
        "ml": {"machine learning", "tensorflow", "pytorch", "scikit-learn", "ml", "ai"},
    }

    # Role type classification based on skills
    ROLE_TYPES: Dict[str, Set[str]] = {
        "backend": {"api", "database", "sql", "rest", "microservices", "server"},
        "frontend": {"react", "vue", "angular", "css", "html", "ui", "ux"},
        "fullstack": {"fullstack", "full-stack", "full stack"},
        "data": {"data engineering", "etl", "spark", "airflow", "data pipeline"},
        "ml": {"machine learning", "deep learning", "nlp", "computer vision", "llm"},
        "devops": {"kubernetes", "docker", "ci/cd", "terraform", "aws", "devops"},
    }

    # Company type indicators (from job titles/descriptions)
    COMPANY_INDICATORS: Dict[str, Set[str]] = {
        "startup": {"startup", "early-stage", "seed", "series a", "fast-paced", "wear many hats"},
        "enterprise": {"fortune 500", "enterprise", "large-scale", "global company", "established"},
        "mid-size": {"growing company", "mid-size", "scale-up"},
    }

    # Geographic keywords
    US_KEYWORDS: Set[str] = {
        "usa", "united states", "new york", "san francisco", "seattle", 
        "austin", "boston", "los angeles", "chicago", "denver"
    }
    EUROPE_KEYWORDS: Set[str] = {
        "uk", "london", "berlin", "amsterdam", "paris", "europe", 
        "germany", "france", "netherlands", "spain", "ireland"
    }
    ASIA_KEYWORDS: Set[str] = {
        "singapore", "tokyo", "india", "bangalore", "asia", 
        "hong kong", "shanghai", "seoul"
    }


    def __init__(self, db: Database):
        self.db = db

    def get_user_patterns(self, candidate_id: str) -> Optional[UserPatterns]:
        likes = self.db.get_feedback_by_candidate(candidate_id, feedback_type="like")

        if len(likes) < 3:
            return None  # Need at least 3 samples

        liked_jobs: List[StructuredJob] = []
        for feedback in likes:
            job = self.db.get_job(feedback.job_id)
            if job:
                liked_jobs.append(job)

        if not liked_jobs:
            return None

        # Rule 1: Remote preference (>60% liked jobs are remote)
        remote_count = sum(1 for j in liked_jobs if j.requirements.remote)
        remote_preference = remote_count / len(liked_jobs) > 0.6

        # Rule 2: Salary preference (average of liked jobs)
        salaries = [
            j.requirements.salary_max 
            for j in liked_jobs 
            if j.requirements.salary_max
        ]
        min_preferred_salary = int(sum(salaries) / len(salaries) * 0.9) if salaries else None

        # Rule 3: Seniority preference (most common)
        seniorities = [
            j.requirements.seniority.value 
            for j in liked_jobs 
            if j.requirements.seniority
        ]
        preferred_seniority = None
        if seniorities:
            seniority_counts = Counter(seniorities)
            preferred_seniority = seniority_counts.most_common(1)[0][0]

        # Rule 4: Top skills (most common across liked jobs)
        all_skills: List[str] = []
        for j in liked_jobs:
            all_skills.extend(j.requirements.skills)
        skill_counts = Counter(all_skills)
        top_skills = [s for s, _ in skill_counts.most_common(5)]

        # Rule 5: Tech stack preference
        tech_stack_preference = self._detect_tech_stack(all_skills)

        # Rule 6: Role type preference
        role_type_preference = self._detect_role_type(all_skills, liked_jobs)

        # Rule 7: Company type preference
        company_type_preference = self._detect_company_type(liked_jobs)

        # Rule 8: Geographic preference
        geographic_preference = self._detect_geographic_preference(liked_jobs)

        return UserPatterns(
            remote_preference=remote_preference,
            min_preferred_salary=min_preferred_salary,
            preferred_seniority=preferred_seniority,
            top_skills=top_skills,
            sample_size=len(likes),
            tech_stack_preference=tech_stack_preference,
            role_type_preference=role_type_preference,
            company_type_preference=company_type_preference,
            geographic_preference=geographic_preference,
        )


    def _detect_tech_stack(self, skills: List[str]) -> Optional[str]:
        skill_set = {s.lower() for s in skills}
        stack_scores: Dict[str, int] = {}

        for stack, keywords in self.TECH_STACKS.items():
            matches = len(skill_set & keywords)
            if matches > 0:
                stack_scores[stack] = matches

        if stack_scores:
            return max(stack_scores, key=stack_scores.get)
        return None

    def _detect_role_type(
        self, 
        skills: List[str], 
        jobs: List[StructuredJob],
    ) -> Optional[str]:
        skill_set = {s.lower() for s in skills}
        title_words: Set[str] = set()
        for j in jobs:
            title_words.update(j.title.lower().split())

        combined = skill_set | title_words
        role_scores: Dict[str, int] = {}

        for role, keywords in self.ROLE_TYPES.items():
            matches = len(combined & keywords)
            if matches > 0:
                role_scores[role] = matches

        if role_scores:
            return max(role_scores, key=role_scores.get)
        return None

    def _detect_company_type(self, jobs: List[StructuredJob]) -> Optional[str]:
        type_scores: Dict[str, int] = {"startup": 0, "enterprise": 0, "mid-size": 0}

        for j in jobs:
            desc_lower = (j.description or "").lower()
            for company_type, keywords in self.COMPANY_INDICATORS.items():
                for keyword in keywords:
                    if keyword in desc_lower:
                        type_scores[company_type] += 1

        max_score = max(type_scores.values())
        if max_score > 0:
            return max(type_scores, key=type_scores.get)
        return None

    def _detect_geographic_preference(self, jobs: List[StructuredJob]) -> Optional[str]:
        geo_scores: Dict[str, int] = {"us": 0, "europe": 0, "asia": 0, "remote-global": 0}

        for j in jobs:
            location = (j.requirements.location or "").lower()
            
            if j.requirements.remote:
                geo_scores["remote-global"] += 1
            
            for kw in self.US_KEYWORDS:
                if kw in location:
                    geo_scores["us"] += 1
                    break
            
            for kw in self.EUROPE_KEYWORDS:
                if kw in location:
                    geo_scores["europe"] += 1
                    break
            
            for kw in self.ASIA_KEYWORDS:
                if kw in location:
                    geo_scores["asia"] += 1
                    break

        max_score = max(geo_scores.values())
        if max_score > 0:
            return max(geo_scores, key=geo_scores.get)
        return None


    def suggest_weights_from_behavior(self, candidate_id: str) -> Optional[Dict[str, float]]:
        patterns = self.get_user_patterns(candidate_id)

        if not patterns or patterns.sample_size < 5:
            return None  # Need at least 5 samples for suggestions

        # Start with balanced preset
        suggested = RankingEngine.PRESETS["balanced"].copy()

        # Rule: If user likes remote jobs, boost location weight
        if patterns.remote_preference:
            suggested["location"] = 0.30
            suggested["skill"] = 0.25

        # Rule: If user likes high-salary jobs, boost salary weight
        if patterns.min_preferred_salary and patterns.min_preferred_salary > 150_000:
            suggested["salary"] = 0.25
            suggested["skill"] = 0.25

        # Rule: If user prefers ML roles, boost skill weight (ML skills are specialized)
        if patterns.role_type_preference == "ml":
            suggested["skill"] = 0.40
            suggested["experience"] = 0.25

        # Rule: If user prefers startups, experience matters less
        if patterns.company_type_preference == "startup":
            suggested["experience"] = 0.15
            suggested["skill"] = 0.35

        # Normalize to sum to 1.0
        total = sum(suggested.values())
        suggested = {k: v / total for k, v in suggested.items()}

        return suggested

    def get_preset_effectiveness(self) -> Dict[str, PresetStats]:
        all_feedback = self.db.get_all_feedback()

        preset_stats: Dict[str, PresetStats] = {}
        
        for preset in RankingEngine.PRESETS.keys():
            preset_feedback = [f for f in all_feedback if f.preset_used == preset]
            
            if preset_feedback:
                likes = sum(1 for f in preset_feedback if f.feedback_type == "like")
                total = len(preset_feedback)
                preset_stats[preset] = PresetStats(
                    total_interactions=total,
                    like_rate=likes / total if total > 0 else 0,
                )

        return preset_stats

    def get_feedback_summary(self, candidate_id: str) -> Dict[str, int]:
        all_feedback = self.db.get_feedback_by_candidate(candidate_id)
        
        likes = sum(1 for f in all_feedback if f.feedback_type == "like")
        dislikes = sum(1 for f in all_feedback if f.feedback_type == "dislike")
        
        return {
            "likes": likes,
            "dislikes": dislikes,
            "total": len(all_feedback),
        }

    def get_skill_demand(self, limit: int = 20) -> List[tuple]:
        all_jobs = self.db.get_all_jobs()
        
        skill_counts: Counter = Counter()
        for job in all_jobs:
            for skill in job.requirements.skills:
                skill_counts[skill.lower()] += 1
        
        return skill_counts.most_common(limit)
