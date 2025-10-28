"""Local embedding generation using sentence-transformers."""

import structlog
from sentence_transformers import SentenceTransformer

logger = structlog.get_logger()


class EmbeddingService:
    """Generate embeddings using local transformer model."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize embedding model.
        
        Args:
            model_name: HuggingFace model name
        """
        self.model_name = model_name
        self.model: SentenceTransformer = None
        logger.info("embedding_service_initialized", model=model_name)

    def load_model(self) -> None:
        """Load transformer model (call on startup)."""
        self.model = SentenceTransformer(self.model_name)
        logger.info("embedding_model_loaded", model=self.model_name)

    def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for single text.
        
        Args:
            text: Input text
            
        Returns:
            384-dimensional embedding vector
        """
        if not self.model:
            raise RuntimeError("Embedding model not loaded")

        embedding = self.model.encode(text, convert_to_numpy=True)
        logger.debug("embedding_generated", length=len(text), dim=len(embedding))
        return embedding.tolist()

    def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of 384-dimensional embedding vectors
        """
        if not self.model:
            raise RuntimeError("Embedding model not loaded")

        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        logger.info("embeddings_generated_batch", count=len(texts))
        return [emb.tolist() for emb in embeddings]
