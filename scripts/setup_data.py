import os
import urllib.request
from pathlib import Path

DATA_DIR = Path("data")
DB_FILE = DATA_DIR / "jobs.db"
EMBEDDINGS_FILE = DATA_DIR / "embeddings.npz"

# Replace these with your actual Google Drive/Dropbox direct download links
# For Google Drive: use format https://drive.google.com/uc?export=download&id=FILE_ID
DB_URL = os.environ.get("DB_DOWNLOAD_URL", "")
EMBEDDINGS_URL = os.environ.get("EMBEDDINGS_DOWNLOAD_URL", "")

def download_file(url: str, dest: Path) -> bool:
    if not url:
        print(f"No URL provided for {dest.name}")
        return False
    
    try:
        print(f"Downloading {dest.name}...")
        urllib.request.urlretrieve(url, dest)
        print(f"Downloaded {dest.name} ({dest.stat().st_size / 1024 / 1024:.1f} MB)")
        return True
    except Exception as e:
        print(f"Failed to download {dest.name}: {e}")
        return False

def setup_data():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if not DB_FILE.exists():
        print("Database not found, downloading...")
        download_file(DB_URL, DB_FILE)
    else:
        print(f"Database exists: {DB_FILE}")
    
    if not EMBEDDINGS_FILE.exists():
        print("Embeddings not found, downloading...")
        download_file(EMBEDDINGS_URL, EMBEDDINGS_FILE)
    else:
        print(f"Embeddings exist: {EMBEDDINGS_FILE}")

if __name__ == "__main__":
    setup_data()
