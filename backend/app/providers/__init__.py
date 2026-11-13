"""
AI Provider Layer for Alex AI Desktop Assistant.
"""

from app.providers.base import (
    AuthenticationError,
    CancellationError,
    LLMProvider,
    ModelDescriptor,
    ModelNotFoundError,
    NormalizedProviderError,
    ProviderCapabilities,
    ProviderTimeoutError,
    QuotaExceededError,
    ServiceUnavailableError,
    StreamingChunk,
    UsageMetadata,
    redact_secret,
    validate_base_url,
)
from app.providers.openai_provider import AntiRepetitionGuard, OpenAICompatibleProvider
from app.providers.ollama_provider import OllamaProvider, check_host_memory_for_model
from app.providers.lm_studio_provider import LMStudioProvider
from app.providers.groq_provider import GroqProvider
from app.providers.deepseek_provider import DeepSeekProvider
from app.providers.reasoning_filter import ReasoningFilter
from app.providers.registry import ProviderRegistry, default_registry
from app.providers.schema_budget import (
    BUDGET_PROFILES,
    CORE_TOOLS_PRIORITY,
    ToolBudgetConfig,
    budget_tools,
    extract_tool_parts,
    payload_size,
)

# Register default provider classes with global registry
default_registry.register_class("openai", OpenAICompatibleProvider)
default_registry.register_class("ollama", OllamaProvider)
default_registry.register_class("lmstudio", LMStudioProvider)
default_registry.register_class("groq", GroqProvider)
default_registry.register_class("deepseek", DeepSeekProvider)

__all__ = [
    "AntiRepetitionGuard",
    "AuthenticationError",
    "BUDGET_PROFILES",
    "CancellationError",
    "CORE_TOOLS_PRIORITY",
    "DeepSeekProvider",
    "GroqProvider",
    "LLMProvider",
    "LMStudioProvider",
    "ModelDescriptor",
    "ModelNotFoundError",
    "NormalizedProviderError",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "ProviderCapabilities",
    "ProviderRegistry",
    "ProviderTimeoutError",
    "QuotaExceededError",
    "ReasoningFilter",
    "ServiceUnavailableError",
    "StreamingChunk",
    "ToolBudgetConfig",
    "UsageMetadata",
    "budget_tools",
    "check_host_memory_for_model",
    "default_registry",
    "extract_tool_parts",
    "payload_size",
    "redact_secret",
    "validate_base_url",
]

