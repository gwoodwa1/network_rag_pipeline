#!/usr/bin/env python3
"""
Build RAG index from Markdown design documents.
This script processes all .md files in 'output/', converts them to JSON-LD via
Panflute filters, extracts text chunks, and builds a FAISS vector index
for semantic search.
"""
import json
import logging
from pathlib import Path
from subprocess import CalledProcessError, run
from typing import Any, Dict, List

import faiss
import pickle
from sentence_transformers import SentenceTransformer

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Custom Exceptions
# -----------------------------------------------------------------------------
class BuildIndexError(Exception):
    """Base exception for index building errors."""
    pass

class FilterNotFoundError(BuildIndexError):
    """Raised when the Panflute filter script is missing."""
    pass

class PandocError(BuildIndexError):
    """Raised when pandoc subprocess fails."""
    pass

class IndexingError(BuildIndexError):
    """Raised when FAISS indexing or saving fails."""
    pass

# -----------------------------------------------------------------------------
# Markdown to JSON-LD Conversion
# -----------------------------------------------------------------------------
class MarkdownFilterRunner:
    """Runs pandoc with a Panflute filter to produce AST and JSON-LD."""

    def __init__(self, filter_script: Path):
        if not filter_script.is_file():
            raise FilterNotFoundError(f"Panflute filter not found: {filter_script}")
        self.filter_script = filter_script
        logger.info("Using Panflute filter: %s", filter_script)

    def generate_ast(self, md_path: Path, ast_path: Path) -> None:
        """Generate AST JSON using pandoc and verify output."""
        cmd = [
            'pandoc', str(md_path),
            '--filter', str(self.filter_script),
            '--to', 'json',
            '--output', str(ast_path)
        ]
        try:
            run(cmd, check=True, capture_output=True, text=True)
            # Validate generated AST
            _ = json.loads(ast_path.read_text(encoding='utf-8'))
            logger.info("AST generated: %s", ast_path.name)
        except CalledProcessError as e:
            logger.error("Pandoc AST conversion failed: %s", e.stderr)
            raise PandocError(f"Pandoc error for {md_path.name}") from e
        except json.JSONDecodeError as e:
            logger.error("Invalid AST JSON: %s", e)
            raise PandocError(f"Corrupt AST JSON for {md_path.name}") from e

    def extract_jsonld(self, md_path: Path) -> Dict[str, Any]:
        """Run Panflute filter in-process to extract JSON-LD from markdown."""
        try:
            import panflute as pf  # type: ignore
            import md2jsonld  # Panflute filter module

            text = md_path.read_text(encoding='utf-8')
            pf_output = pf.convert_text(text, input_format='markdown', output_format='panflute')
            doc = pf.Doc(*pf_output) if isinstance(pf_output, list) else pf_output
            doc.filename = md_path.name

            doc = md2jsonld.prepare(doc)
            doc.walk(md2jsonld.action, doc=doc)
            doc = md2jsonld.finalize(doc)

            first = doc.content[0]
            if isinstance(first, pf.RawBlock) and first.format == 'json':
                return json.loads(first.text)
            raise ValueError("Unexpected filter output format")

        except Exception as e:
            logger.warning("Filter extraction failed for %s: %s", md_path.name, e)
            # Fallback minimal JSON-LD structure
            return {
                '@context': {'@vocab': 'https://schema.org/'},
                '@graph': [{
                    '@type': 'Document',
                    '@id': md_path.stem,
                    'filename': md_path.name,
                    'title': md_path.stem,
                    'sections': []
                }]
            }

# -----------------------------------------------------------------------------
# Chunk Extraction
# -----------------------------------------------------------------------------
class ChunkExtractor:
    """Extracts text chunks from JSON-LD document graphs."""
    @staticmethod
    def extract(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []
        graph = data.get('@graph', [])
        # The first node is the Document
        doc = next((n for n in graph if n.get('@type') == 'Document'), {})
        base_info = {
            'doc_id':   doc.get('@id', ''),
            'filename': doc.get('filename', ''),
            'title':    doc.get('title', '')
        }

        # Subsequent nodes are Section objects
        for sec in graph:
            if sec.get('@type') != 'Section':
                continue
            text = sec.get('content', '').strip()
            if not text:
                continue

            chunks.append({
                **base_info,
                'section_id':    sec.get('@id', ''),
                'section_title': sec.get('title', ''),
                'level':         sec.get('level', 0),
                'text':          text,
                'primary':       sec.get('primary', False)   # preserve the flag
            })

        logger.info("Extracted %d chunks", len(chunks))
        return chunks
# -----------------------------------------------------------------------------
# FAISS Index Builder
# -----------------------------------------------------------------------------
class VectorIndexBuilder:
    """Builds and saves a FAISS index from text chunks."""

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        logger.info("Loading embedding model: %s", model_name)
        self.embedder = SentenceTransformer(model_name)
        self.dim = self.embedder.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatL2(self.dim)
        self.metadata: List[Dict[str, Any]] = []

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        if not chunks:
            return
        texts = [c['text'] for c in chunks]
        embeddings = self.embedder.encode(texts, convert_to_numpy=True)
        try:
            self.index.add(embeddings.astype('float32'))
            self.metadata.extend(chunks)
            logger.info("Indexed %d chunks", len(chunks))
        except Exception as e:
            logger.error("Failed to add embeddings: %s", e)
            raise IndexingError("Embedding addition failed") from e

    def save(self, directory: Path) -> None:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, str(directory / 'faiss_index.bin'))
            with open(directory / 'metadata.pkl', 'wb') as f:
                pickle.dump(self.metadata, f)
            info = {
                'dimension': self.dim,
                'chunks': len(self.metadata),
                'documents': len({m['doc_id'] for m in self.metadata})
            }
            with open(directory / 'info.json', 'w') as f:
                json.dump(info, f, indent=2)
            logger.info("Index saved (%d chunks, %d docs)",
                        info['chunks'], info['documents'])
        except Exception as e:
            logger.error("Failed to save index: %s", e)
            raise IndexingError("Index saving failed") from e

# -----------------------------------------------------------------------------
# Main Execution Flow
# -----------------------------------------------------------------------------
def main() -> None:
    input_dir = Path('output')
    proc_dir = Path('processed')
    index_dir = Path('index')
    proc_dir.mkdir(exist_ok=True)
    index_dir.mkdir(exist_ok=True)

    if not input_dir.is_dir():
        logger.error("Input directory 'output/' not found")
        return

    filter_runner = MarkdownFilterRunner(Path('md2jsonld.py'))
    extractor = ChunkExtractor()
    builder = VectorIndexBuilder()

    md_files = list(input_dir.glob('*.md'))
    logger.info("Found %d markdown files", len(md_files))

    for md in md_files:
        try:
            ast_path = proc_dir / f"{md.stem}.ast.json"
            filter_runner.generate_ast(md, ast_path)
            jsonld = filter_runner.extract_jsonld(md)
            jl_path = proc_dir / f"{md.stem}.jsonld"
            jl_path.write_text(json.dumps(jsonld, indent=2), encoding='utf-8')
        except BuildIndexError:
            logger.warning("Skipping file due to filter error: %s", md.name)
            continue

        chunks = extractor.extract(jsonld)
        try:
            builder.add_chunks(chunks)
        except IndexingError:
            logger.warning("Skipping indexing for file: %s", md.name)
            continue

    try:
        builder.save(index_dir)
        logger.info("Index build complete")
    except IndexingError:
        logger.error("Index build failed during save")


if __name__ == '__main__':
    main()
