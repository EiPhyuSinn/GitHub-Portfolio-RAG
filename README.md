# GitHub Portfolio RAG System

A LangChain-powered RAG system for indexing and searching GitHub portfolio projects using hybrid search (vector + BM25) with automated evaluation and rate limit handling.

## Architecture

- **LangChain**: Core framework for RAG pipeline
- **Database**: PostgreSQL 16 with pgvector for embeddings and full-text search
- **LLM**: Groq API (Llama 3.1) with rate limiting and caching
- **Embeddings**: Local sentence-transformers (all-MiniLM-L6-v2)
- **Monitoring**: Grafana dashboard with faithfulness scoring
- **Deployment**: Docker Compose

## Features

- GitHub repository ingestion (README + file structure)
- Hybrid search with Reciprocal Rank Fusion (RRF)
- Rate-limited Groq integration with response caching
- Automated faithfulness evaluation and metrics tracking
- Real-time performance monitoring with Grafana

## Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Add your API keys to .env
# GROQ_API_KEY=your_groq_api_key_here
# GITHUB_TOKEN=your_github_token_here (optional)
```

### 2. Start Docker Services

```bash
# Start PostgreSQL and Grafana
docker-compose up -d

# Initialize database schema
docker-compose exec postgres psql -U postgres -d rag_portfolio -f /docker-entrypoint-initdb.d/schema.sql
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Ingest GitHub Repository

```bash
# Ingest a repository
python ingest.py

# Or ingest a specific repo
python -c "
from ingest import GitHubDataLoader
loader = GitHubDataLoader()
loader.ingest_repository('https://github.com/langchain-ai/langchain')
"
```

### 5. Ask Questions

```bash
# Basic RAG query
python -c "
from rag_chain import RAGChain
rag = RAGChain()
result = rag.ask_sensei('What are the main components of this project?')
print(result['response'])
"

# With evaluation
python -c "
from evaluate import EvaluatedRAGChain
rag = EvaluatedRAGChain()
result = rag.ask_and_evaluate('How is the database structured?')
print(f'Score: {result[\"faithfulness_score\"]:.3f}')
print(result['response'])
"
```

## Project Structure

```
rag_project/
├── docker-compose.yml      # PostgreSQL + Grafana
├── requirements.txt         # LangChain dependencies
├── schema.sql              # Database schema
├── .env.example           # Environment template
├── ingest.py              # GitHub data loader
├── search.py              # Hybrid search with RRF
├── rag_chain.py           # Groq RAG with rate limiting
└── evaluate.py            # Metrics and evaluation
```

## Components

### Phase 1: Docker Environment
- PostgreSQL 16 with pgvector extension
- Grafana for monitoring
- Health checks and proper networking

### Phase 2: GitHub Data Loader
- Fetches README.md and file tree via GitHub API
- Chunks content with RecursiveCharacterTextSplitter (500 chars, 50 overlap)
- Generates embeddings with all-MiniLM-L6-v2

### Phase 3: Hybrid Search
- Vector similarity search using pgvector
- Keyword-based full-text search
- Reciprocal Rank Fusion (RRF) for result combination

### Phase 4: RAG Chain
- LangChain integration with Groq
- Rate limiting (2s between calls)
- Response caching (1 hour TTL)
- Project analysis prompts

### Phase 5: Evaluation
- Faithfulness scoring based on term overlap
- Response latency tracking
- Metrics storage in PostgreSQL
- Grafana dashboard integration

## Access Points

- **PostgreSQL**: localhost:5432
- **Grafana**: http://localhost:3000 (admin/admin)
- **Database**: rag_portfolio

## Monitoring with Grafana

Once data is flowing into the `metrics` table, create these panels:

1. **Avg Faithfulness**: Gauge showing average RAG answer quality
2. **Request Volume**: Time series of Groq API calls
3. **Top Projects Queried**: Bar chart of most-asked repositories

## Performance Tips

- Embed once, reuse: Data is embedded during ingestion and stored
- Small model: all-MiniLM-L6-v2 is efficient for CPU-only systems
- Rate limiting: Built-in 2s delays prevent hitting Groq limits
- Caching: 1-hour response cache reduces redundant API calls

## Example Queries

```python
# Architecture questions
"What design patterns are used?"
"How is the data flow organized?"

# Technical questions
"What databases are used?"
"Which programming languages?"

# Improvement questions
"What are potential optimizations?"
"How could scalability be improved?"
