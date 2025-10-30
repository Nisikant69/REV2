import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
INDEX_DIR = DATA_DIR / "indexes"
REPO_CACHE_DIR = DATA_DIR / "repo_cache"


# limits
MAX_DIFF_SIZE = int(os.getenv("MAX_DIFF_SIZE", 15000))
MAX_FILE_CHARS = int(os.getenv("MAX_FILE_SIZE", 8000))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 800))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))
TOP_K = int(os.getenv("TOP_K", 5))


# GitHub/Gemini env
#GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
GITHUB_WEBHOOK_SECRET ="V5NoEwgFZRxOhiZ"
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
GITHUB_PRIVATE_KEY = os.getenv("GITHUB_PRIVATE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# ensure directories
INDEX_DIR.mkdir(parents=True, exist_ok=True)
REPO_CACHE_DIR.mkdir(parents=True, exist_ok=True)