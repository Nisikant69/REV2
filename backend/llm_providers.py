"""
Abstract LLM providers for multi-model support.
Supports Gemini, Claude, GPT-4, and local endpoints.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from backend.logger import get_logger

logger = get_logger(__name__)


class CodeReviewProvider(ABC):
    """Abstract base class for code review LLM providers."""

    @abstractmethod
    def generate_review(self, prompt: str, max_retries: int = 3) -> str:
        """
        Generate a code review from the given prompt.

        Args:
            prompt: The review prompt
            max_retries: Maximum retries on rate limit

        Returns:
            Review text
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if provider is accessible."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get provider name."""
        pass


class GeminiProvider(CodeReviewProvider):
    """Google Gemini API provider."""

    def __init__(self, api_key: str = None, model_name: str = "gemini-2.5-pro"):
        """Initialize Gemini provider."""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(model_name)
        else:
            self.model = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    def generate_review(self, prompt: str, max_retries: int = 3) -> str:
        """Generate review using Gemini API."""
        if not self.model:
            raise RuntimeError("Gemini API not configured")

        import time
        delay = 10

        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                if response and response.text:
                    logger.debug("Gemini API call successful")
                    return response.text
                return "No response from Gemini API"

            except ResourceExhausted:
                logger.warning(
                    "Gemini rate limit hit",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                )
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise

            except Exception as e:
                logger.error(f"Gemini API error: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    raise

        return "Review failed after all retries"

    def health_check(self) -> bool:
        """Check Gemini API health."""
        try:
            if not self.model:
                return False
            # Try a simple API call
            response = self.model.generate_content("Say 'OK'")
            return response and response.text
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            return False


class ClaudeProvider(CodeReviewProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: str = None, model_name: str = "claude-3-sonnet-20240229"):
        """Initialize Claude provider."""
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY")
        self.model_name = model_name
        if self.api_key:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
            except ImportError:
                logger.warning("anthropic library not installed")
                self.client = None
        else:
            self.client = None

    @property
    def provider_name(self) -> str:
        return "claude"

    def generate_review(self, prompt: str, max_retries: int = 3) -> str:
        """Generate review using Claude API."""
        if not self.client:
            raise RuntimeError("Claude API not configured")

        import time
        delay = 10

        for attempt in range(max_retries):
            try:
                message = self.client.messages.create(
                    model=self.model_name,
                    max_tokens=2048,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                if message.content:
                    logger.debug("Claude API call successful")
                    return message.content[0].text
                return "No response from Claude API"

            except Exception as e:
                if "rate_limit" in str(e).lower():
                    logger.warning(
                        "Claude rate limit hit",
                        attempt=attempt + 1,
                    )
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay *= 2
                    else:
                        raise
                else:
                    logger.error(f"Claude API error: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(5)
                    else:
                        raise

        return "Review failed after all retries"

    def health_check(self) -> bool:
        """Check Claude API health."""
        try:
            if not self.client:
                return False
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "Say OK"}]
            )
            return message and message.content
        except Exception as e:
            logger.warning(f"Claude health check failed: {e}")
            return False


