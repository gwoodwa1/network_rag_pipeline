# RAG Network Documentation Toolkit

This repository provides a complete pipeline for processing Markdown-based network documentation, converting it into JSON-LD, indexing content for semantic search, and offering an interactive RAG (Retrieval-Augmented Generation) chat interface. By emitting JSON-LD, our documentation becomes immediately graph‑ready: you can ingest the output into any graph database (e.g., Neo4j, TigerGraph, Amazon Neptune) to perform advanced network analyses, visualize topology, and drive next‑generation knowledge applications.

---

## Table of Contents

1. [Why JSON‑LD for Network Docs?](#why-json-ld-for-network-docs)
2. [Key Features](#key-features)
3. [Architecture Overview](#architecture-overview)
4. [Project Structure](#project-structure)
5. [Installation](#installation)
6. [Usage Guide](#usage-guide)

   * [1. Prepare Markdown Files](#1-prepare-markdown-files)
   * [2. Convert to JSON‑LD](#2-convert-to-json-ld)
   * [3. Build FAISS Index](#3-build-faiss-index)
   * [4. Launch Chat Interface](#4-launch-chat-interface)
7. [JSON‑LD Output & Graph Import](#json-ld-output--graph-import)

   * [Sample JSON‑LD Document](#sample-json-ld-document)
   * [Ingesting into Neo4j](#ingesting-into-neo4j)
8. [Customization & Extensions](#customization--extensions)
9. [Troubleshooting & FAQs](#troubleshooting--faqs)
10. [Contributing](#contributing)
11. [License](#license)

---

## Why JSON‑LD for Network Docs?

Network documentation often consists of device lists, topologies, configuration snippets, and conceptual diagrams—scattered across multiple files. Traditional formats (plain Markdown, PDF, Word) lack standardized structure for machine processing. JSON‑LD (JSON for Linking Data) provides:

* **Semantic Structure**: An explicit graph model (`@context`, `@graph`) ties entities (devices, interfaces, subnets) to vocabularies (e.g., [schema.org](https://schema.org/), [NetworkVocabulary](https://example.org/network#)).
* **Interoperability**: JSON‑LD is supported by RDF tools, SPARQL engines, and graph databases.
* **Ease of Authoring**: Markdown authors can write in familiar syntax; our Panflute filter lifts semantics into JSON‑LD.
* **Graph-Ready**: Outputs map directly to nodes/relationships—no ETL gymnastics.

## Key Features

* **Panflute Filter (`md2jsonld.py`)** converts Markdown to JSON‑LD, preserving frontmatter metadata, sections, code blocks, tables, images, and lists.
* **Chunk Extraction & FAISS Indexing** (`build_index.py`): Breaks JSON‑LD sections into text chunks, computes embeddings with SentenceTransformers, and builds a FAISS vector index for semantic retrieval.
* **Interactive RAG Chat** (`rag_chat.py`): Gradio-based UI to ask natural language questions about your network docs, retrieving relevant chunks and synthesizing answers via OpenAI or local LLMs.
* **Graph Database Integration**: JSON‑LD outputs are ready for Cypher, Gremlin, or SPARQL imports with minimal transformation.

## Architecture Overview

```text
+-----------------+       +----------------+       +----------------------+       +----------------+
| Markdown Files  |  →    | md2jsonld.py   |  →    | JSON‑LD Documents   |  →    | Chunk Extractor|
| (network.md)    |       +----------------+       +----------------------+       +----------------+
| - frontmatter   |                              
| - sections      |                              
+-----------------+                                              |                      
                                                                 ▼                     
                                                              +----------------+        
                                                              | VectorIndex     |        
                                                      +------>| Builder         |        
                                                      |       +----------------+        
                                                      |                             
                                                      ▼                             
                                                +-----------------+                
                                                | FAISS Index      |                
                                                +-----------------+                
                                                      |                             
                                                      ▼                             
                                               +------------------+               
                                               | Gradio Chat UI   |               
                                               | (RAG System)     |               
                                               +------------------+               
                                                      |                             
                                                      ▼                             
                                             +---------------------+             
                                             | Graph DB Ingestion  |             
                                             | (Neo4j, etc.)       |             
                                             +---------------------+             
```

## Project Structure

```
├── md2jsonld.py        ← Panflute filter: Markdown → JSON‑LD
├── build_index.py      ← Processes JSON‑LD → text chunks → FAISS index
├── rag_chat.py         ← Gradio RAG chat interface over FAISS index
├── output/             ← Your raw `.md` network documentation
├── processed/          ← Generated `.jsonld`, `.ast.json` files
├── index/              ← Saved FAISS index, metadata, and info
└── README.md           ← This documentation
```

## Installation

1. **Clone the repo**:

   ```bash
   git clone https://github.com/your-org/network-docs-rag.git
   cd network-docs-rag
   ```

2. **Python & venv**:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

3. **Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

   > *requirements.txt should include:*
   >
   > ```text
   > panflute
   > pandoc
   > sentence-transformers
   > faiss-cpu
   > gradio
   > openai
   > requests
   > ```

4. **Pandoc & Panflute**:

   * Ensure `pandoc` is installed and on your `$PATH`.
   * Confirm `md2jsonld.py` is executable:

     ```bash
     chmod +x md2jsonld.py
     ```

## Usage Guide

### 1. Prepare Markdown Files

Place all your network documentation in Markdown under the `output/` directory. Example frontmatter:

```markdown
---
id: network-architecture
title: "Corporate Network Overview"
description: "High-level topology, device configs, and VLAN assignments"
author: "NetOps Team"
date: "2025-06-01"
---

# Core Switches

Details about switch models, uplink ports, etc.
```

### 2. Convert to JSON‑LD

Run the Panflute filter and generate AST to catch errors:

```bash
python3 build_index.py
```

> This step invokes `md2jsonld.py` internally, producing JSON-LD (`processed/*.jsonld`) and AST dumps (`processed/*.ast.json`).

### 3. Build FAISS Index

The same `build_index.py` script will:

1. Read each `.jsonld` file.
2. Extract text chunks per section.
3. Compute embeddings and build a FAISS index.
4. Save index, metadata, and `info.json` under `index/`.

### 4. Launch Chat Interface

Interactively query your docs:

```bash
python3 rag_chat.py
```

* **OpenAI**: Set `OPENAI_API_KEY` env var to use OpenAI.
* **Local LLM**: Set `LOCAL_LLM_URL` & `LOCAL_LLM_MODEL` to point at Ollama/LocalAI.

Access the Gradio URL shown in terminal to ask natural-language questions and receive source‑cited answers.

## JSON‑LD Output & Graph Import

Your `processed/*.jsonld` files follow this structure:

```jsonld
{
  "@context": {
    "@vocab": "https://schema.org/",
    "sections": { "@container": "@list" }
  },
  "@graph": [
    {
      "@type": "Document",
      "@id": "network-architecture",
      "filename": "network.md",
      "title": "Corporate Network Overview",
      "description": "High-level topology...",
      "dateCreated": "2025-06-01",
      "author": "NetOps Team",
      "sections": [
        {
          "@type": "Section",
          "@id": "network-architecture-sec-1-core-switches",
          "title": "Core Switches",
          "level": 1,
          "content": "Details about switch models..."
        }
      ]
    }
  ]
}
```

### Ingesting into Neo4j

1. **Install APOC** plugin.
2. **Load JSON-LD** via Cypher:

   ```cypher
   CALL apoc.load.json("file:///processed/network.jsonld") YIELD value
   UNWIND value['@graph'] AS doc
   MERGE (d:Document {id: doc['@id']})
   SET d.title = doc.title, d.description = doc.description
   
   UNWIND doc.sections AS sec
   MERGE (s:Section {id: sec['@id']})
   SET s.title = sec.title, s.content = sec.content
   MERGE (d)-[:HAS_SECTION]->(s);
   ```

3. **Explore**: Run graph queries, visualize topologies, or connect sections to device nodes in your network graph.

## Customization & Extensions

- **Custom Context**: Modify `@context` in `md2jsonld.py` to map to your network ontology (e.g., Cisco IOS, `netconf:Interface`).  
- **Additional Elements**: Extend `action()` to handle custom Panflute elements (e.g., diagrams, YAML code blocks).  
- **Alternative Embeddings**: Swap out the SentenceTransformer model in `build_index.py` for domain‑specific embeddings.  
- **Graph DB Plugins**: Provide scripts for Amazon Neptune's bulk loader or JanusGraph's TinkerPop loader.

## Troubleshooting & FAQs

- **JSON-LD generation fails**: Check `processed/*.ast.json` for pandoc errors.  
- **No chunks indexed**: Ensure your sections contain non-empty content.  
- **LLM errors**: Verify your API key or local LLM endpoint is reachable.  
- **Graph import issues**: Confirm file paths and APOC plugin availability.

## Contributing

1. Fork the repo.  
2. Create a feature branch (`git checkout -b feature/my-feature`).  
3. Commit your changes (`git commit -m 'Add new feature'`).  
4. Push to the branch (`git push origin feature/my-feature`).  
5. Open a Pull Request.

Please adhere to our code style, include tests for new functionality, and update documentation accordingly.

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.
