import sqlite3
import argparse
from pathlib import Path


# Tech job title keywords - based on domain expertise
TECH_KEYWORDS = [
    # Software Engineering
    'software', 'developer', 'programmer', 'coder',
    'full stack', 'fullstack', 'full-stack',
    'backend', 'back-end', 'back end',
    'frontend', 'front-end', 'front end',
    
    # Data roles
    'data engineer', 'data scientist', 'data analyst',
    'machine learning', 'ml engineer', 'ai engineer',
    'deep learning', 'nlp', 'computer vision',
    
    # DevOps/Cloud/Infrastructure
    'devops', 'dev ops', 'sre', 'site reliability',
    'cloud engineer', 'cloud architect',
    'platform engineer', 'infrastructure',
    'kubernetes', 'docker',
    
    # Specific technologies (strong signals)
    'python developer', 'java developer', 'javascript',
    'react', 'angular', 'vue',
    'node.js', 'nodejs',
    'aws', 'azure', 'gcp',
    '.net developer', 'dotnet',
    'golang', 'rust developer',
    
    # Mobile
    'ios developer', 'android developer', 'mobile developer',
    'flutter', 'react native',
    
    # Web
    'web developer', 'web engineer',
    
    # Security
    'security engineer', 'cybersecurity', 'appsec',
    
    # QA/Testing (tech-related)
    'qa engineer', 'sdet', 'test automation',
    'quality engineer',
]

# Exclude these even if they match (false positives)
EXCLUDE_KEYWORDS = [
    'sales engineer',  # Usually sales, not engineering
    'field engineer',  # Usually hardware/physical
    'support engineer',  # Usually customer support
    'building engineer',  # Construction
    'mechanical engineer',  # Not software
    'civil engineer',  # Not software
    'electrical engineer',  # Not software (unless embedded)
    'chemical engineer',  # Not software
    'process engineer',  # Usually manufacturing
    'manufacturing engineer',  # Not software
    'industrial engineer',  # Not software
    'structural engineer',  # Construction
    'environmental engineer',  # Not software
    'biomedical engineer',  # Not software
    'audio engineer',  # Not software
    'sound engineer',  # Not software
    'recording engineer',  # Not software
    'broadcast engineer',  # Not software
    'hvac',  # Not software
    'plumber',  # Not software
    'electrician',  # Not software
]


def is_tech_job(title: str) -> bool:
    title_lower = title.lower()
    
    # First check exclusions
    for exclude in EXCLUDE_KEYWORDS:
        if exclude in title_lower:
            return False
    
    # Then check inclusions
    for keyword in TECH_KEYWORDS:
        if keyword in title_lower:
            return True
    
    return False


def filter_tech_jobs(db_path: str, dry_run: bool = False) -> dict:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all jobs
    cursor.execute("SELECT id, title FROM jobs")
    all_jobs = cursor.fetchall()
    
    total = len(all_jobs)
    tech_jobs = []
    non_tech_jobs = []
    
    for job_id, title in all_jobs:
        if is_tech_job(title):
            tech_jobs.append((job_id, title))
        else:
            non_tech_jobs.append((job_id, title))
    
    stats = {
        'total': total,
        'tech': len(tech_jobs),
        'non_tech': len(non_tech_jobs),
        'percentage': 100 * len(tech_jobs) / total if total > 0 else 0
    }
    
    if not dry_run:
        # Delete non-tech jobs
        non_tech_ids = [job_id for job_id, _ in non_tech_jobs]
        
        if non_tech_ids:
            # Delete in batches to avoid SQL limits
            batch_size = 500
            for i in range(0, len(non_tech_ids), batch_size):
                batch = non_tech_ids[i:i + batch_size]
                placeholders = ','.join(['?' for _ in batch])
                cursor.execute(f"DELETE FROM jobs WHERE id IN ({placeholders})", batch)
            
            conn.commit()
            print(f"✅ Deleted {len(non_tech_ids)} non-tech jobs")
    
    conn.close()
    return stats, tech_jobs[:20], non_tech_jobs[:20]  # Return samples


def main():
    parser = argparse.ArgumentParser(description='Filter LinkedIn jobs to tech roles only')
    parser.add_argument('--db', default='data/jobs.db', help='Path to SQLite database')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be filtered without deleting')
    parser.add_argument('--show-samples', action='store_true', help='Show sample job titles')
    args = parser.parse_args()
    
    if not Path(args.db).exists():
        print(f"❌ Database not found: {args.db}")
        return
    
    print("=" * 60)
    print("TECH JOB FILTER")
    print("=" * 60)
    print(f"\nDatabase: {args.db}")
    print(f"Mode: {'DRY RUN (no changes)' if args.dry_run else 'LIVE (will delete non-tech jobs)'}")
    
    stats, tech_samples, non_tech_samples = filter_tech_jobs(args.db, dry_run=args.dry_run)
    
    print(f"\n📊 Results:")
    print(f"   Total jobs: {stats['total']:,}")
    print(f"   Tech jobs: {stats['tech']:,} ({stats['percentage']:.1f}%)")
    print(f"   Non-tech jobs: {stats['non_tech']:,}")
    
    if args.show_samples or args.dry_run:
        print(f"\n✅ Sample TECH jobs (keeping):")
        for job_id, title in tech_samples[:10]:
            print(f"   - {title}")
        
        print(f"\n❌ Sample NON-TECH jobs (removing):")
        for job_id, title in non_tech_samples[:10]:
            print(f"   - {title}")
    
    if args.dry_run:
        print(f"\n⚠️  DRY RUN - No changes made. Run without --dry-run to apply filter.")
    else:
        print(f"\n✅ Database filtered to {stats['tech']:,} tech jobs!")


if __name__ == '__main__':
    main()
