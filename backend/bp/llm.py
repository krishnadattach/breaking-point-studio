"""Creates the Claude chat models. Cheap model for simple steps, writer model for the script."""
from langchain_anthropic import ChatAnthropic

from . import config


def cheap():
    """Haiku: used for fact-checking (simple yes/no work)."""
    return ChatAnthropic(model=config.MODEL_CHEAP, max_tokens=2000)


def writer():
    """Sonnet: used once per script draft."""
    return ChatAnthropic(model=config.MODEL_WRITER, max_tokens=4000)
