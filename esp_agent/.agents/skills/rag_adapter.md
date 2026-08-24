# Skill: RAG Adapter

## Purpose
Searches domain documentation (operating manuals, troubleshooting guides, maintenance SOPs) using vector embeddings and similarity search.

## Inputs
- `query`: Search query or symptom description.
- `top_k`: Number of passages to retrieve.

## Outputs
- List of relevant document chunks with source file citations and relevance scores.
