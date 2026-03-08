"""
Custom RAG prompt loader for CDSCO pharmaceutical regulatory compliance.

Loads the full system prompt from `data/rag_system_prompt.txt` and
provides template variable substitution.

Usage:
    from app.utils.custom_prompt import get_prompt_loader
    loader = get_prompt_loader()
    prompt = loader.get_system_prompt()
"""

import logging
import os
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to the prompt file relative to this module
_PROMPT_DIR = Path(__file__).resolve().parent.parent / "data"
_DEFAULT_PROMPT_FILE = "rag_system_prompt.txt"


class PromptLoader:
    """
    Load and manage the custom RAG system prompt.
    
    The prompt is loaded once from disk and cached.
    Template variables {context} and {query} are left as-is
    for Bedrock's promptTemplate to substitute at runtime.
    """

    def __init__(self, prompt_dir: Path = _PROMPT_DIR, prompt_file: str = _DEFAULT_PROMPT_FILE):
        self._prompt_dir = prompt_dir
        self._prompt_file = prompt_file
        self._cached_prompt: str | None = None

    def _load_from_disk(self) -> str:
        """Read the prompt file from disk."""
        file_path = self._prompt_dir / self._prompt_file

        if not file_path.exists():
            logger.error("Prompt file not found: %s", file_path)
            raise FileNotFoundError(
                f"RAG system prompt not found at {file_path}. "
                f"Please ensure 'data/rag_system_prompt.txt' exists in the app directory."
            )

        text = file_path.read_text(encoding="utf-8").strip()
        logger.info("Loaded RAG system prompt: %d chars from %s", len(text), file_path)
        return text

    def get_system_prompt(self) -> str:
        """
        Get the full system prompt text.
        
        Returns the raw prompt with {context} and {query} placeholders
        intact — Bedrock's promptTemplate handles substitution.
        
        NOTE: Bedrock Knowledge Base uses $search_results$ for context.
        We include both {context} and $search_results$ for compatibility.
        """
        if self._cached_prompt is None:
            raw = self._load_from_disk()
            
            # Bedrock KB uses $search_results$ as its context placeholder.
            # Our prompt uses {context}. Replace for Bedrock compatibility.
            # Keep {query} as the user's input placeholder (handled by input.text).
            bedrock_prompt = raw.replace("{context}", "$search_results$")
            bedrock_prompt = bedrock_prompt.replace("{query}", "$query$")
            
            self._cached_prompt = bedrock_prompt

        return self._cached_prompt

    def get_raw_prompt(self) -> str:
        """Get the unmodified prompt text directly from file."""
        return self._load_from_disk()

    def reload(self) -> str:
        """Force reload the prompt from disk (useful for hot-reloading)."""
        self._cached_prompt = None
        return self.get_system_prompt()


@lru_cache()
def get_prompt_loader() -> PromptLoader:
    """Singleton prompt loader — cached after first call."""
    return PromptLoader()
