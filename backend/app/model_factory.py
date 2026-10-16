from app.config import get_settings
from app.model_adapter import OpenAIResponses
from app.gemini_adapter import GeminiGenerateContent


def configured_model():
    settings = get_settings()
    provider = settings.llm_provider
    if provider == "auto":
        provider = "gemini" if settings.llm_model.startswith("gemini-") else "openai"
    if provider == "gemini":
        return GeminiGenerateContent()
    if provider == "openai":
        return OpenAIResponses()
    raise ValueError("LLM_PROVIDER must be auto, gemini or openai")
