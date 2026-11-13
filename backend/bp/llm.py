"""Creates the Claude chat models. Cheap model for simple steps, writer model for the script."""
from langchain_anthropic import ChatAnthropic

from . import config


def cheap():
    """Haiku: used for fact-checking (simple yes/no work)."""
    # max_tokens is only a ceiling (you pay for tokens actually used). It must leave room for the
    # model's hidden "thinking" tokens, or the answer gets cut off (seen with the writer at 4000).
    return ChatAnthropic(model=config.MODEL_CHEAP, max_tokens=8000)


def writer():
    """Sonnet: used once per script draft."""
    return ChatAnthropic(model=config.MODEL_WRITER, max_tokens=16000)
