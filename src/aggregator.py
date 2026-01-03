import hashlib
import logging
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from src.models import RawJobPosting, StructuredJob, ExtractedRequirements

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def __bool__(self) -> bool:
        return self.is_valid


def validate_job(job: StructuredJob) -> ValidationResult:
    errors = []
    warnings = []
    
    # Required field checks
    if not job.id or not job.id.strip():
        errors.append("Job ID is required")
    
    if not job.title or not job.title.strip():
        errors.append("Job title is required")
    elif len(job.title.strip()) < 3:
        errors.append("Job title must be at least 3 characters")
    elif len(job.title) > 500:
        warnings.append("Job title is unusually long (>500 chars)")
    
    if not job.company or not job.company.strip():
        errors.append("Company name is required")
    elif job.company.strip().lower() in ["unknown", "n/a", "na", "-", "none"]:
        warnings.append("Company name appears to be a placeholder")
    
    if not job.source or not job.source.strip():
        errors.append("Job source is required")
    
    # Description quality checks
    if not job.description or len(job.description.strip()) < 10:
        warnings.append("Job description is missing or very short")
    elif len(job.description) > 50000:
        warnings.append("Job description is unusually long (>50K chars)")
    
    # URL validation (if present)
    if job.url:
        if not job.url.startswith(("http://", "https://")):
            warnings.append("Job URL does not start with http:// or https://")
    
    # Requirements validation
    if job.requirements:
        req = job.requirements
        
        # Experience range validation
        if req.experience_min is not None and req.experience_max is not None:
            if req.experience_min > req.experience_max:
                errors.append("Experience min cannot be greater than max")
            if req.experience_min < 0:
                errors.append("Experience min cannot be negative")
            if req.experience_max > 50:
                warnings.append("Experience max seems unusually high (>50 years)")
        
        # Salary range validation
        if req.salary_min is not None and req.salary_max is not None:
            if req.salary_min > req.salary_max:
                errors.append("Salary min cannot be greater than max")
            if req.salary_min < 0:
                errors.append("Salary min cannot be negative")
            if req.salary_max > 10_000_000:
                warnings.append("Salary max seems unusually high (>$10M)")
        
        # Skills validation
        if req.skills:
            if len(req.skills) > 50:
                warnings.append("Unusually high number of skills (>50)")
            for skill in req.skills:
                if len(skill) > 100:
                    warnings.append(f"Skill name unusually long: {skill[:50]}...")
    
    is_valid = len(errors) == 0
    
    if errors:
        logger.warning(f"Job validation failed for {job.id}: {errors}")
    if warnings:
        logger.debug(f"Job validation warnings for {job.id}: {warnings}")
    
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


def validate_raw_job(job: RawJobPosting) -> ValidationResult:
    errors = []
    warnings = []
    
    if not job.title or not job.title.strip():
        errors.append("Job title is required")
    elif len(job.title.strip()) < 3:
        errors.append("Job title must be at least 3 characters")
    
    if not job.company or not job.company.strip():
        errors.append("Company name is required")
    elif job.company.strip().lower() in ["unknown", "n/a", "na", "-", "none"]:
        warnings.append("Company name appears to be a placeholder")
    
    if not job.source or not job.source.strip():
        errors.append("Job source is required")
    
    if not job.description or len(job.description.strip()) < 10:
        warnings.append("Job description is missing or very short")
    
    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


