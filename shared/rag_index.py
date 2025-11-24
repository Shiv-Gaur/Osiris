"""RAG index helper for Osiris Command R.

This module builds a small Chroma + llama-index vector index over
project documentation so Command R can retrieve relevant context.

The rest of the system is optional: if building the index fails,
callers should handle a None return value gracefully.
"""

from pathlib import Path
from typing import List, Optional

import chromadb
from llama_index.core import VectorStoreIndex, Document, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore


def build_osiris_index() -> Optional[VectorStoreIndex]:
    """Build a llama-index + Chroma index over key Osiris docs.

    Returns a VectorStoreIndex, or None if something goes wrong.
    """
    root = Path(__file__).parent.parent
    sources = [
        root / "README.md",
        root / "iris_cli_framework" / "COMPONENT_EXPLANATION.md",
        root / "shiv_command_execution" / "COMPONENT_EXPLANATION.md",
        root / "kshitij_safety_gate" / "COMPONENT_EXPLANATION.md",
        root / "prabal_efficiency_metrics" / "COMPONENT_EXPLANATION.md",
    ]

    documents: List[Document] = []
    for path in sources:
        if path.exists():
            try:
                documents.append(
                    Document(
                        text=path.read_text(encoding="utf-8"),
                        metadata={"source": str(path)},
                    )
                )
            except Exception:
                continue

    if not documents:
        return None

    try:
        client = chromadb.Client()
        collection = client.get_or_create_collection("osiris-command-r")
        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        index = VectorStoreIndex.from_documents(
            documents, storage_context=storage_context
        )
        return index
    except Exception:
        # RAG is optional; surface no hard failure
        return None
