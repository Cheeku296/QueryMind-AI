import logging
import time
from typing import Any, Dict, Optional, Tuple, Type
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIProviderManager:
    """Centralized LLM provider manager with Google Gemini as primary default."""

    def __init__(self):
        self._llm = None
        self._genai_client = None

    @property
    def provider_name(self) -> str:
        return settings.LLM_PROVIDER.lower()

    @property
    def model_name(self) -> str:
        if self.provider_name == "ollama":
            return settings.OLLAMA_MODEL
        return settings.GEMINI_MODEL

    def is_configured(self) -> bool:
        """Returns True if the active provider has valid credentials."""
        if self.provider_name == "gemini":
            return bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 10)
        elif self.provider_name == "ollama":
            return bool(settings.OLLAMA_BASE_URL)
        return False

    def get_llm(self, temperature: float = 0.0):
        """Returns initialized LangChain chat model."""
        if self.provider_name == "gemini":
            if not self.is_configured():
                raise ValueError(
                    "Google Gemini API key is not configured. "
                    "Please set GEMINI_API_KEY in backend/.env with your key from Google AI Studio."
                )
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=settings.GEMINI_API_KEY,
                temperature=temperature,
                max_retries=2,
                timeout=30.0,
            )
        elif self.provider_name == "ollama":
            from langchain_community.chat_models import ChatOllama
            return ChatOllama(
                base_url=settings.OLLAMA_BASE_URL,
                model=self.model_name,
                temperature=temperature,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider_name}")

    def test_connectivity(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Performs a real live test against Google Gemini API."""
        if not self.is_configured():
            return False, "Gemini API key is not configured. Please paste your key in backend/.env.", {}

        start_time = time.perf_counter()
        try:
            llm = self.get_llm(temperature=0.0)
            response = llm.invoke([
                SystemMessage(content="You are QueryMind AI system validator."),
                HumanMessage(content="Respond with the exact word 'READY' and nothing else.")
            ])
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            text_resp = response.content.strip() if hasattr(response, "content") else str(response)

            return True, f"Gemini API handshake successful ({duration_ms}ms).", {
                "provider": "gemini",
                "model": self.model_name,
                "latency_ms": duration_ms,
                "response_sample": text_resp[:100],
            }
        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            err_str = str(e)
            logger.warning(f"Gemini connectivity test failed ({duration_ms}ms): {err_str}")
            return False, f"Gemini API connection error: {err_str}", {
                "provider": "gemini",
                "model": self.model_name,
                "latency_ms": duration_ms,
                "error": err_str,
            }

    def generate_structured(
        self,
        prompt: str,
        schema_class: Type[BaseModel],
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
    ) -> BaseModel:
        """Invokes Gemini with structured output validation."""
        llm = self.get_llm(temperature=temperature)
        structured_llm = llm.with_structured_output(schema_class)

        messages = []
        if system_instruction:
            messages.append(SystemMessage(content=system_instruction))
        messages.append(HumanMessage(content=prompt))

        result = structured_llm.invoke(messages)
        return result

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Invokes Gemini for freeform conversational or analytical text."""
        llm = self.get_llm(temperature=temperature)
        messages = []
        if system_instruction:
            messages.append(SystemMessage(content=system_instruction))
        messages.append(HumanMessage(content=prompt))

        response = llm.invoke(messages)
        return response.content.strip() if hasattr(response, "content") else str(response)


ai_provider = AIProviderManager()
