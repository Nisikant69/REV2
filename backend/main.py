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

app = FastAPI()

@app.post("/api/webhook")
async def github_webhook(request: Request):
    # --- Signature verification ---
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        raise HTTPException(status_code=400, detail="Missing signature header")
    body = await request.body()
    hash_object = hmac.new(WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256)
    if not hmac.compare_digest(signature_header.split("=")[1], hash_object.hexdigest()):
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = await request.json()
    event = request.headers.get("X-GitHub-Event")

    if event == "pull_request":
        action = payload.get("action")
        if action in ["opened", "reopened", "synchronize"]:
            try:
                installation_id = payload["installation"]["id"]
                access_token = get_installation_token(installation_id)
                g = Github(login_or_token=access_token)

                repo_name = payload["repository"]["full_name"]
                repo = g.get_repo(repo_name)
                pr_number = payload["pull_request"]["number"]
                pr = repo.get_pull(pr_number)

                head_sha = payload["pull_request"]["head"]["sha"]
                ref = payload["pull_request"]["head"]["ref"]

                # --- Snapshot + Index (done once) ---
                repo_dir = save_repo_snapshot(repo, head_sha)
                index, metadata = index_repo(repo_dir, repo_name, head_sha)

                files = pr.get_files()
                all_review_comments = []
                action_flag = "COMMENT"
                summary_blocks = []

                for file in files:
                    if file.status == "removed" or not file.patch:
                        continue
                    if len(file.patch) > MAX_DIFF_SIZE:
                        continue
                    
                    review_json = review_patch(
                        file.patch,
                        file.filename,
                        repo_name,
                        ref,
                        head_sha,
                        index,
                        metadata
                    )

                    if review_json and "review" in review_json:
                        summary_blocks.append(f"### Review for `{review_json['file']}`\n\n{review_json['review']}")
                        all_review_comments.append({
                            "path": file.filename,
                            "body": review_json['review'],
                            "position": 1, # Using position=1 as a fallback for the first line of the patch
                        })
                        # Add logic to determine a more precise line number if needed
                        # The current logic doesn't support line-specific comments, so this is a placeholder

                if all_review_comments:
                    pr.create_review(
                        body="🤖 **AI Code Review**\n\n" + "\n---\n".join(summary_blocks),
                        event=action_flag,
                        comments=all_review_comments,
                    )
                else:
                    pr.create_review(
                        body="🤖 **AI Code Review**\n\nNo issues found!",
                        event="COMMENT",
                    )

            except (GithubException, requests.exceptions.RequestException) as e:
                print("⚠️ GitHub/Network error:", repr(e))
                traceback.print_exc()
                raise HTTPException(status_code=502, detail=f"GitHub API error: {e}")
            except Exception as e:
                print("🔥 Internal error in webhook:", repr(e))
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Internal error: {e}")

    return {"status": "success"}