class GPT4Provider(CodeReviewProvider):
    """OpenAI GPT-4 API provider."""

    def __init__(self, api_key: str = None, model_name: str = "gpt-4"):
        """Initialize GPT-4 provider."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                logger.warning("openai library not installed")
                self.client = None
        else:
            self.client = None

    @property
    def provider_name(self) -> str:
        return "gpt4"

    def generate_review(self, prompt: str, max_retries: int = 3) -> str:
        """Generate review using GPT-4 API."""
        if not self.client:
            raise RuntimeError("GPT-4 API not configured")

        import time
        delay = 10

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert code reviewer."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2048,
                )
                if response.choices and response.choices[0].message.content:
                    logger.debug("GPT-4 API call successful")
                    return response.choices[0].message.content
                return "No response from GPT-4 API"

            except Exception as e:
                if "rate_limit" in str(e).lower():
                    logger.warning(
                        "GPT-4 rate limit hit",
                        attempt=attempt + 1,
                    )
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay *= 2
                    else:
                        raise
                else:
                    logger.error(f"GPT-4 API error: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(5)
                    else:
                        raise

        return "Review failed after all retries"

    def health_check(self) -> bool:
        """Check GPT-4 API health."""
        try:
            if not self.client:
                return False
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Say OK"}],
                max_tokens=10,
            )
            return response and response.choices
        except Exception as e:
            logger.warning(f"GPT-4 health check failed: {e}")
            return False


class LLMProviderManager:
    """Manages multiple LLM providers with fallback."""

    def __init__(
        self,
        primary_provider: str = "gemini",
        fallback_provider: Optional[str] = "claude",
    ):
        """
        Initialize provider manager.

        Args:
            primary_provider: Primary LLM provider name
            fallback_provider: Fallback provider if primary fails
        """
        self.primary_provider_name = primary_provider
        self.fallback_provider_name = fallback_provider
        self.providers = self._initialize_providers()

    def _initialize_providers(self) -> dict:
        """Initialize all configured providers."""
        providers = {}

        # Initialize primary provider
        primary = self._get_provider(self.primary_provider_name)
        if primary:
            providers[self.primary_provider_name] = primary

        # Initialize fallback provider
        if self.fallback_provider_name:
            fallback = self._get_provider(self.fallback_provider_name)
            if fallback:
                providers[self.fallback_provider_name] = fallback

        return providers

    def _get_provider(self, provider_name: str) -> Optional[CodeReviewProvider]:
        """Get provider instance by name."""
        if provider_name == "gemini":
            return GeminiProvider()
        elif provider_name == "claude":
            return ClaudeProvider()
        elif provider_name == "gpt4":
            return GPT4Provider()
        else:
            logger.warning(f"Unknown provider: {provider_name}")
            return None

    def generate_review(self, prompt: str) -> tuple:
        """
        Generate review with fallback.

        Returns:
            Tuple of (review_text, provider_used)
        """
        # Try primary provider
        if self.primary_provider_name in self.providers:
            try:
                provider = self.providers[self.primary_provider_name]
                review = provider.generate_review(prompt)
                logger.info(
                    "Review generated",
                    provider=self.primary_provider_name,
                )
                return review, self.primary_provider_name
            except Exception as e:
                logger.warning(
                    f"Primary provider failed: {e}",
                    provider=self.primary_provider_name,
                )

        # Try fallback provider
        if self.fallback_provider_name and self.fallback_provider_name in self.providers:
            try:
                provider = self.providers[self.fallback_provider_name]
                review = provider.generate_review(prompt)
                logger.info(
                    "Review generated (fallback)",
                    provider=self.fallback_provider_name,
                )
                return review, self.fallback_provider_name
            except Exception as e:
                logger.error(
                    f"Fallback provider also failed: {e}",
                    provider=self.fallback_provider_name,
                )

        raise RuntimeError("All LLM providers failed")

    def health_check(self) -> dict:
        """Check health of all providers."""
        status = {}
        for name, provider in self.providers.items():
            try:
                status[name] = provider.health_check()
            except Exception as e:
                logger.warning(f"Health check failed for {name}: {e}")
                status[name] = False
        return status


# Global provider manager
_provider_manager: Optional[LLMProviderManager] = None


def get_provider_manager() -> LLMProviderManager:
    """Get or create global provider manager."""
    global _provider_manager
    if _provider_manager is None:
        primary = os.getenv("PRIMARY_LLM_PROVIDER", "gemini")
        fallback = os.getenv("FALLBACK_LLM_PROVIDER", "claude")
        _provider_manager = LLMProviderManager(
            primary_provider=primary,
            fallback_provider=fallback,
        )
    return _provider_manager
