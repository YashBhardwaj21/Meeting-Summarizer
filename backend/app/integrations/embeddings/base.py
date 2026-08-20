from typing import Protocol


class EmbeddingProvider(Protocol):
    """Interface for text embedding providers."""
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of strings.
        Must return a list of exactly the same length as `texts`,
        where each item is a list of floats of length `self.dimensions`.
        """
        ...
        
    @property
    def dimensions(self) -> int:
        """The number of dimensions produced by this embedding provider."""
        ...
        
    @property
    def model_name(self) -> str:
        """The identifier of the embedding model."""
        ...
