"""
LLM Service with Two-Phased Security Verification

This service provides a secure interface to Databricks-hosted LLM endpoints with:
1. Phase 1: Security check for injection attempts and malicious content
2. Phase 2: Content analysis with configurable system prompt

All interactions use the OpenAI SDK with Databricks endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
import os

from src.common.config import Settings, get_settings
from src.common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LLMAnalysisResult:
    """Result from LLM analysis with security metadata."""
    success: bool
    content: str
    phase1_passed: bool  # True if security check passed
    render_as_markdown: bool  # True if safe to render as markdown (phase1 passed)
    llm_model_used: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class LLMService:
    """Service for secure LLM interactions with two-phased verification."""

    def __init__(self, settings: Settings):
        """
        Initialize LLM service.

        Args:
            settings: Application settings with LLM configuration
        """
        self.settings = settings

    def _get_openai_client(self, user_token: Optional[str] = None):
        """
        Create OpenAI client for Databricks with proper authentication.

        In Databricks Apps: Uses user_token from x-forwarded-access-token header
        In local dev: Falls back to DATABRICKS_TOKEN from settings/env

        Args:
            user_token: Per-user access token from request header (Databricks Apps context)

        Returns:
            Configured OpenAI client instance

        Note: Creates new client instance each time (not cached) because each user
        has a different token in Databricks Apps context.
        """
        try:
            from openai import OpenAI

            # Use user token (Databricks Apps) or fall back to global token (local dev)
            token = user_token or self.settings.DATABRICKS_TOKEN or os.environ.get('DATABRICKS_TOKEN')
            if not token:
                raise RuntimeError("No authentication token available (user_token or DATABRICKS_TOKEN)")

            # Derive base URL from explicit config or DATABRICKS_HOST
            base_url = self.settings.LLM_BASE_URL
            if not base_url and self.settings.DATABRICKS_HOST:
                # Use same host as workspace client + /serving-endpoints suffix
                base_url = f"{self.settings.DATABRICKS_HOST.rstrip('/')}/serving-endpoints"

            if not base_url:
                raise RuntimeError("LLM_BASE_URL not configured and cannot be derived from DATABRICKS_HOST")

            # Create new client instance (don't cache - each user has different token)
            client = OpenAI(
                api_key=token,
                base_url=base_url
            )

            token_source = "user_token" if user_token else "DATABRICKS_TOKEN"
            logger.info(f"OpenAI client created for Databricks at {base_url} (auth: {token_source})")
            return client

        except Exception as e:
            logger.error(f"Failed to create OpenAI client: {e}")
            raise RuntimeError(f"OpenAI client initialization failed: {e}")

    def is_enabled(self) -> bool:
        """Check if LLM functionality is enabled."""
        return self.settings.LLM_ENABLED

    def get_endpoint(self) -> Optional[str]:
        """Get the configured LLM endpoint."""
        endpoint = self.settings.LLM_ENDPOINT
        if not endpoint:
            logger.warning("No LLM endpoint configured (LLM_ENDPOINT)")
        return endpoint

    def _call_llm(self, messages: list[Dict[str, str]], max_tokens: int = 1024, user_token: Optional[str] = None) -> Optional[str]:
        """
        Internal method to call LLM endpoint via OpenAI SDK.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            user_token: Per-user access token (for Databricks Apps)

        Returns:
            Response content string or None on failure
        """
        endpoint = self.get_endpoint()
        if not endpoint:
            logger.error("Cannot call LLM: No endpoint configured")
            return None

        try:
            client = self._get_openai_client(user_token=user_token)

            response = client.chat.completions.create(
                model=endpoint,
                messages=messages,
                max_tokens=max_tokens
            )

            # Extract content from OpenAI response
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content:
                    return str(content).strip()

            logger.warning(f"LLM returned no content in response")
            return None

        except Exception as e:
            logger.error(f"Error calling LLM endpoint {endpoint}: {e}", exc_info=True)
            return None

    def _phase1_security_check(self, content: str, user_token: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Phase 1: Security check for injection attempts and malicious content.

        Args:
            content: User-provided content to analyze
            user_token: Per-user access token (for Databricks Apps)

        Returns:
            Tuple of (passed: bool, reason: Optional[str])
        """
        logger.info("Running Phase 1: Security injection check")

        messages = [
            {"role": "system", "content": self.settings.LLM_INJECTION_CHECK_PROMPT},
            {"role": "user", "content": content}
        ]

        response = self._call_llm(messages, max_tokens=256, user_token=user_token)

        if response is None:
            logger.error("Phase 1 security check failed: No response from LLM")
            return False, "Security check failed: Unable to verify content safety"

        # Check if response indicates content is safe
        response_upper = response.upper()
        if "SAFE" in response_upper and "UNSAFE" not in response_upper:
            logger.info("Phase 1 PASSED: Content deemed safe")
            return True, None
        else:
            # Extract reason if available
            reason = response if "UNSAFE" in response_upper else "Content flagged as potentially unsafe"
            logger.warning(f"Phase 1 FAILED: {reason}")
            return False, reason

    def _phase2_content_analysis(self, content: str, user_token: Optional[str] = None) -> Optional[str]:
        """
        Phase 2: Content analysis with configurable system prompt.

        Args:
            content: Content to analyze (already passed security check)
            user_token: Per-user access token (for Databricks Apps)

        Returns:
            Analysis result or None on failure
        """
        logger.info("Running Phase 2: Content analysis")

        # Use configured system prompt or fallback to a default
        system_prompt = self.settings.LLM_SYSTEM_PROMPT or (
            "You are a Data Steward tasked with reviewing metadata, data, and SQL/Python code to check if "
            "any sensitive information is used. These include PII data, like names, addresses, age, "
            "social security numbers, credit card numbers etc. Look at the provided text and identify "
            "insecure coding or sensitive data and return a summary."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]

        response = self._call_llm(messages, max_tokens=2048, user_token=user_token)

        if response:
            logger.info("Phase 2 COMPLETED: Content analysis successful")
        else:
            logger.error("Phase 2 FAILED: No response from LLM")

        return response

    def analyze_content(self, content: str, user_token: Optional[str] = None) -> LLMAnalysisResult:
        """
        Analyze content with two-phased verification.

        Phase 1: Security check for injections/malicious content
        Phase 2: Content analysis with configured prompt (only if phase 1 passes)

        Args:
            content: Content to analyze
            user_token: Per-user access token from x-forwarded-access-token header (Databricks Apps)

        Returns:
            LLMAnalysisResult with security metadata
        """
        # Check if LLM is enabled
        if not self.is_enabled():
            logger.warning("LLM analysis requested but LLM_ENABLED is False")
            return LLMAnalysisResult(
                success=False,
                content="",
                phase1_passed=False,
                render_as_markdown=False,
                error_message="LLM functionality is disabled"
            )

        endpoint = self.get_endpoint()
        if not endpoint:
            return LLMAnalysisResult(
                success=False,
                content="",
                phase1_passed=False,
                render_as_markdown=False,
                error_message="No LLM endpoint configured"
            )

        # Phase 1: Security Check
        phase1_passed, security_reason = self._phase1_security_check(content, user_token=user_token)

        if not phase1_passed:
            # Return security failure - content should be displayed as plain text
            warning_message = (
                f"⚠️ SECURITY WARNING ⚠️\n\n"
                f"The content analysis was blocked due to potential security concerns:\n\n"
                f"{security_reason}\n\n"
                f"Please review the content manually."
            )
            return LLMAnalysisResult(
                success=False,
                content=warning_message,
                phase1_passed=False,
                render_as_markdown=False,  # Must display as plain text
                llm_model_used=endpoint,
                error_message=security_reason
            )

        # Phase 2: Content Analysis
        analysis = self._phase2_content_analysis(content, user_token=user_token)

        if analysis is None:
            return LLMAnalysisResult(
                success=False,
                content="",
                phase1_passed=True,
                render_as_markdown=False,
                llm_model_used=endpoint,
                error_message="Content analysis failed after security check"
            )

        # Success: Both phases passed
        return LLMAnalysisResult(
            success=True,
            content=analysis,
            phase1_passed=True,
            render_as_markdown=True,  # Safe to render as markdown
            llm_model_used=endpoint
        )


def get_llm_service() -> LLMService:
    """Get or create the global LLM service instance."""
    settings = get_settings()
    return LLMService(settings)
