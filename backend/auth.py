import time, jwt, os, requests
from fastapi import HTTPException
from backend.config import GITHUB_APP_ID, GITHUB_PRIVATE_KEY

APP_ID, PRIVATE_KEY = GITHUB_APP_ID, GITHUB_PRIVATE_KEY
def build_app_jwt():
    now = int(time.time())
    payload = {"iat": now, "exp": now + 9 * 60, "iss": APP_ID}
    private_key_str = PRIVATE_KEY
    if PRIVATE_KEY and not PRIVATE_KEY.strip().startswith("-----BEGIN"):
        with open(PRIVATE_KEY.strip(), "r") as f:
            private_key_str = f.read()
    return jwt.encode(payload, private_key_str.encode("utf-8"), algorithm="RS256")

def get_installation_token(installation_id: str) -> str:
    app_jwt = build_app_jwt()
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
    }
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    return response.json()["token"]


# API Key Validation for Frontend Access
VALID_API_KEYS = {
    os.getenv("FRONTEND_API_KEY", "default-dev-key-change-in-production"): "frontend_user"
}


def validate_api_key(authorization_header: str) -> str:
    """
    Validate API key from Authorization header.
    Expected format: 'Bearer <api_key>'

    Args:
        authorization_header: Authorization header value

    Returns:
        The API key if valid

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not authorization_header:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected: Bearer <api_key>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_key = parts[1]

    if api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )

    return api_key
