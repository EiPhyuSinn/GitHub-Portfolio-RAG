# GitHub Portfolio RAG System

A comprehensive Retrieval-Augmented Generation (RAG) system for indexing and searching GitHub portfolio projects using hybrid search with automated evaluation and web interface.

## Architecture Overview

The system combines multiple technologies to create an intelligent code analysis platform:

- **LangChain**: Core framework for RAG pipeline and LLM integration
- **Database**: PostgreSQL 16 with pgvector extension for embeddings and full-text search
- **LLM**: Groq API (Llama 3.1) with intelligent rate limiting and response caching
- **Embeddings**: Local sentence-transformers (all-MiniLM-L6-v2) for semantic search
- **Web Interface**: Flask-based UI with real-time chat and repository management
- **Deployment**: Docker Compose for containerized services

## Key Features

- **GitHub Repository Ingestion**: Automatically fetches and processes README files and code structure
- **Hybrid Search**: Combines vector similarity search with BM25 keyword search using Reciprocal Rank Fusion
- **Intelligent Rate Limiting**: Handles Groq API limits with 2-second intervals and 1-hour response caching
- **Automated Evaluation**: Faithfulness scoring and performance metrics tracking
- **Web Interface**: Modern chat-based UI for querying and repository management
- **Real-time Statistics**: Live dashboard showing document counts, query metrics, and response times

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GitHub API    │    │   Flask Web UI   │    │   PostgreSQL    │
│                 │    │                  │    │   + pgvector    │
│  Repository     │────│  Chat Interface  │────│  Document Store │
│  Ingestion      │    │  Repo Management │    │  Embeddings     │
│                 │    │  Search UI       │    │  Metrics        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  LangChain      │    │   Groq API       │    │   Grafana       │
│  RAG Pipeline   │    │                  │    │   Dashboard     │
│  Hybrid Search  │────│  Llama 3.1 LLM   │────│  Monitoring     │
│  Prompt         │    │  Rate Limiting   │    │  Analytics      │
│  Engineering    │    │  Response Cache  │    │  Performance    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 16 with pgvector
- Docker & Docker Compose
- Groq API key
- (Optional) GitHub token for higher rate limits

### Installation

1. **Clone and Setup Environment**
   ```bash
   git clone <repository-url>
   cd GitHub-Portfolio-RAG
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Database Setup**
   ```bash
   # Start PostgreSQL with Docker
   docker compose up -d postgres
   
   # Initialize database schema
   psql -h localhost -U postgres -d rag_portfolio -f schema.sql
   ```

3. **Python Environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements_flask.txt
   ```

### Usage

#### 1. Start the Web Interface
```bash
python flask_app.py
```
Access at: http://localhost:5000

#### 2. Ingest Repositories
```bash
# Ingest a specific repository
python ingest.py https://github.com/username/repository

# Or use the web interface to add repositories
```

#### 3. Query the System
```bash
# Command line interface
python -c "
from rag_chain import RAGChain
rag = RAGChain()
result = rag.ask_sensei('What are the main components of this project?')
print(result['response'])
"
```

## Web Interface

The Flask web application provides a complete user interface for interacting with the RAG system:

### Features
- **Chat Interface**: Natural language queries with contextual responses
- **Repository Management**: Add and manage GitHub repositories
- **Document Search**: Direct search through indexed content
- **Real-time Statistics**: Live metrics and performance data
- **Error Handling**: Comprehensive error reporting

### UI Components

![Web Interface](images/web_interface.png)
*Figure 1: Web interface showing chat, statistics, and repository management*

### Command Line Interface

```bash
# Example ingestion session
$ python ingest.py https://github.com/EiPhyuSinn/Evaluating-RAG-CourseFAQs
Loading repository information...
Processing README.md...
Chunking content...
Generating embeddings...
Storing in database...
✅ Ingestion completed: 12 documents added

# Example query session
$ python -c "
from rag_chain import RAGChain
rag = RAGChain()
result = rag.ask_sensei('Explain the evaluation methodology')
print(result['response'])
"
Retrieving context for: 'Explain the evaluation methodology'
Hybrid search completed in 0.892 seconds
Found 5 relevant documents
Calling Groq API...
Response time: 2.34 seconds

Response: The evaluation methodology uses RAGAS (Retrieval-Augmented 
Generation Assessment Score) framework with four key metrics:
1. Faithfulness Score: Measures factual consistency between generated
   response and retrieved context
2. Answer Relevancy: Evaluates how relevant the answer is to the question
3. Context Precision: Measures signal-to-noise ratio in retrieved context
4. Context Recall: Assesses completeness of retrieved context

The system implements automated scoring through semantic similarity
comparisons and provides detailed performance analytics.
```

![Command Line Interface](images/cli_output.png)
*Figure 2: Command line interface showing repository ingestion and querying*

