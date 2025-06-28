#!/usr/bin/env python3
"""
RAG Chat Interface using Gradio.
This script loads the pre-built FAISS index and provides a chat interface
for querying design documents with semantic search and LLM synthesis.
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Protocol

import gradio as gr
import faiss
import pickle
import requests
from sentence_transformers import SentenceTransformer
import openai

# -----------------------------------------------------------------------------
# Configure logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Custom Exceptions
# -----------------------------------------------------------------------------
class RAGError(Exception):
    """Base exception for RAG system errors."""
    pass

class IndexNotFoundError(RAGError):
    """Raised when the FAISS index or metadata file is missing."""
    pass

class LLMClientError(RAGError):
    """Raised when LLM API calls fail."""
    pass

# -----------------------------------------------------------------------------
# Abstractions (Interface Segregation & Dependency Inversion)
# -----------------------------------------------------------------------------
class LLMClient(Protocol):
    """Protocol for LLM client implementations."""
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        ...

# -----------------------------------------------------------------------------
# Concrete LLM Clients
# -----------------------------------------------------------------------------
class OpenAIClient:
    """Client for OpenAI's ChatCompletion API."""
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo") -> None:
        openai.api_key = api_key
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            resp = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=1000,
                temperature=0.7,
            )
            return resp.choices[0].message.content.strip()

        except Exception as e:
            logger.error("OpenAI API call failed: %s", e)
            raise LLMClientError("OpenAI generation error") from e

class LocalLLMClient:
    """Client for local LLM endpoint (e.g., Ollama, LocalAI)."""
    def __init__(self, url: str, model: str) -> None:
        self.url = url.rstrip('/')
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 1000},
        }
        try:
            resp = requests.post(f"{self.url}/chat/completions", json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

        except requests.RequestException as e:
            logger.error("Local LLM connection failed: %s", e)
            raise LLMClientError("Local LLM generation error") from e

# -----------------------------------------------------------------------------
# RAG System Components
# -----------------------------------------------------------------------------
class EmbeddingModel:
    """Wrapper around SentenceTransformer."""
    def __init__(self, model_name: str):
        logger.info("Loading sentence transformer model: %s", model_name)
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: List[str]) -> Any:
        return self.model.encode(texts, convert_to_numpy=True)

class IndexStore:
    """Handles FAISS index and associated metadata."""
    def __init__(self, index_dir: Path):
        self.index_dir = index_dir
        self.index = self._load_faiss()
        self.metadata = self._load_metadata()

    def _load_faiss(self) -> faiss.Index:
        path = self.index_dir / "faiss_index.bin"
        if not path.exists():
            logger.error("FAISS index file missing: %s", path)
            raise IndexNotFoundError(f"Missing index file: {path}")
        logger.info("Loading FAISS index from %s", path)
        idx = faiss.read_index(str(path))
        logger.info("FAISS index loaded; total vectors=%d", idx.ntotal)
        return idx

    def _load_metadata(self) -> List[Dict[str, Any]]:
        path = self.index_dir / "metadata.pkl"
        if not path.exists():
            logger.error("Metadata file missing: %s", path)
            raise IndexNotFoundError(f"Missing metadata file: {path}")
        logger.info("Loading metadata from %s", path)
        with open(path, 'rb') as f:
            meta = pickle.load(f)
        logger.info("Metadata loaded; total chunks=%d", len(meta))
        return meta

class RetrievalService:
    """Performs semantic search over the FAISS index."""
    def __init__(self, embed_model: EmbeddingModel, store: IndexStore):
        self.embed_model = embed_model
        self.store = store

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        # Convert query to embedding
        emb = self.embed_model.encode([query]).astype('float32')
        distances, indices = self.store.index.search(emb, top_k)
        results = []
        for rank, (dist, idx) in enumerate(zip(distances[0], indices[0]), start=1):
            if 0 <= idx < len(self.store.metadata):
                chunk = dict(self.store.metadata[idx])
                chunk.update(distance=float(dist), rank=rank)
                results.append(chunk)
        return results

