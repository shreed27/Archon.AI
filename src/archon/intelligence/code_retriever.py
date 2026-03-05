import os
import chromadb
from pathlib import Path
from typing import List, Dict
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class CodeRetriever:
    """
    Retrieves relevant code files for context using ChromaDB vector search.
    Embeds files when written, allowing agents to access related parts of the codebase.
    """

    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.db_path = self.project_path / ".archon" / "chroma_db"
        self.initialized = False
        try:
            self._initialize_client()
        except Exception as e:
            # Handle common ChromaDB schema mismatch error by wiping and retrying
            if "no such column: collections.topic" in str(e) or "OperationalError" in str(e):
                logger.warning("ChromaDB schema mismatch detected. Wiping and recreating index...")
                import shutil

                if self.db_path.exists():
                    shutil.rmtree(self.db_path)
                try:
                    self._initialize_client()
                except Exception as retry_e:
                    logger.error(f"Failed to initialize ChromaDB after retry: {retry_e}")
            else:
                logger.error(f"Failed to initialize ChromaDB CodeRetriever: {e}")

    def _initialize_client(self):
        """Initialize the ChromaDB client and collection."""
        from chromadb.config import Settings

        self.client = chromadb.PersistentClient(
            path=str(self.db_path), settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="codebase_embeddings", metadata={"hnsw:space": "cosine"}
        )
        self.initialized = True
        logger.info("ChromaDB CodeRetriever initialized")

    def embed_file(self, file_path: str, content: str):
        """
        Embeds a source file into the vector index.
        """
        if not self.initialized or not content.strip():
            return

        try:
            self.collection.upsert(
                documents=[content], metadatas=[{"path": file_path}], ids=[file_path]
            )
            logger.debug(f"Embedded file into CodeRetriever index: {file_path}")
        except Exception as e:
            logger.error(f"Failed to embed file {file_path}: {e}")

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, str]]:
        """
        Retrieves the top_k relevant files based on the semantic query.
        """
        relevant_files = []
        if not self.initialized:
            return relevant_files

        try:
            results = self.collection.query(query_texts=[query], n_results=top_k)

            if (
                results
                and "documents" in results
                and results["documents"]
                and len(results["documents"]) > 0
            ):
                docs = results["documents"][0]
                metas = results["metadatas"][0]

                for doc, meta in zip(docs, metas):
                    relevant_files.append({"path": meta["path"], "content": doc})
        except Exception as e:
            logger.error(f"Failed to search CodeRetriever: {e}")

        return relevant_files
