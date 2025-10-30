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
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
GITHUB_PRIVATE_KEY = os.getenv("GITHUB_PRIVATE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Validate critical environment variables at startup
def validate_config():
    """Validate that required environment variables are set."""
    required_vars = {
        "GITHUB_WEBHOOK_SECRET": "Webhook secret for GitHub signature verification",
        "GITHUB_APP_ID": "GitHub App ID for authentication",
        "GITHUB_PRIVATE_KEY": "GitHub App private key path or content",
        "GEMINI_API_KEY": "Google Gemini API key"
    }

    missing_vars = []
    for var_name, description in required_vars.items():
        if not os.getenv(var_name):
            missing_vars.append(f"  - {var_name}: {description}")

    if missing_vars:
        raise ValueError(
            "Missing required environment variables:\n" + "\n".join(missing_vars) +
            "\n\nPlease set these variables in your .env file. See .env.example for reference."
        )

# Call validation
validate_config()


# ensure directories
INDEX_DIR.mkdir(parents=True, exist_ok=True)
REPO_CACHE_DIR.mkdir(parents=True, exist_ok=True)