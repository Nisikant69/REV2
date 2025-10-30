# main.py
from fastapi import FastAPI, Request, HTTPException
import hmac, hashlib, os, json, traceback, uuid
from github import Github, GithubException
import requests

from backend.reviewer import review_patch
from backend.auth import get_installation_token
from backend.repo_fetcher import save_repo_snapshot
from backend.context_indexer import index_repo
from backend.config import GITHUB_WEBHOOK_SECRET as WEBHOOK_SECRET, MAX_DIFF_SIZE
from backend.logger import get_logger
from backend.validators import (
    validate_webhook_payload,
    validate_patch,
    sanitize_patch_for_llm,
    ValidationError,
)
from backend.rate_limiter import get_rate_limiter
from backend.database import init_db
from backend.health import router as health_router

app = FastAPI(title="REV2 - AI Code Reviewer")
logger = get_logger(__name__)
rate_limiter = get_rate_limiter()

# Include health check routes
app.include_router(health_router)


@app.on_event("startup")
async def startup_event():
    """Initialize database and system on startup."""
    try:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.critical(f"Failed to initialize database: {str(e)}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down REV2...")
    # Flush logs, close connections, etc.


@app.post("/api/webhook")
async def github_webhook(request: Request):
    """Handle GitHub webhook for pull request events."""
    # Generate request ID for tracing
    request_id = str(uuid.uuid4())
    logger.set_request_id(request_id)

    try:
        # --- Signature verification ---
        signature_header = request.headers.get("X-Hub-Signature-256")
        if not signature_header:
            logger.warning("Missing signature header")
            raise HTTPException(status_code=400, detail="Missing signature header")

        body = await request.body()
        hash_object = hmac.new(
            WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256
        )
        expected_signature = hash_object.hexdigest()
        provided_signature = signature_header.split("=")[1] if "=" in signature_header else ""

        if not hmac.compare_digest(provided_signature, expected_signature):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

        payload = await request.json()
        event = request.headers.get("X-GitHub-Event")
        logger.info("Webhook received", event_type=event)

        # Validate webhook payload
        try:
            validate_webhook_payload(payload)
        except ValidationError as e:
            logger.warning(f"Invalid webhook payload: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")

        if event == "pull_request":
            action = payload.get("action")
            if action in ["opened", "reopened", "synchronize"]:
                installation_id = payload["installation"]["id"]
                repo_name = payload["repository"]["full_name"]
                pr_number = payload["pull_request"]["number"]

                logger.info(
                    "Processing pull request",
                    repo=repo_name,
                    pr_number=pr_number,
                    action=action,
                    installation_id=installation_id,
                )

                # Check rate limit
                is_allowed, current_count = rate_limiter.check_limit(installation_id)
                if not is_allowed:
                    logger.warning(
                        "Rate limit exceeded",
                        installation_id=installation_id,
                        current_count=current_count,
                        limit=rate_limiter.max_reviews_per_hour,
                    )
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded: {current_count}/{rate_limiter.max_reviews_per_hour} reviews this hour",
                    )

                try:
                    access_token = get_installation_token(installation_id)
                    g = Github(login_or_token=access_token)

                    repo = g.get_repo(repo_name)
                    pr = repo.get_pull(pr_number)

                    head_sha = payload["pull_request"]["head"]["sha"]
                    ref = payload["pull_request"]["head"]["ref"]

                    logger.info(
                        "Building repository snapshot and index",
                        head_sha=head_sha,
                    )

                    # --- Snapshot + Index (done once) ---
                    repo_dir = save_repo_snapshot(repo, head_sha)
                    index, metadata = index_repo(repo_dir, repo_name, head_sha)

                    files = pr.get_files()
                    all_review_comments = []
                    action_flag = "COMMENT"
                    summary_blocks = []
                    files_reviewed = 0

                    for file in files:
                        if file.status == "removed" or not file.patch:
                            logger.debug(
                                "Skipping file",
                                filename=file.filename,
                                reason="removed or no patch",
                            )
                            continue

                        if len(file.patch) > MAX_DIFF_SIZE:
                            logger.warning(
                                "Patch exceeds size limit",
                                filename=file.filename,
                                patch_size=len(file.patch),
                                max_size=MAX_DIFF_SIZE,
                            )
                            continue

                        # Validate and sanitize patch
                        try:
                            validate_patch(file.patch)
                            sanitized_patch = sanitize_patch_for_llm(file.patch)
                        except ValidationError as e:
                            logger.warning(
                                f"Invalid patch for file {file.filename}: {str(e)}"
                            )
                            continue

                        logger.debug(
                            "Reviewing file", filename=file.filename
                        )

                        review_json = review_patch(
                            sanitized_patch,
                            file.filename,
                            repo_name,
                            ref,
                            head_sha,
                            index,
                            metadata,
                        )

                        if review_json and "review" in review_json:
                            files_reviewed += 1
                            summary_blocks.append(
                                f"### Review for `{review_json['file']}`\n\n{review_json['review']}"
                            )
                            all_review_comments.append(
                                {
                                    "path": file.filename,
                                    "body": review_json["review"],
                                    "position": 1,  # Fallback position
                                }
                            )

                    logger.info(
                        "Review complete",
                        files_reviewed=files_reviewed,
                        total_comments=len(all_review_comments),
                    )

                    if all_review_comments:
                        pr.create_review(
                            body="🤖 **AI Code Review**\n\n"
                            + "\n---\n".join(summary_blocks),
                            event=action_flag,
                            comments=all_review_comments,
                        )
                    else:
                        pr.create_review(
                            body="🤖 **AI Code Review**\n\nNo issues found!",
                            event="COMMENT",
                        )

                    logger.info("Review posted successfully")

                except (GithubException, requests.exceptions.RequestException) as e:
                    logger.error(
                        "GitHub/Network error during review",
                        error=str(e),
                        exc_info=True,
                    )
                    raise HTTPException(
                        status_code=502, detail=f"GitHub API error: {e}"
                    )
                except Exception as e:
                    logger.error(
                        "Internal error during review processing",
                        error=str(e),
                        exc_info=True,
                    )
                    raise HTTPException(status_code=500, detail=f"Internal error: {e}")

        logger.clear_request_id()
        return {"status": "success"}

    except HTTPException:
        logger.clear_request_id()
        raise
    except Exception as e:
        logger.error("Unhandled webhook error", error=str(e), exc_info=True)
        logger.clear_request_id()
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")