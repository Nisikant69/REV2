"""
Enhanced AI code review module for REV2.
Supports:
- Parallel processing of multiple files
- Batch API calls for cost optimization
- Severity levels (critical, warning, info)
- Structured review output
"""

import json
import time
import re
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from backend.utils import (
    trim_diff,
    extract_symbols_from_patch,
    detect_language_from_filename,
)
from backend.semantic_search import semantic_search
from backend.config import GEMINI_API_KEY, TOP_K
from backend.logger import get_logger
import faiss

logger = get_logger(__name__)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

SAFE_TOKEN_LIMIT = 5000
CHUNK_SIZE_LINES = 50
DEFAULT_PARALLEL_WORKERS = int(os.getenv("PARALLEL_REVIEW_WORKERS", 2))
DEFAULT_BATCH_SIZE = int(os.getenv("BATCH_SIZE", 5))


class Severity(Enum):
    """Review comment severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ReviewComment:
    """Structured review comment."""
    severity: Severity
    line_number: Optional[int]
    comment: str
    category: str  # e.g., "security", "performance", "maintainability"


@dataclass
class PatchReview:
    """Complete review for a patch."""
    file: str
    language: str
    symbols: List[str]
    comments: List[ReviewComment]
    summary: str
    context_used: List[Dict]
    processing_time_ms: float
    status: str  # "success" or "failure"


class ReviewGenerator:
    """Generates code reviews with advanced features."""

    def __init__(self, model_name: str = "gemini-2.5-pro"):
        """Initialize review generator."""
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name

    def _extract_severity_and_category(self, text: str) -> Tuple[Severity, str]:
        """Extract severity level and category from review text."""
        text_lower = text.lower()

        # Check for severity indicators
        if any(word in text_lower for word in ["critical", "vulnerability", "security", "crash", "data loss"]):
            severity = Severity.CRITICAL
        elif any(word in text_lower for word in ["warning", "issue", "bug", "performance"]):
            severity = Severity.WARNING
        else:
            severity = Severity.INFO

        # Check for category
        if any(word in text_lower for word in ["security", "vulnerability", "injection", "auth"]):
            category = "security"
        elif any(word in text_lower for word in ["performance", "slow", "optimize", "memory"]):
            category = "performance"
        elif any(word in text_lower for word in ["style", "format", "naming", "convention"]):
            category = "style"
        else:
            category = "maintainability"

        return severity, category

    def _parse_review_response(self, response_text: str) -> List[ReviewComment]:
        """Parse AI response into structured comments."""
        comments = []

        # Split response into comment blocks (separated by numbers or bullet points)
        blocks = re.split(r"\n\d+\.|•|-", response_text)

        for block in blocks:
            if not block.strip():
                continue

            severity, category = self._extract_severity_and_category(block)
            comments.append(
                ReviewComment(
                    severity=severity,
                    line_number=None,  # TODO: Extract line numbers from response
                    comment=block.strip()[:500],  # Limit to 500 chars
                    category=category,
                )
            )

        return comments

    def review_patch(
        self,
        patch: str,
        filename: str,
        index: faiss.Index,
        metadata: List[Dict],
        repo_name: str = "",
    ) -> PatchReview:
        """
        Generate a review for a single patch.

        Args:
            patch: The patch/diff content
            filename: The filename being reviewed
            index: FAISS index for semantic search
            metadata: Metadata for indexed chunks
            repo_name: Name of repository

        Returns:
            PatchReview object with structured comments
        """
        start_time = time.time()

        try:
            language = detect_language_from_filename(str(filename))
            symbols = extract_symbols_from_patch(patch)
            trimmed = trim_diff(patch)

            # Get semantic context
            context_chunks = semantic_search(trimmed, index, metadata)
            context_chunks = context_chunks[:TOP_K]

            # Generate review prompt
            prompt = self._build_review_prompt(
                filename=filename,
                language=language,
                symbols=symbols,
                context=context_chunks,
                patch=trimmed,
            )

            logger.debug(
                "Generating review",
                filename=filename,
                patch_length=len(trimmed),
            )

            # Call API with retry logic
            response_text = self._call_api_with_retry(prompt)

            # Parse response into structured comments
            comments = self._parse_review_response(response_text)

            processing_time = (time.time() - start_time) * 1000

            logger.info(
                "Review generated",
                filename=filename,
                comments_count=len(comments),
                processing_time_ms=int(processing_time),
            )

            return PatchReview(
                file=filename,
                language=language,
                symbols=symbols,
                comments=comments,
                summary=response_text[:1000],
                context_used=context_chunks,
                processing_time_ms=processing_time,
                status="success",
            )

        except Exception as e:
            logger.error(
                "Review generation failed",
                filename=filename,
                error=str(e),
                exc_info=True,
            )
            return PatchReview(
                file=filename,
                language="unknown",
                symbols=[],
                comments=[],
                summary=f"Review failed: {str(e)}",
                context_used=[],
                processing_time_ms=(time.time() - start_time) * 1000,
                status="failure",
            )

    def _build_review_prompt(
        self,
        filename: str,
        language: str,
        symbols: List[str],
        context: List[Dict],
        patch: str,
    ) -> str:
        """Build the review prompt."""
        return f"""
