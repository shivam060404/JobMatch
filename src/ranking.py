from typing import Dict, List, Optional, Set

from src.models import (
    CandidateProfile,
    RankedJob,
    ScoreBreakdown,
    StructuredJob,
    WeightConfig,
)


class RankingEngine:

    # Preset weight profiles for different job search strategies
    PRESETS: Dict[str, Dict[str, float]] = {
        "skill_focused": {
            "skill": 0.50,
            "experience": 0.20,
            "seniority": 0.15,
            "location": 0.10,
            "salary": 0.05,
        },
        "career_growth": {
            "skill": 0.30,
            "experience": 0.35,
            "seniority": 0.20,
            "location": 0.10,
            "salary": 0.05,
        },
        "compensation_first": {
            "skill": 0.25,
            "experience": 0.20,
            "seniority": 0.10,
            "location": 0.10,
            "salary": 0.35,
        },
        "remote_priority": {
            "skill": 0.30,
            "experience": 0.20,
            "seniority": 0.10,
            "location": 0.30,
            "salary": 0.10,
        },
        "balanced": {
            "skill": 0.30,
            "experience": 0.25,
            "seniority": 0.15,
            "location": 0.15,
            "salary": 0.15,
        },
    }

    # Seniority level ordering for distance calculation
    SENIORITY_ORDER: List[str] = ["entry", "mid", "senior", "lead", "executive"]

    # Comprehensive skill synonym mapping for tech roles
    SKILL_SYNONYMS: Dict[str, Set[str]] = {
        # Programming Languages
        "python": {"python", "py", "python3", "python2"},
        "javascript": {"javascript", "js", "ecmascript", "es6", "es2015"},
        "typescript": {"typescript", "ts"},
        "java": {"java", "jvm", "j2ee", "jdk", "openjdk", "core java"},
        "c#": {"c#", "csharp", "c sharp", ".net", "dotnet", ".net core", "asp.net"},
        "go": {"go", "golang"},
        "rust": {"rust", "rustlang"},
        "c++": {"c++", "cpp", "c plus plus"},
        "c": {"c", "c language", "ansi c"},
        "ruby": {"ruby", "rails", "ruby on rails", "ror"},
        "php": {"php", "laravel", "symfony"},
        "scala": {"scala"},
        "kotlin": {"kotlin", "android kotlin"},
        "swift": {"swift", "ios swift", "swiftui"},
        "r": {"r", "r language", "rstudio", "r programming"},
        "matlab": {"matlab"},
        "perl": {"perl"},
        "shell": {"shell", "bash", "sh", "zsh", "shell scripting", "bash scripting"},
        
        # AI/ML Core
        "machine learning": {"machine learning", "ml", "ai/ml", "deep learning", "dl", "neural networks", "nn"},
        "artificial intelligence": {"artificial intelligence", "ai", "ai/ml"},
        "natural language processing": {"natural language processing", "nlp", "text processing", "text mining", "text analytics", "language models"},
        "computer vision": {"computer vision", "cv", "image recognition", "object detection", "image processing"},
        "data science": {"data science", "data scientist", "ds", "data analytics", "analytics"},
        
        # LLM & Generative AI
        "llm": {"llm", "large language model", "large language models", "llms", "generative ai", "genai"},
        "llama": {"llama", "llama2", "llama-2", "llama3", "llama-3", "meta llama"},
        "gpt": {"gpt", "gpt-4", "gpt-3", "chatgpt", "openai", "gpt-4o"},
        "claude": {"claude", "claude-3", "anthropic"},
        "gemini": {"gemini", "google gemini", "bard"},
        "prompt engineering": {"prompt engineering", "prompting", "prompt design"},
        "rag": {"rag", "retrieval augmented generation", "retrieval-augmented"},
        "fine-tuning": {"fine-tuning", "fine tuning", "finetuning", "model tuning"},
        
        # AI Agents & Frameworks
        "ai agents": {"ai agents", "agentic", "agent systems", "autonomous agents"},
        "langchain": {"langchain", "lanchain", "lang chain"},
        "llamaindex": {"llamaindex", "llama index", "llama-index"},
        "crewai": {"crewai", "crew ai", "crew"},
        "autogen": {"autogen", "auto gen", "microsoft autogen"},
        
        # Vector Databases & Embeddings
        "vector database": {"vector db", "vectordb", "vector database", "vector store"},
        "qdrant": {"qdrant"},
        "pinecone": {"pinecone"},
        "weaviate": {"weaviate"},
        "chroma": {"chroma", "chromadb"},
        "milvus": {"milvus"},
        "embeddings": {"embeddings", "vector embeddings", "sentence embeddings", "word embeddings"},
        
        # Frontend Frameworks
        "react": {"react", "reactjs", "react.js", "react native"},
        "angular": {"angular", "angularjs", "angular.js"},
        "vue": {"vue", "vuejs", "vue.js", "nuxt", "nuxtjs"},
        "nextjs": {"nextjs", "next.js", "next"},
        "svelte": {"svelte", "sveltekit"},
        "html": {"html", "html5", "html/css"},
        "css": {"css", "css3", "sass", "scss", "less", "tailwind", "tailwindcss", "bootstrap"},
        
        # Backend & Runtime
        "node": {"node", "nodejs", "node.js"},
        "fastapi": {"fastapi", "fast api"},
        "django": {"django", "django rest framework", "drf"},
        "flask": {"flask"},
        "express": {"express", "expressjs", "express.js"},
        "spring": {"spring", "spring boot", "springboot", "spring framework"},
        
        # Databases - SQL Family (grouped together)
        "sql": {"sql", "mysql", "postgresql", "postgres", "sqlite", "t-sql", "mssql", "sql server", "oracle", "oracle db", "mariadb", "rdbms", "relational database"},
        "postgresql": {"postgresql", "postgres", "psql", "pg"},
        "mysql": {"mysql", "mariadb"},
        "oracle": {"oracle", "oracle db", "oracle database", "plsql", "pl/sql"},
        "sql server": {"sql server", "mssql", "microsoft sql server", "t-sql"},
        
        # Databases - NoSQL Family
        "nosql": {"nosql", "mongodb", "mongo", "dynamodb", "cassandra", "couchdb", "document database"},
        "mongodb": {"mongodb", "mongo", "mongoose"},
        "redis": {"redis", "elasticache"},
        "elasticsearch": {"elasticsearch", "elastic", "elk", "opensearch"},
        "cassandra": {"cassandra", "apache cassandra"},
        "dynamodb": {"dynamodb", "dynamo", "aws dynamodb"},
        
        # Cloud Platforms
        "aws": {"aws", "amazon web services", "amazon aws", "ec2", "s3", "lambda", "aws lambda"},
        "gcp": {"gcp", "google cloud", "google cloud platform", "bigquery"},
        "azure": {"azure", "microsoft azure", "azure cloud"},
        "cloud": {"cloud", "cloud computing", "cloud services", "cloud infrastructure"},
        
        # DevOps & Infrastructure
        "docker": {"docker", "containerization", "containers", "dockerfile"},
        "kubernetes": {"kubernetes", "k8s", "k8", "eks", "aks", "gke"},
        "ci/cd": {"ci/cd", "cicd", "continuous integration", "continuous deployment", "jenkins", "github actions", "gitlab ci", "circleci", "travis"},
        "terraform": {"terraform", "iac", "infrastructure as code", "terragrunt"},
        "ansible": {"ansible", "ansible playbook"},
        "helm": {"helm", "helm charts"},
        "linux": {"linux", "unix", "ubuntu", "centos", "redhat", "rhel", "debian"},
        
        # APIs
        "rest": {"rest", "restful", "rest api", "restful api", "api", "apis", "web api"},
        "graphql": {"graphql", "gql", "apollo"},
        "grpc": {"grpc", "protobuf", "protocol buffers"},
        
        # Data Engineering & Processing
        "data engineering": {"data engineering", "data engineer", "de", "etl", "data pipeline", "data pipelines"},
        "spark": {"spark", "apache spark", "pyspark", "spark sql"},
        "kafka": {"kafka", "apache kafka", "kafka streams"},
        "airflow": {"airflow", "apache airflow", "dag"},
        "hadoop": {"hadoop", "hdfs", "mapreduce", "hive"},
        "databricks": {"databricks"},
        "snowflake": {"snowflake"},
        "dbt": {"dbt", "data build tool"},
        
        # Data Analysis
        "pandas": {"pandas", "dataframe"},
        "numpy": {"numpy", "np"},
        "scipy": {"scipy"},
        "matplotlib": {"matplotlib", "pyplot"},
        "tableau": {"tableau"},
        "power bi": {"power bi", "powerbi"},
        "excel": {"excel", "microsoft excel", "spreadsheet"},
        
        # ML Frameworks
        "tensorflow": {"tensorflow", "tf", "tf2"},
        "pytorch": {"pytorch", "torch"},
        "scikit-learn": {"scikit-learn", "sklearn", "scikit learn"},
        "keras": {"keras"},
        "huggingface": {"huggingface", "hugging face", "transformers", "hf"},
        "xgboost": {"xgboost", "xgb"},
        "lightgbm": {"lightgbm", "lgbm"},
        
        # MLOps & DevOps
        "mlops": {"mlops", "ml ops", "machine learning operations"},
        "devops": {"devops", "dev ops", "sre", "site reliability"},
        "monitoring": {"monitoring", "observability", "prometheus", "grafana", "datadog", "new relic"},
        
        # Testing
        "testing": {"testing", "unit testing", "test automation", "qa", "quality assurance"},
        "selenium": {"selenium", "webdriver"},
        "pytest": {"pytest", "py.test"},
        "jest": {"jest"},
        "cypress": {"cypress"},
        
        # Security
        "security": {"security", "cybersecurity", "infosec", "information security"},
        "oauth": {"oauth", "oauth2", "authentication", "authorization"},
        
        # Methodologies
        "agile": {"agile", "scrum", "kanban", "sprint"},
        "git": {"git", "github", "gitlab", "bitbucket", "version control", "vcs"},
        
        # Mobile
        "android": {"android", "android development", "android sdk"},
        "ios": {"ios", "ios development", "xcode"},
        "mobile": {"mobile", "mobile development", "mobile app"},
        "flutter": {"flutter", "dart"},
        "react native": {"react native", "rn"},
        
        # Big Data
        "big data": {"big data", "large scale data", "distributed systems"},
    }


    def __init__(
        self, weights: Optional[Dict[str, float]] = None, preset: str = "balanced"
    ):
        if weights is not None:
            self.weights = self.normalize_weights(weights)
        else:
            self.weights = self.PRESETS.get(preset, self.PRESETS["balanced"]).copy()

    def normalize_skill(self, skill: str) -> str:
        normalized = skill.lower().strip()
        for canonical, synonyms in self.SKILL_SYNONYMS.items():
            if normalized in synonyms:
                return canonical
        return normalized

    def score_skill_overlap(
        self, candidate_skills: Set[str], job_skills: Set[str]
    ) -> float:
        if not candidate_skills and not job_skills:
            return 1.0  # No skills required, perfect match
        if not candidate_skills or not job_skills:
            return 0.0  # One side empty, no match

        # Normalize skills using synonym mapping
        candidate_normalized = {self.normalize_skill(s) for s in candidate_skills}
        job_normalized = {self.normalize_skill(s) for s in job_skills}

        intersection = candidate_normalized & job_normalized
        union = candidate_normalized | job_normalized

        return len(intersection) / len(union) if union else 0.0

    def score_experience(
        self,
        candidate_years: int,
        job_min: Optional[int],
        job_max: Optional[int],
    ) -> float:
        if job_min is None and job_max is None:
            return 1.0  # No requirement specified

        job_min = job_min or 0
        job_max = job_max or job_min + 10  # Default range if only min specified

        if job_min <= candidate_years <= job_max:
            return 1.0

        # Calculate distance from acceptable range
        if candidate_years < job_min:
            distance = job_min - candidate_years
        else:
            distance = candidate_years - job_max

        # Decay: lose 0.15 per year outside range
        score = 1.0 - (distance * 0.15)
        return max(0.0, score)

    def score_seniority(
        self, candidate_level: Optional[str], job_level: Optional[str]
    ) -> float:
        if job_level is None:
            return 1.0  # No requirement specified

        if candidate_level is None:
            return 0.5  # Unknown candidate level, neutral score

        try:
            candidate_idx = self.SENIORITY_ORDER.index(candidate_level.lower())
            job_idx = self.SENIORITY_ORDER.index(job_level.lower())
        except ValueError:
            return 0.5  # Unknown level, neutral score

        distance = abs(candidate_idx - job_idx)

        if distance == 0:
            return 1.0
        elif distance == 1:
            return 0.7
        elif distance == 2:
            return 0.4
        else:
            return 0.1

    def score_location(
        self,
        candidate_pref: Optional[str],
        job_location: Optional[str],
        job_remote: bool,
    ) -> float:
        candidate_wants_remote = candidate_pref and "remote" in candidate_pref.lower()

        # Remote preference handling
        if candidate_wants_remote and job_remote:
            return 1.0

        if job_remote:
            return 0.8  # Remote is always somewhat acceptable

        # Location string matching
        if candidate_pref and job_location:
            candidate_lower = candidate_pref.lower()
            job_lower = job_location.lower()

            # Check for city/state match
            if candidate_lower in job_lower or job_lower in candidate_lower:
                return 1.0

            # Check for country match
            country_keywords = [
                "usa",
                "united states",
                "uk",
                "canada",
                "germany",
                "france",
                "australia",
            ]
            if any(
                loc in candidate_lower and loc in job_lower for loc in country_keywords
            ):
                return 0.7

        # No location specified by job
        if not job_location:
            return 0.6

        return 0.2  # Location mismatch


    def score_salary(
        self,
        candidate_expected: Optional[int],
        job_min: Optional[int],
        job_max: Optional[int],
    ) -> float:
        if candidate_expected is None:
            return 0.8  # No expectation, slightly positive

        if job_min is None and job_max is None:
            return 0.5  # No salary info, neutral

        job_min = job_min or 0
        job_max = job_max or int(job_min * 1.3)  # Estimate max if only min given

        if job_min <= candidate_expected <= job_max:
            return 1.0

        # Job pays more than expected - good!
        if candidate_expected < job_min:
            return 1.0  # Job pays more, always good

        # Job pays less than expected
        if candidate_expected > job_max:
            # Calculate percentage shortfall
            shortfall = (candidate_expected - job_max) / candidate_expected
            score = 1.0 - (shortfall * 2)  # Lose 2x the percentage
            return max(0.0, score)

        return 0.5

    def compute_composite(self, scores: Dict[str, float]) -> float:
        composite = (
            scores["skill"] * self.weights["skill"]
            + scores["experience"] * self.weights["experience"]
            + scores["seniority"] * self.weights["seniority"]
            + scores["location"] * self.weights["location"]
            + scores["salary"] * self.weights["salary"]
        )
        return min(1.0, max(0.0, composite))  # Clamp to [0, 1]

    def normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        total = sum(weights.values())
        if total == 0:
            return self.PRESETS["balanced"].copy()
        return {k: v / total for k, v in weights.items()}

    def rank(
        self, candidate: CandidateProfile, jobs: List[StructuredJob]
    ) -> List[RankedJob]:
        ranked = []

        for job in jobs:
            req = job.requirements

            scores = {
                "skill": self.score_skill_overlap(
                    set(candidate.skills), set(req.skills)
                ),
                "experience": self.score_experience(
                    candidate.experience_years,
                    req.experience_min,
                    req.experience_max,
                ),
                "seniority": self.score_seniority(
                    candidate.seniority.value if candidate.seniority else None,
                    req.seniority.value if req.seniority else None,
                ),
                "location": self.score_location(
                    candidate.location_preference,
                    req.location,
                    req.remote,
                ),
                "salary": self.score_salary(
                    candidate.salary_expected,
                    req.salary_min,
                    req.salary_max,
                ),
            }

            composite = self.compute_composite(scores)

            ranked.append(
                RankedJob(
                    job=job,
                    scores=ScoreBreakdown(
                        skill_score=scores["skill"],
                        experience_score=scores["experience"],
                        seniority_score=scores["seniority"],
                        location_score=scores["location"],
                        salary_score=scores["salary"],
                        composite_score=composite,
                    ),
                )
            )

        # Sort by composite score descending
        ranked.sort(key=lambda x: x.scores.composite_score, reverse=True)
        return ranked

    def set_weights(self, weights: Dict[str, float]) -> None:
        self.weights = self.normalize_weights(weights)

    def set_preset(self, preset: str) -> None:
        if preset not in self.PRESETS:
            raise ValueError(
                f"Unknown preset: {preset}. Available: {list(self.PRESETS.keys())}"
            )
        self.weights = self.PRESETS[preset].copy()

    def get_weights(self) -> Dict[str, float]:
        return self.weights.copy()
