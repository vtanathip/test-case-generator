"""Ollama client for Llama 3.2 inference."""
import httpx
from typing import Optional, Dict, Any, AsyncGenerator
import structlog

logger = structlog.get_logger()


class LLMClient:
    """Async Ollama client for local LLM inference."""

    def __init__(self, host: str, model: str, timeout: int = 120):
        """Initialize Ollama client.
        
        Args:
            host: Ollama server URL (e.g., http://ollama:11434)
            model: Model name (e.g., llama3.2:11b)
            timeout: Request timeout in seconds
        """
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
        logger.info("llm_client_initialized", host=host, model=model, timeout=timeout)

    async def connect(self) -> None:
        """Initialize HTTP client."""
        self.client = httpx.AsyncClient(timeout=self.timeout)
        # Verify Ollama is reachable
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            response.raise_for_status()
            logger.info("llm_client_connected")
        except Exception as e:
            logger.error("llm_client_connection_failed", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            logger.info("llm_client_disconnected")

    async def generate(
        self, 
        prompt: str, 
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate completion from prompt.
        
        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        if not self.client:
            raise RuntimeError("LLM client not connected")

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        
        if system:
            payload["system"] = system
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            response = await self.client.post(
                f"{self.host}/api/generate",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            generated_text = result.get("response", "")
            logger.info(
                "llm_generated",
                model=self.model,
                prompt_length=len(prompt),
                response_length=len(generated_text),
                done=result.get("done", False)
            )
            return generated_text
            
        except httpx.TimeoutException as e:
            logger.error("llm_timeout", model=self.model, timeout=self.timeout)
            raise TimeoutError(f"LLM generation timeout after {self.timeout}s") from e
        except Exception as e:
            logger.error("llm_generation_failed", error=str(e))
            raise

    async def generate_stream(
        self, 
        prompt: str, 
        system: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Generate completion with streaming.
        
        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Sampling temperature
            
        Yields:
            Generated text chunks
        """
        if not self.client:
            raise RuntimeError("LLM client not connected")

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
            }
        }
        
        if system:
            payload["system"] = system

        try:
            async with self.client.stream(
                "POST",
                f"{self.host}/api/generate",
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        import json
                        chunk = json.loads(line)
                        if "response" in chunk:
                            yield chunk["response"]
                            
        except Exception as e:
            logger.error("llm_streaming_failed", error=str(e))
            raise