# -----------------------------------------------------------------------------
# RAG System Orchestrator
# -----------------------------------------------------------------------------
class RAGSystem:
    """Coordinates retrieval and LLM synthesis for user queries."""
    def __init__(
        self,
        index_dir: Path,
        embedding_model: EmbeddingModel,
        retrieval_service: RetrievalService,
        llm_client: LLMClient,
    ):
        self.store = retrieval_service.store
        self.retrieval = retrieval_service
        self.llm = llm_client
        logger.info("RAGSystem initialized with backend=%s", type(llm_client).__name__)

    def generate_response(
        self, query: str, top_k: int = 5
    ) -> Tuple[str, List[Dict[str, Any]]]:
        # Validate input
        if not query or not query.strip():
            raise ValueError("Query must be a non-empty string.")

        # Retrieve relevant chunks
        chunks = self.retrieval.retrieve(query, top_k)
        if not chunks:
            return "No relevant documents found for your query.", []

        # Assemble context
        context = "\n\n---\n\n".join(
            f"[{c['filename']} - {c['section_title']}]\n{c['text']}" for c in chunks
        )

        system_prompt = (
            "You are a helpful assistant that answers questions about design documents. "
            "Use the provided context... Always cite sources."
        )
        user_prompt = f"Context:\n{context}\n\nQuestion: {query}"  # concise prompt

        # Generate answer
        try:
            answer = self.llm.generate(system_prompt, user_prompt)
        except LLMClientError as e:
            logger.error("LLM generation failed: %s", e)
            answer = f"Error generating response: {e}"

        return answer, chunks

# -----------------------------------------------------------------------------
# Gradio Interface
# -----------------------------------------------------------------------------
class GradioInterface:
    """Web UI for interacting with the RAG system via Gradio."""
    def __init__(self, rag: RAGSystem):
        self.rag = rag
        self.chat_history: List[Dict[str, Any]] = []

    def process(self, query: str, top_k: int) -> Tuple[str, str, str]:
        if not query.strip():
            return "Please enter a question.", "", ""
        try:
            response, chunks = self.rag.generate_response(query, top_k)
            self.chat_history.append({"query": query, "chunks": len(chunks)})
            return response, self._format_context(chunks), self._format_details(chunks)
        except Exception as e:
            logger.error("Processing error: %s", e)
            return f"Error: {e}", "", ""

    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return "No context retrieved."
        lines = [f"{i+1}. {c['filename']} - {c['section_title']}" for i, c in enumerate(chunks)]
        return "**Retrieved Context:**\n" + "\n".join(lines)

    def _format_details(self, chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return ""
        parts = []
        for i, c in enumerate(chunks, start=1):
            parts.append(
                f"**Chunk {i}:** {c['filename']} ({c['section_title']}) - "
                f"Score: {c['distance']:.3f}\n{c['text'][:150]}..."
            )
        return "\n\n".join(parts)

    def launch(self) -> None:
        """Build and start the Gradio app."""
        with gr.Blocks(title="RAG Design Document Chat") as demo:
            gr.Markdown("# 🔍 RAG Design Document Chat")
            # Input components
            query = gr.Textbox(label="Your Question", lines=2)
            top_k = gr.Slider(minimum=1, maximum=10, step=1, value=5, label="Top K")
            submit = gr.Button("Ask")

            # Output components
            response = gr.Textbox(label="AI Response", interactive=False)
            context = gr.Markdown(label="Retrieved Context")
            details = gr.Markdown(label="Retrieval Details")

            submit.click(self.process, [query, top_k], [response, context, details])
            query.submit(self.process, [query, top_k], [response, context, details])

        demo.launch(server_name="0.0.0.0", server_port=7860, debug=False)

# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------
def main():
    index_dir = Path("index")
    if not index_dir.exists():
        raise IndexNotFoundError("Index directory does not exist.")

    # Initialize components with dependency injection
    embed_model = EmbeddingModel(model_name=os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2"))
    store = IndexStore(index_dir)
    retrieval = RetrievalService(embed_model, store)

    # Choose LLM client based on environment
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        llm_client = OpenAIClient(api_key)
    else:
        local_url = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/v1")
        local_model = os.getenv("LOCAL_LLM_MODEL", "llama2")
        llm_client = LocalLLMClient(local_url, local_model)

    # Compose RAG system and launch UI
    rag_system = RAGSystem(index_dir, embed_model, retrieval, llm_client)
    GradioInterface(rag_system).launch()


if __name__ == "__main__":
    main()
