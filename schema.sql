-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table for storing GitHub content
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_url VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    embedding vector(384), -- all-MiniLM-L6-v2 dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(repo_url, file_path, chunk_index)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_repo_url ON documents(repo_url);
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Metrics table for RAG evaluation
CREATE TABLE IF NOT EXISTS metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT NOT NULL,
    retrieved_context TEXT[],
    llm_response TEXT NOT NULL,
    faithfulness_score FLOAT CHECK (faithfulness_score >= 0 AND faithfulness_score <= 1),
    response_latency_ms INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for metrics
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_faithfulness ON metrics(faithfulness_score);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_documents_content_fts ON documents USING GIN(to_tsvector('english', content));
