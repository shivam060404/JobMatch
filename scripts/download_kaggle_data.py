import argparse
import logging
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# LinkedIn Job Postings dataset
LINKEDIN_DATASET = {
    "name": "arshkon/linkedin-job-postings",
    "description": "LinkedIn Job Postings 2023-2024 (~124K jobs)",
    "main_file": "postings.csv",
}


def check_kaggle_credentials() -> bool:
    if sys.platform == "win32":
        win_kaggle = Path(os.environ.get("USERPROFILE", "")) / ".kaggle" / "kaggle.json"
        if win_kaggle.exists():
            return True
    
    # Check Linux/Mac location
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if kaggle_json.exists():
        return True
    
    # Check environment variables
    if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
        return True
    
    return False


def download_linkedin_dataset(output_dir: str = "data/kaggle/linkedin") -> Path:
    logger.info(f"Downloading {LINKEDIN_DATASET['description']}...")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        
        api = KaggleApi()
        api.authenticate()
        
        # Download and extract
        api.dataset_download_files(
            LINKEDIN_DATASET["name"],
            path=str(output_path),
            unzip=True
        )
        
        logger.info(f"Downloaded to: {output_path}")
        
        # Find the main CSV file
        csv_files = list(output_path.glob("**/*.csv"))
        logger.info(f"Found {len(csv_files)} CSV files:")
        
        for f in csv_files:
            size_mb = f.stat().st_size / (1024 * 1024)
            logger.info(f"  - {f.name} ({size_mb:.1f} MB)")
        
        # Return path to main file
        main_file = output_path / LINKEDIN_DATASET["main_file"]
        if main_file.exists():
            return main_file
        
        # Search for it
        matches = list(output_path.glob(f"**/{LINKEDIN_DATASET['main_file']}"))
        if matches:
            return matches[0]
        
        # Return largest CSV as fallback
        if csv_files:
            return max(csv_files, key=lambda f: f.stat().st_size)
        
        raise FileNotFoundError("No CSV files found in downloaded dataset")
        
    except ImportError:
        logger.error("Kaggle package not installed!")
        logger.error("Run: pip install kaggle")
        sys.exit(1)


def print_setup_instructions():
    print("""
╔══════════════════════════════════════════════════════════════╗
║           KAGGLE API SETUP INSTRUCTIONS                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Step 1: Create Kaggle Account                               ║
║  → Go to https://www.kaggle.com and sign up                  ║
║                                                              ║
║  Step 2: Get API Token                                       ║
║  → Click your profile icon (top right)                       ║
║  → Click "Settings"                                          ║
║  → Scroll to "API" section                                   ║
║  → Click "Create New Token"                                  ║
║  → This downloads kaggle.json                                ║
║                                                              ║
║  Step 3: Place the Token                                     ║
║  Windows:                                                    ║
║    mkdir %USERPROFILE%\\.kaggle                              ║
║    move Downloads\\kaggle.json %USERPROFILE%\\.kaggle\\      ║
║                                                              ║
║  Linux/Mac:                                                  ║
║    mkdir ~/.kaggle                                           ║
║    mv ~/Downloads/kaggle.json ~/.kaggle/                     ║
║    chmod 600 ~/.kaggle/kaggle.json                           ║
║                                                              ║
║  Step 4: Install Kaggle Package                              ║
║    pip install kaggle                                        ║
║                                                              ║
║  Step 5: Verify Setup                                        ║
║    python -m scripts.download_kaggle_data --check            ║
║                                                              ║
║  Step 6: Download Dataset                                    ║
║    python -m scripts.download_kaggle_data --dataset linkedin ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


def main():
    parser = argparse.ArgumentParser(
        description="Download LinkedIn Job Postings dataset from Kaggle"
    )
    
    parser.add_argument(
        "--dataset",
        choices=["linkedin"],
        help="Dataset to download (currently only 'linkedin' supported)"
    )
    parser.add_argument(
        "--output-dir",
        default="data/kaggle/linkedin",
        help="Output directory for downloaded data"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if Kaggle credentials are configured"
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Show setup instructions"
    )
    
    args = parser.parse_args()
    
    if args.setup:
        print_setup_instructions()
        return
    
    if args.check:
        if check_kaggle_credentials():
            print("✓ Kaggle credentials found!")
            print("\nYou can now download the dataset:")
            print("  python -m scripts.download_kaggle_data --dataset linkedin")
        else:
            print("✗ Kaggle credentials not found!")
            print_setup_instructions()
        return
    
    if not args.dataset:
        parser.error("Specify --dataset linkedin, or use --check/--setup")
    
    # Check credentials
    if not check_kaggle_credentials():
        print("✗ Kaggle credentials not configured!")
        print_setup_instructions()
        sys.exit(1)
    
    # Download dataset
    csv_path = download_linkedin_dataset(args.output_dir)
    
    print("\n" + "=" * 60)
    print("Download Complete!")
    print("=" * 60)
    print(f"Main file: {csv_path}")
    print("\nTo ingest the data into the database, run:")
    print(f"  python -m scripts.ingest_data --kaggle {csv_path} --limit 50000")


if __name__ == "__main__":
    main()
