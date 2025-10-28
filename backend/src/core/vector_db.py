"""ChromaDB client for vector storage and similarity search."""
from typing import Any

import chromadb
import structlog
from chromadb.config import Settings

logger = structlog.get_logger()


class VectorDBClient:
    """ChromaDB client for test case embeddings."""

    def __init__(
        self,
        host: str,
        port: int,
        collection_name: str = "test_cases"
    ):
        """Initialize ChromaDB client.
        
        Args:
            host: ChromaDB hostname
            port: ChromaDB port
            collection_name: Collection name for test cases
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.client: chromadb.HttpClient | None = None
        self.collection: chromadb.Collection | None = None
        logger.info(
            "vector_db_initialized",
            host=host,
            port=port,
            collection=collection_name
        )

    async def connect(self) -> None:
        """Connect to ChromaDB and get/create collection."""
        self.client = chromadb.HttpClient(
            host=self.host,
            port=self.port,
            settings=Settings(anonymized_telemetry=False)
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "AI-generated test case documents"}
        )
        logger.info("vector_db_connected", collection=self.collection_name)

    async def disconnect(self) -> None:
        """Disconnect from ChromaDB."""
        self.client = None
        self.collection = None
        logger.info("vector_db_disconnected")

    async def add_documents(
        self,
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        ids: list[str]
    ) -> None:
        """Add documents with embeddings to collection.
        
        Args:
            documents: Document texts
            embeddings: Document embeddings (384-dim vectors)
            metadatas: Document metadata (issue_id, created_at, etc.)
            ids: Document IDs
        """
        if not self.collection:
            raise RuntimeError("ChromaDB collection not initialized")

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        logger.info("vector_db_added", count=len(documents))

    async def query_similar(
        self,
        query_embedding: list[float],
        n_results: int = 5
    ) -> dict[str, Any]:
        """Query similar documents by embedding.
        
        Args:
            query_embedding: Query vector (384-dim)
            n_results: Number of results to return
            
        Returns:
            Dict with 'documents', 'metadatas', 'distances', 'ids'
        """
        if not self.collection:
            raise RuntimeError("ChromaDB collection not initialized")

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        logger.info(
            "vector_db_queried",
            n_results=n_results,
            found=len(results['documents'][0]) if results['documents'] else 0
        )
        return results

    async def delete_old_documents(self, days: int = 30) -> int:
        """Delete documents older than specified days.
        
        Args:
            days: Age threshold in days
            
        Returns:
            Number of documents deleted
        """
        if not self.collection:
            raise RuntimeError("ChromaDB collection not initialized")

        # ChromaDB doesn't have built-in TTL, so we filter by metadata
        # This is a placeholder for manual cleanup job
        logger.info("vector_db_cleanup_triggered", days=days)
        return 0  # Implement cleanup logic based on created_at metadata

    async def get_collection_count(self) -> int:
        """Get number of documents in collection.
        
        Returns:
            Document count
        """
        if not self.collection:
            raise RuntimeError("ChromaDB collection not initialized")

        count = self.collection.count()
        logger.debug("vector_db_count", count=count)
        return count