## Grafana Monitoring

The RAG system includes real-time monitoring with Grafana dashboard to track performance metrics and system health.

### Accessing Grafana

1. **Start Services**:
   ```bash
   docker compose up -d postgres grafana
   ```

2. **Access Grafana**:
   - **URL**: http://localhost:3000
   - **Login**: admin / admin

3. **Configure Data Source**:
   - Go to **Configuration → Data Sources**
   - Select **PostgreSQL**
   - Set **Host**: `postgres:5432`
   - **Database**: `rag_portfolio`
   - **User**: `postgres`
   - **Password**: `password`
   - **Save & Test**

4. **Import Dashboard**:
   - Go to **Dashboards → Import**
   - Upload `grafana_dashboard.json`
   - Select PostgreSQL data source
   - Click **Import**

### Dashboard Features

The Grafana dashboard provides real-time monitoring of:

- **Response Latency**: Track LLM response times over time
- **Faithfulness Score**: Monitor answer quality metrics
- **Query Volume**: Track system usage patterns
- **Document Count**: Monitor repository ingestion status

### Setting Up Monitoring

![Grafana PostgreSQL Setup](images/grafana_explore_postgresql.png)
*Figure 3: Configuring PostgreSQL data source in Grafana*

![Grafana Dashboard](images/grafana_daashboard.png)
*Figure 4: Real-time RAG system monitoring dashboard*

### Dashboard Queries

The dashboard uses these key SQL queries:

```sql
-- Response Latency
SELECT timestamp AT TIME ZONE 'UTC' AS time, response_latency_ms AS value 
FROM metrics 
WHERE response_latency_ms IS NOT NULL 
ORDER BY timestamp

-- Faithfulness Score
SELECT AVG(faithfulness_score) as value 
FROM metrics 
WHERE faithfulness_score IS NOT NULL

-- Query Volume
SELECT DATE_TRUNC('hour', timestamp AT TIME ZONE 'UTC') AS time, COUNT(*) AS value 
FROM metrics 
GROUP BY 1 
ORDER BY 1

-- Document Count
SELECT COUNT(*) as value 
FROM documents
```

### Real-time Updates

The dashboard automatically refreshes every 5 seconds, providing:
- **Live performance metrics**
- **Query response tracking**
- **System health monitoring**
- **Usage analytics**

## API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Submit questions to RAG system |
| `/api/search` | POST | Search documents directly |
| `/api/ingest` | POST | Ingest new repository |
| `/api/stats` | GET | Get system statistics |
| `/api/repositories` | GET | List ingested repositories |

### Python API

```python
from rag_chain import RAGChain
from search import HybridSearch
from ingest import GitHubDataLoader

# Initialize components
rag = RAGChain()
searcher = HybridSearch()
loader = GitHubDataLoader()

# Query the system
result = rag.ask_sensei('What technologies are used?')

# Search documents
results = searcher.hybrid_search('machine learning', limit=10)

# Ingest repository
loader.ingest_repository('https://github.com/user/repo')
```


## Configuration

### Environment Variables

```bash
# Required
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://postgres:password@localhost:5432/rag_portfolio

# Optional
GITHUB_TOKEN=your_github_token_here
```

### Rate Limiting Configuration

```python
# In rag_chain.py
self.min_call_interval = 2.0  # seconds between Groq calls
self.cache_ttl = 3600         # 1 hour cache TTL
```

## Troubleshooting

### Common Issues

1. **Groq API Access Denied**
   - Check VPN/firewall settings
   - Verify API key validity
   - Ensure proper network connectivity

2. **Database Connection Errors**
   - Confirm PostgreSQL is running
   - Check DATABASE_URL format
   - Verify pgvector extension is installed

3. **Empty Search Results**
   - Ensure repositories are ingested
   - Check document indexing status
   - Verify search query relevance

### Debug Commands

```bash
# Test database connection
python test_connection.py

# Test Groq API
python -c "
from langchain_groq import ChatGroq
llm = ChatGroq(groq_api_key='your_key', model_name='llama-3.1-8b-instant')
print(llm.invoke('Hello').content)
"

# Check database contents
python -c "
from search import HybridSearch
searcher = HybridSearch()
conn = searcher.get_connection()
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM documents')
print(f'Documents: {cursor.fetchone()[0]}')
conn.close()
"
```

## Development

### Project Structure

```
GitHub-Portfolio-RAG/
├── flask_app.py              # Web application server
├── templates/
│   └── index.html           # Web interface template
├── rag_chain.py             # RAG pipeline implementation
├── search.py                # Hybrid search engine
├── ingest.py                # GitHub repository ingestion
├── schema.sql               # Database schema
├── docker-compose.yml       # Container orchestration
├── requirements_flask.txt    # Python dependencies
└── .env.example            # Environment configuration
```
