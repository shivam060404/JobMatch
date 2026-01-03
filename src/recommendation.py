from collections import Counter
from typing import List, Optional, Set
from src.models import (
    CandidateProfile,
    RankedJob,
    Recommendation,
    ScoreBreakdown,
    SkillAnalysis,
    StructuredJob,
)


class RecommendationGenerator:

    def generate(
        self,
        candidate: CandidateProfile,
        ranked_job: RankedJob,
        top_jobs_skills: Optional[List[Set[str]]] = None,
    ) -> Recommendation:
        skill_analysis = self.list_skill_gaps(
            set(candidate.skills),
            set(ranked_job.job.requirements.skills),
            top_jobs_skills=top_jobs_skills,
        )

        explanation = self.explain_match(
            ranked_job.scores,
            candidate,
            ranked_job.job,
            skill_analysis=skill_analysis,
        )

        return Recommendation(
            job=ranked_job.job,
            scores=ranked_job.scores,
            skill_analysis=skill_analysis,
            explanation=explanation,
            rank=0,  # Set by caller
        )


    def explain_match(
        self,
        scores: ScoreBreakdown,
        candidate: CandidateProfile,
        job: StructuredJob,
        skill_analysis: Optional[SkillAnalysis] = None,
    ) -> str:
        lines = []
        req = job.requirements
        match_pct = int(scores.composite_score * 100)

        # Header with emoji based on match quality
        if match_pct >= 85:
            lines.append(f"🎯 **Excellent match ({match_pct}%)!**")
        elif match_pct >= 70:
            lines.append(f"✨ **Strong match ({match_pct}%)**")
        elif match_pct >= 55:
            lines.append(f"👍 **Good potential ({match_pct}%)**")
        else:
            lines.append(f"📊 **Partial match ({match_pct}%)**")

        # Skill breakdown with specific skills mentioned
        if skill_analysis:
            total_required = len(skill_analysis.matched_skills) + len(skill_analysis.missing_skills)
            matched_count = len(skill_analysis.matched_skills)

            if total_required > 0:
                lines.append(f"\nYou have **{matched_count}/{total_required}** key skills:")

                # Show matched skills (max 3)
                for skill in skill_analysis.matched_skills[:3]:
                    lines.append(f"  • ✅ {skill}")

                # Show critical missing skills with learning suggestion
                if skill_analysis.critical_missing_skills:
                    lines.append("\n**Skills to prioritize:**")
                    for skill in skill_analysis.critical_missing_skills[:2]:
                        lines.append(f"  • ⚠️ {skill} *(high demand in similar roles)*")

                # Show nice-to-have skills
                if skill_analysis.nice_to_have_skills and not skill_analysis.critical_missing_skills:
                    lines.append("\n**Nice to have:**")
                    for skill in skill_analysis.nice_to_have_skills[:2]:
                        lines.append(f"  • 📚 {skill}")
        else:
            # Fallback to generic skill explanation
            if scores.skill_score >= 0.8:
                lines.append("\n✅ Your skills align very well with this role.")
            elif scores.skill_score >= 0.5:
                lines.append("\n👍 You have several relevant skills for this position.")
            else:
                lines.append("\n📚 This role requires skills you may want to develop.")

        # Experience insight
        lines.append("")
        if scores.experience_score >= 0.9:
            lines.append(f"✅ Your {candidate.experience_years} years of experience is ideal for this role.")
        elif scores.experience_score >= 0.7:
            lines.append(f"👍 Your {candidate.experience_years} years experience is a reasonable fit.")
        elif candidate.experience_years < (req.experience_min or 0):
            gap = (req.experience_min or 0) - candidate.experience_years
            lines.append(f"⚠️ This role typically requires {gap}+ more years of experience.")
        else:
            lines.append(f"👍 Your experience level is compatible with this role.")

        # Location/Remote alignment
        if scores.location_score >= 0.9:
            if req.remote and candidate.remote_preferred:
                lines.append("✅ Remote position - matches your preference!")
            elif not req.remote and req.location:
                lines.append(f"✅ Location ({req.location}) matches your preference.")
        elif req.remote:
            lines.append("🌍 Remote work available for this role.")

        # Salary alignment
        if req.salary_max:
            if scores.salary_score >= 0.9:
                lines.append(f"💰 Salary range (${req.salary_min:,}-${req.salary_max:,}) aligns with your expectations.")
            elif scores.salary_score < 0.5 and candidate.salary_expected:
                lines.append(f"💡 Salary (${req.salary_max:,}) may be below your target.")

        return "\n".join(lines)


    def generate_quick_summary(
        self,
        scores: ScoreBreakdown,
        skill_analysis: SkillAnalysis,
    ) -> str:
        match_pct = int(scores.composite_score * 100)
        matched = len(skill_analysis.matched_skills)
        total = matched + len(skill_analysis.missing_skills)

        if match_pct >= 85:
            return f"🎯 Excellent fit! {matched}/{total} skills match"
        elif match_pct >= 70:
            return f"✨ Strong match with {matched}/{total} skills"
        elif match_pct >= 55:
            return f"👍 Good potential - {total - matched} skills to develop"
        else:
            return f"📊 Partial match - consider for growth opportunity"

    def list_skill_gaps(
        self,
        candidate_skills: Set[str],
        job_skills: Set[str],
        top_jobs_skills: Optional[List[Set[str]]] = None,
    ) -> SkillAnalysis:
        candidate_normalized = {s.lower().strip() for s in candidate_skills}
        job_normalized = {s.lower().strip() for s in job_skills}

        matched = candidate_normalized & job_normalized
        missing = job_normalized - candidate_normalized

        # Map back to original case from job skills
        matched_original = [s for s in job_skills if s.lower().strip() in matched]
        missing_original = [s for s in job_skills if s.lower().strip() in missing]

        match_pct = len(matched) / len(job_normalized) if job_normalized else 1.0

        # Classify missing skills by priority
        critical_skills: List[str] = []
        nice_to_have_skills: List[str] = []

        if top_jobs_skills and missing_original:
            # Count frequency of each missing skill across top jobs
            skill_frequency: Counter = Counter()
            for job_skill_set in top_jobs_skills:
                for skill in job_skill_set:
                    skill_frequency[skill.lower().strip()] += 1

            total_jobs = len(top_jobs_skills)
            for skill in missing_original:
                freq = skill_frequency.get(skill.lower().strip(), 0)
                frequency_pct = freq / total_jobs if total_jobs > 0 else 0

                # Critical: mentioned in >50% of top jobs
                if frequency_pct >= 0.5:
                    critical_skills.append(skill)
                else:
                    nice_to_have_skills.append(skill)
        else:
            # Without frequency data, all missing skills are nice-to-have
            nice_to_have_skills = missing_original

        return SkillAnalysis(
            matched_skills=matched_original,
            missing_skills=missing_original,
            critical_missing_skills=critical_skills,
            nice_to_have_skills=nice_to_have_skills,
            match_percentage=match_pct,
        )

    def generate_batch(
        self,
        candidate: CandidateProfile,
        ranked_jobs: List[RankedJob],
        top_n_for_skills: int = 10,
    ) -> List[Recommendation]:
        top_jobs_skills: List[Set[str]] = []
        for ranked_job in ranked_jobs[:top_n_for_skills]:
            top_jobs_skills.append(set(ranked_job.job.requirements.skills))

        recommendations: List[Recommendation] = []
        for rank, ranked_job in enumerate(ranked_jobs, start=1):
            recommendation = self.generate(
                candidate=candidate,
                ranked_job=ranked_job,
                top_jobs_skills=top_jobs_skills,
            )
            recommendation.rank = rank
            recommendations.append(recommendation)

        return recommendations