You are an expert software code reviewer. Analyze the following patch and provide a detailed code review.

**File:** {filename}
**Language:** {language}
**Changed Symbols:** {', '.join(symbols) if symbols else 'N/A'}

**Repository Context** (similar code from repo):
{json.dumps(context, indent=2)[:2000]}

**Patch to Review:**
{patch}

Please provide a detailed review with:
1. **Critical Issues**: Security vulnerabilities, crashes, data loss risks
2. **Warnings**: Performance issues, code smells, maintainability concerns
3. **Info**: Style suggestions, documentation improvements

Format each issue as:
- [CRITICAL/WARNING/INFO] Category: Brief description

Be specific and actionable in your feedback.
"""

    def _call_api_with_retry(
        self, prompt: str, max_retries: int = 3
    ) -> str:
        """Call Gemini API with exponential backoff retry."""
        delay = 10

        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                if response and response.text:
                    return response.text
                return "No response from API"

            except ResourceExhausted as e:
                logger.warning(
                    "API rate limit hit",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                )
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise Exception(f"API rate limit exceeded after {max_retries} retries")

            except Exception as e:
                logger.error(f"API error: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    raise

        return "Review failed after all retries"

    def review_batch(
        self,
        patches: List[Tuple[str, str]],  # List of (patch, filename)
        index: faiss.Index,
        metadata: List[Dict],
    ) -> List[PatchReview]:
        """
        Review multiple patches in parallel.

        Args:
            patches: List of (patch, filename) tuples
            index: FAISS index for semantic search
            metadata: Metadata for indexed chunks

        Returns:
            List of PatchReview objects
        """
        reviews = []

        with ThreadPoolExecutor(max_workers=DEFAULT_PARALLEL_WORKERS) as executor:
            futures = {
                executor.submit(
                    self.review_patch, patch, filename, index, metadata
                ): filename
                for patch, filename in patches
            }

            for future in as_completed(futures):
                try:
                    review = future.result()
                    reviews.append(review)
                except Exception as e:
                    filename = futures[future]
                    logger.error(
                        "Parallel review failed",
                        filename=filename,
                        error=str(e),
                    )
                    reviews.append(
                        PatchReview(
                            file=filename,
                            language="unknown",
                            symbols=[],
                            comments=[],
                            summary=f"Review failed: {str(e)}",
                            context_used=[],
                            processing_time_ms=0,
                            status="failure",
                        )
                    )

        return reviews


def review_patch_legacy(
    patch: str,
    filename: str,
    repo_full_name: str,
    ref: str,
    commit_sha: str,
    index: faiss.Index,
    metadata: List[dict],
) -> Dict[str, Any]:
    """
    Legacy interface for backward compatibility.
    Generates a review using the new ReviewGenerator.
    """
    generator = ReviewGenerator()
    review = generator.review_patch(patch, filename, index, metadata, repo_full_name)

    # Convert to legacy format
    return {
        "file": review.file,
        "language": review.language,
        "symbols": review.symbols,
        "review": review.summary,
        "context_used": review.context_used,
        "comments": [
            {
                "severity": comment.severity.value,
                "category": comment.category,
                "text": comment.comment,
            }
            for comment in review.comments
        ],
        "status": review.status,
        "processing_time_ms": int(review.processing_time_ms),
    }
