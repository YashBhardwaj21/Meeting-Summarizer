from typing import Protocol


class TokenCounter(Protocol):
    """Interface for token counting implementations."""
    
    def count(self, text: str) -> int:
        """Count the number of tokens in the given text."""
        ...


class TiktokenCounter:
    """Token counter using OpenAI's tiktoken library."""
    
    def __init__(self, encoding: str = "cl100k_base"):
        import tiktoken
        self._encoding = tiktoken.get_encoding(encoding)
        
    def count(self, text: str) -> int:
        """Count tokens accurately using the specified encoding."""
        # Avoid crashing on empty strings or None
        if not text:
            return 0
        return len(self._encoding.encode(text))
