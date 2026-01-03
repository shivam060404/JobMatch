import json
import logging
import time
from typing import Optional

from groq import Groq

from src.models import ExtractedRequirements, RawJobPosting, SeniorityLevel

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    pass


class RequirementExtractor:

    EXTRACTION_PROMPT = """Extract job requirements from this posting. Return ONLY valid JSON.

Job Title: {title}
Company: {company}
Description: {description}

Return this exact JSON structure:
{{
    "skills": ["skill1", "skill2"],
    "experience_min": 2,
    "experience_max": 5,
    "seniority": "mid",
    "location": "San Francisco, CA",
    "remote": true,
    "salary_min": 80000,
    "salary_max": 120000
}}

Rules:
- skills: List of technical skills mentioned (max 15)
- experience_min/max: Years required (null if not mentioned)
- seniority: One of "entry", "mid", "senior", "lead", "executive" (null if unclear)
- location: City/state or "Remote" (null if not mentioned)
- remote: true if remote work mentioned, false otherwise
- salary_min/max: Annual salary in USD (null if not mentioned)

Example input: "Senior Python Developer, 5+ years experience, remote OK, $150k-180k"
Example output: {{"skills": ["Python"], "experience_min": 5, "experience_max": null, "seniority": "senior", "location": null, "remote": true, "salary_min": 150000, "salary_max": 180000}}

Now extract from the job posting above. Return ONLY the JSON, no explanation."""

    def __init__(self, groq_api_key: str, model: str = "llama-3.1-8b-instant"):
        self.client = Groq(api_key=groq_api_key)
        self.model = model
        self._extraction_stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "needs_review": 0,
        }
        logger.info(f"Initialized RequirementExtractor with model: {model}")

    def extract(self, raw_posting: RawJobPosting) -> ExtractedRequirements:
        self._extraction_stats["total"] += 1
        prompt = self._build_prompt(raw_posting)

        for attempt in range(3):
            try:
                start_time = time.time()
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=500,
                )
                latency = time.time() - start_time

                result = self._parse_response(response.choices[0].message.content)

                if result.needs_review:
                    self._extraction_stats["needs_review"] += 1
                else:
                    self._extraction_stats["success"] += 1

                logger.debug(
                    f"Extracted requirements for '{raw_posting.title}' "
                    f"in {latency:.2f}s (attempt {attempt + 1})"
                )
                return result

            except Exception as e:
                if attempt < 2:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"Extraction attempt {attempt + 1} failed for "
                        f"'{raw_posting.title}': {e}. Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue

                self._extraction_stats["failed"] += 1
                logger.error(
                    f"Extraction failed after 3 attempts for '{raw_posting.title}': {e}"
                )
                raise ExtractionError(f"Failed after 3 attempts: {e}")

    def _build_prompt(self, posting: RawJobPosting) -> str:
        description = posting.description[:3000] if posting.description else ""

        return self.EXTRACTION_PROMPT.format(
            title=posting.title or "",
            company=posting.company or "",
            description=description,
        )

    def _parse_response(self, response: str) -> ExtractedRequirements:
        try:
            # Handle markdown code blocks
            cleaned_response = response.strip()
            if "```json" in cleaned_response:
                cleaned_response = cleaned_response.split("```json")[1].split("```")[0]
            elif "```" in cleaned_response:
                cleaned_response = cleaned_response.split("```")[1].split("```")[0]

            data = json.loads(cleaned_response.strip())

            # Validate and convert seniority
            seniority = None
            raw_seniority = data.get("seniority")
            if raw_seniority:
                seniority_lower = str(raw_seniority).lower().strip()
                if seniority_lower in ["entry", "mid", "senior", "lead", "executive"]:
                    seniority = SeniorityLevel(seniority_lower)

            # Parse and validate skills
            raw_skills = data.get("skills", [])
            if isinstance(raw_skills, list):
                skills = [
                    s.strip() for s in raw_skills
                    if isinstance(s, str) and s.strip()
                ][:15]  # Max 15 skills
            else:
                skills = []

            # Parse experience values
            experience_min = self._parse_int(data.get("experience_min"))
            experience_max = self._parse_int(data.get("experience_max"))

            # Parse salary values
            salary_min = self._parse_int(data.get("salary_min"))
            salary_max = self._parse_int(data.get("salary_max"))

            # Parse location
            location = data.get("location")
            if location and isinstance(location, str):
                location = location.strip() or None
            else:
                location = None

            # Parse remote flag
            remote = bool(data.get("remote", False))

            return ExtractedRequirements(
                skills=skills,
                experience_min=experience_min,
                experience_max=experience_max,
                seniority=seniority,
                location=location,
                remote=remote,
                salary_min=salary_min,
                salary_max=salary_max,
                needs_review=False,
            )

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}. Response: {response[:200]}...")
            # Fallback: return empty requirements, mark for manual review
            return ExtractedRequirements(skills=[], needs_review=True)

        except Exception as e:
            logger.warning(f"Unexpected parsing error: {e}. Response: {response[:200]}...")
            return ExtractedRequirements(skills=[], needs_review=True)

    def _parse_int(self, value) -> Optional[int]:
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                # Handle strings like "5+" or "5 years"
                cleaned = ''.join(c for c in value if c.isdigit())
                return int(cleaned) if cleaned else None
        except (ValueError, TypeError):
            pass
        return None

    def get_stats(self) -> dict:
        return self._extraction_stats.copy()

    def reset_stats(self) -> None:
        self._extraction_stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "needs_review": 0,
        }
