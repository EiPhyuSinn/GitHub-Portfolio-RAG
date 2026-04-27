#!/usr/bin/env python3
"""
Phase 3: Local Embeddings & Hybrid Search
Implements hybrid search with vector similarity + keyword search using RRF.
"""

import os
import time
from typing import List, Dict, Any, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class HybridSearch:
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/rag_portfolio")
        
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for search query"""
        return self.embedding_model.encode(query, convert_to_numpy=True).tolist()
    
    def vector_search(self, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Perform vector similarity search"""
        query_vector = np.array(query_embedding, dtype=np.float32).tolist()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Vector similarity search using cosine distance
            sql = """
                SELECT 
                    id,
                    repo_url,
                    file_path,
                    content,
                    chunk_index,
                    1 - (embedding <=> %s::vector) as similarity_score
                FROM documents
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            
            cursor.execute(sql, (query_vector, query_vector, limit))
            results = cursor.fetchall()
            
            return [dict(row) for row in results]
    
    def keyword_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform keyword-based full-text search"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Full-text search using tsvector
            sql = """
                SELECT 
                    id,
                    repo_url,
                    file_path,
                    content,
                    chunk_index,
                    ts_rank(to_tsvector('english', content), plainto_tsquery('english', %s)) as keyword_score
                FROM documents
                WHERE to_tsvector('english', content) @@ plainto_tsquery('english', %s)
                ORDER BY keyword_score DESC
                LIMIT %s
            """
            
            cursor.execute(sql, (query, query, limit))
            results = cursor.fetchall()
            
            return [dict(row) for row in results]
    
    def reciprocal_rank_fusion(self, vector_results: List[Dict], keyword_results: List[Dict], k: int = 60) -> List[Dict[str, Any]]:
        """
        Combine results using Reciprocal Rank Fusion (RRF)
        RRF_score = sum(1 / (k + rank_i)) for each result i
        """
        # Create score dictionaries
        rrf_scores = {}
        result_info = {}
        
        # Add vector search results
        for rank, result in enumerate(vector_results, 1):
            doc_id = result['id']
            score = 1.0 / (k + rank)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + score
            result_info[doc_id] = result
        
        # Add keyword search results
        for rank, result in enumerate(keyword_results, 1):
            doc_id = result['id']
            score = 1.0 / (k + rank)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + score
            if doc_id not in result_info:
                result_info[doc_id] = result
        
        # Sort by RRF score
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Combine with original result info
        final_results = []
        for doc_id, rrf_score in sorted_results:
            result = result_info[doc_id].copy()
            result['rrf_score'] = rrf_score
            final_results.append(result)
        
        return final_results
    
    def hybrid_search(self, query: str, limit: int = 10, vector_weight: float = 0.5) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector similarity and keyword search
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            vector_weight: Weight for vector search (0.0 to 1.0)
        
        Returns:
            List of search results with combined scores
        """
        print(f"Performing hybrid search for: '{query}'")
        start_time = time.time()
        
        # Generate query embedding
        query_embedding = self.embed_query(query)
        
        # Perform both searches
        vector_results = self.vector_search(query_embedding, limit * 2)
        keyword_results = self.keyword_search(query, limit * 2)
        
        # Combine using RRF
        combined_results = self.reciprocal_rank_fusion(vector_results, keyword_results)
        
        # Limit results
        final_results = combined_results[:limit]
        
        end_time = time.time()
        print(f"Hybrid search completed in {end_time - start_time:.3f} seconds")
        print(f"Found {len(final_results)} results")
        
        return final_results
    
    def get_context_for_query(self, query: str, max_context_length: int = 2000) -> str:
        """
        Get formatted context for RAG from search results
        
        Args:
            query: Search query
            max_context_length: Maximum length of context string
        
        Returns:
            Formatted context string
        """
        results = self.hybrid_search(query, limit=5)
        
        context_parts = []
        current_length = 0
        
        for result in results:
            content = result['content']
            file_path = result['file_path']
            repo_url = result['repo_url']
            
            # Format context piece
            context_piece = f"From {repo_url} ({file_path}):\n{content}\n"
            
            # Check if adding this would exceed the limit
            if current_length + len(context_piece) > max_context_length:
                break
            
            context_parts.append(context_piece)
            current_length += len(context_piece)
        
        return "\n".join(context_parts)


if __name__ == "__main__":
    # Test the hybrid search
    searcher = HybridSearch()
    
    # Test query
    test_query = "vector database implementation"
    results = searcher.hybrid_search(test_query, limit=5)
    
    print(f"\nSearch Results for: '{test_query}'")
    print("=" * 50)
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['repo_url']} ({result['file_path']})")
        print(f"   Score: {result['rrf_score']:.4f}")
        print(f"   Content: {result['content'][:100]}...")
    
    # Test context generation
    context = searcher.get_context_for_query(test_query)
    print(f"\nGenerated Context:")
    print("=" * 50)
    print(context[:500] + "..." if len(context) > 500 else context)