class JobAggregator:

    def __init__(self):
        self._seen_hashes = set()
        self._hash_to_source = {}

    def load_linkedin_dataset(self, csv_path: str) -> List[RawJobPosting]:
        return self.load_kaggle_dataset(csv_path, source_name="linkedin")

    def load_kaggle_dataset(self, csv_path: str, source_name: str = "linkedin") -> List[RawJobPosting]:
        try:
            logger.info(f"Loading dataset from: {csv_path}")
            df = pd.read_csv(csv_path, low_memory=False, on_bad_lines='skip')
            
            logger.info(f"Dataset has {len(df):,} rows and columns: {list(df.columns)[:10]}...")
            
            jobs = []
            skipped = 0

            for idx, row in df.iterrows():
                try:
                    job = self._parse_row_to_job(row, source_name)
                    if job and job.title and len(job.title.strip()) >= 3:
                        jobs.append(job)
                    else:
                        skipped += 1
                except Exception as e:
                    skipped += 1
                    if skipped <= 5:
                        logger.debug(f"Skipped row {idx}: {e}")
                
                # Progress logging for large datasets
                if (idx + 1) % 10000 == 0:
                    logger.info(f"Processed {idx + 1:,} rows, {len(jobs):,} valid jobs...")

            logger.info(f"Loaded {len(jobs):,} jobs from {csv_path} (skipped {skipped:,} invalid rows)")
            return jobs
            
        except Exception as e:
            logger.error(f"Failed to load dataset from {csv_path}: {e}")
            return []
    
    def _parse_row_to_job(self, row: pd.Series, source: str) -> Optional[RawJobPosting]:
        def get_val(*names, default=""):
            for name in names:
                if name in row.index:
                    val = row[name]
                    if pd.notna(val):
                        return str(val).strip()
                for col in row.index:
                    if col.lower() == name.lower():
                        val = row[col]
                        if pd.notna(val):
                            return str(val).strip()
            return default
        
        job_id = get_val("job_id", "id", "Uniq Id", "index", "job_link")
        if not job_id:
            job_id = str(hash(str(row.values)))
        
        title = get_val(
            "title", "job_title", "Job Title", "position", 
            "job_name", "role", "Position"
        )
        
        company = get_val(
            "company_name", "company", "Company Name", "Company",
            "employer", "organization"
        )
        if not company or company.lower() in ["nan", "none", ""]:
            company = "Unknown"
        
        description = get_val(
            "description", "job_description", "Job Description",
            "job_summary", "summary", "details"
        )
        
        location = get_val(
            "location", "job_location", "Location", "city",
            "formatted_location", "work_location"
        )
        
        url = get_val(
            "application_url", "url", "job_url", "job_link",
            "apply_url", "Job URL", "link"
        )
        
        return RawJobPosting(
            source=source,
            external_id=job_id,
            title=title,
            company=company,
            description=description,
            location=location if location and location.lower() != "nan" else None,
            url=url if url and url.lower() != "nan" else None,
        )

    def normalize_job(self, raw_posting: RawJobPosting, validate: bool = True) -> Optional[StructuredJob]:
        import uuid
        from datetime import datetime

        if validate:
            raw_validation = validate_raw_job(raw_posting)
            if not raw_validation.is_valid:
                return None

        job_id = f"{raw_posting.source}_{raw_posting.external_id}"
        if not raw_posting.external_id:
            job_id = f"{raw_posting.source}_{uuid.uuid4().hex[:8]}"

        structured_job = StructuredJob(
            id=job_id,
            source=raw_posting.source,
            external_id=raw_posting.external_id,
            title=raw_posting.title.strip() if raw_posting.title else "",
            company=raw_posting.company.strip() if raw_posting.company else "Unknown",
            description=raw_posting.description.strip() if raw_posting.description else "",
            requirements=ExtractedRequirements(),
            posted_date=raw_posting.posted_date,
            url=raw_posting.url,
            created_at=datetime.utcnow(),
        )
        
        if validate:
            validation = validate_job(structured_job)
            if not validation.is_valid:
                return None
        
        return structured_job

    def normalize_all(self, raw_jobs: List[RawJobPosting], validate: bool = True) -> List[StructuredJob]:
        structured_jobs = []
        invalid_count = 0
        
        for raw_job in raw_jobs:
            structured = self.normalize_job(raw_job, validate=validate)
            if structured:
                structured_jobs.append(structured)
            else:
                invalid_count += 1
        
        if invalid_count > 0:
            logger.info(f"Normalized {len(structured_jobs):,} jobs, skipped {invalid_count:,} invalid")
        
        return structured_jobs

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        normalized = text.lower().strip()
        normalized = " ".join(normalized.split())
        for suffix in [" inc", " inc.", " llc", " ltd", " corp", " corporation", " co", " co."]:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
        return normalized

    def _compute_job_hash(self, job: RawJobPosting) -> str:
        title_norm = self._normalize_text(job.title)
        company_norm = self._normalize_text(job.company)
        location_norm = self._normalize_text(job.location or "")
        key = f"{title_norm}|{company_norm}|{location_norm}"
        return hashlib.md5(key.encode()).hexdigest()

    def deduplicate(self, jobs: List[RawJobPosting], cross_source: bool = True) -> List[RawJobPosting]:
        seen = {}
        duplicates = 0

        for job in jobs:
            job_hash = self._compute_job_hash(job)

            if job_hash in seen:
                duplicates += 1
                existing = seen[job_hash]
                if len(job.description or "") > len(existing.description or ""):
                    seen[job_hash] = job
            elif cross_source and job_hash in self._seen_hashes:
                duplicates += 1
            else:
                seen[job_hash] = job
                if cross_source:
                    self._seen_hashes.add(job_hash)

        deduped = list(seen.values())
        logger.info(f"Deduplicated {len(jobs):,} -> {len(deduped):,} jobs (removed {duplicates:,} duplicates)")
        return deduped
    
    def reset_deduplication_state(self) -> None:
        self._seen_hashes.clear()
        self._hash_to_source.clear()

    # Tech job filtering keywords (Requirement 1.2)
    TECH_KEYWORDS = {
        # Software Engineering
        "software engineer", "software developer", "backend", "frontend", "full stack",
        "fullstack", "full-stack", "web developer", "mobile developer", "ios developer",
        "android developer", "application developer", "systems engineer", "embedded",
        
        # Data Roles
        "data engineer", "data scientist", "data analyst", "machine learning", "ml engineer",
        "ai engineer", "deep learning", "nlp", "computer vision", "analytics engineer",
        "business intelligence", "bi developer", "etl", "data architect",
        
        # DevOps/Cloud/Infrastructure
        "devops", "sre", "site reliability", "cloud engineer", "platform engineer",
        "infrastructure", "kubernetes", "docker", "aws", "azure", "gcp", "terraform",
        "devsecops", "systems administrator", "linux", "unix",
        
        # Security
        "security engineer", "cybersecurity", "infosec", "penetration", "appsec",
        
        # QA/Testing
        "qa engineer", "quality assurance", "test engineer", "sdet", "automation engineer",
        
        # Architecture/Leadership
        "solutions architect", "technical architect", "engineering manager", "tech lead",
        "principal engineer", "staff engineer", "cto", "vp engineering",
        
        # Specialized
        "blockchain", "smart contract", "solidity", "web3", "game developer",
        "graphics programmer", "firmware", "robotics", "computer engineer",
    }
    
    TECH_EXCLUSIONS = {
        "nurse", "nursing", "medical", "healthcare", "physician", "therapist",
        "dental", "pharmacy", "clinical", "patient", "hospital",
        "teacher", "professor", "instructor", "tutor", "education",
        "sales representative", "account executive", "business development",
        "marketing manager", "social media", "content writer",
        "accountant", "financial analyst", "bookkeeper", "auditor",
        "lawyer", "attorney", "paralegal", "legal assistant",
        "hr manager", "recruiter", "talent acquisition",
        "warehouse", "forklift", "driver", "delivery", "logistics",
        "chef", "cook", "restaurant", "hospitality", "hotel",
        "construction", "electrician", "plumber", "hvac", "mechanic",
    }

    def is_tech_job(self, title: str) -> bool:
        if not title:
            return False
        
        title_lower = title.lower()
        
        # First check exclusions
        for exclusion in self.TECH_EXCLUSIONS:
            if exclusion in title_lower:
                return False
        
        # Then check for tech keywords
        for keyword in self.TECH_KEYWORDS:
            if keyword in title_lower:
                return True
        
        return False

    def filter_tech_jobs(self, jobs: List[RawJobPosting]) -> List[RawJobPosting]:
        tech_jobs = [job for job in jobs if self.is_tech_job(job.title)]
        logger.info(f"Filtered {len(jobs):,} -> {len(tech_jobs):,} tech jobs")
        return tech_jobs
