"""Google Gemini API client wrapper."""

import json
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar

import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse
from pydantic import BaseModel, ValidationError

from supportops_agent.cache import get_cache
from supportops_agent.config import settings
from supportops_agent.llm.circuit_breaker import CircuitBreaker
from supportops_agent.llm.retry import retry_with_backoff
from supportops_agent.metrics import get_metrics

logger = logging.getLogger(__name__)
metrics = get_metrics()
cache = get_cache()

T = TypeVar("T", bound=BaseModel)


class GeminiClient:
    """Client for Google Gemini API with structured output support."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize Gemini client."""
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model or settings.gemini_model
        self.base_url = base_url or settings.gemini_base_url

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        
        # Circuit breaker for resilience
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
        )

    def _parse_json_response(self, text: str, max_retries: int = 2) -> Dict[str, Any]:
        """Parse JSON from text with retry and repair logic."""
        # Try to extract JSON from markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()

        for attempt in range(max_retries):
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    # Try to repair common JSON issues
                    text = text.replace("'", '"')  # Replace single quotes
                    text = text.replace("None", "null")  # Replace Python None
                    text = text.replace("True", "true")  # Replace Python True
                    text = text.replace("False", "false")  # Replace Python False
                    logger.warning(f"JSON parse error (attempt {attempt + 1}): {e}, trying repair")
                else:
                    logger.error(f"Failed to parse JSON after {max_retries} attempts: {e}")
                    raise

    @retry_with_backoff(max_retries=3, initial_delay=1.0, max_delay=10.0)
    def chat(
        self,
        messages: List[Dict[str, str]],
        response_schema: Optional[Type[BaseModel]] = None,
        temperature: float = 0.0,
        timeout: float = 30.0,
        max_retries: int = 2,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Chat with Gemini model.

        Args:
            messages: List of message dicts with 'role' and 'content'
            response_schema: Optional Pydantic model for structured output
            temperature: Sampling temperature (0.0 for deterministic)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for JSON parsing
            use_cache: Whether to use response caching

        Returns:
            Parsed response as dict, or validated Pydantic model if schema provided
        """
        # Check cache first
        if use_cache:
            cache_key = cache._make_key(
                "gemini_chat",
                messages=messages,
                schema=response_schema.__name__ if response_schema else None,
                temperature=temperature,
            )
            cached = cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for Gemini chat: {cache_key[:20]}...")
                metrics.increment("llm.cache_hits")
                return cached

        # Convert messages to Gemini format
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"System: {content}\n")
            elif role == "user":
                prompt_parts.append(f"User: {content}\n")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}\n")

        # Add schema instruction if provided
        if response_schema:
            schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
            prompt_parts.append(
                f"\nYou must respond with valid JSON matching this schema:\n{schema_json}\n"
            )
            prompt_parts.append("Return only the JSON object, no additional text.\n")

        prompt = "".join(prompt_parts)

        try:
            # Use circuit breaker for resilience
            with metrics.timer("llm.gemini.chat", tags={"model": self.model_name}):
                # Generate content
                generation_config = genai.types.GenerationConfig(
                    temperature=temperature,
                )

                def _call_gemini():
                    return self.model.generate_content(
                        prompt,
                        generation_config=generation_config,
                    )

                response: GenerateContentResponse = self.circuit_breaker.call(_call_gemini)
            
            metrics.increment("llm.gemini.calls", tags={"model": self.model_name})

            if not response.text:
                raise ValueError("Empty response from Gemini API")

            # Parse JSON if schema provided
            if response_schema:
                parsed = self._parse_json_response(response.text, max_retries)
                # Validate against schema
                try:
                    validated = response_schema(**parsed)
                    result = validated.model_dump()
                except ValidationError as e:
                    logger.error(f"Schema validation failed: {e}")
                    metrics.record_error("llm.schema_validation_failed", str(e))
                    # Return parsed anyway, but log warning
                    result = parsed
            else:
                # Return raw text as dict
                result = {"text": response.text}

            # Cache the result
            if use_cache:
                cache.set(cache_key, result, ttl=3600)  # Cache for 1 hour

            return result

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            metrics.record_error("llm.gemini.error", str(e), {"model": self.model_name})
            metrics.increment("llm.gemini.errors", tags={"model": self.model_name})
            raise

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
    ) -> Any:
        """Stream chat responses (for future use)."""
        # Implementation for streaming if needed
        raise NotImplementedError("Streaming not yet implemented")
