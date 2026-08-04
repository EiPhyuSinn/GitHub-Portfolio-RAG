#!/usr/bin/env python3
"""
Retrieval Evaluation: Compare multiple retrieval approaches
Evaluates vector-only, keyword-only, and hybrid search performance.
"""

import os
import time
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from search import HybridSearch

load_dotenv()

class RetrievalEvaluator:
    def __init__(self):
        self.searcher = HybridSearch()
        self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/rag_portfolio")
        
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
    
    def evaluate_vector_search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Evaluate vector-only search"""
        start_time = time.time()
        query_embedding = self.searcher.embed_query(query)
        results = self.searcher.vector_search(query_embedding, limit)
        end_time = time.time()
        
        return {
            "method": "vector_only",
            "query": query,
            "results_count": len(results),
            "latency_ms": int((end_time - start_time) * 1000),
            "results": results
        }
    
    def evaluate_keyword_search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Evaluate keyword-only search"""
        start_time = time.time()
        results = self.searcher.keyword_search(query, limit)
        end_time = time.time()
        
        return {
            "method": "keyword_only",
            "query": query,
            "results_count": len(results),
            "latency_ms": int((end_time - start_time) * 1000),
            "results": results
        }
    
    def evaluate_hybrid_search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Evaluate hybrid search"""
        start_time = time.time()
        results = self.searcher.hybrid_search(query, limit)
        end_time = time.time()
        
        return {
            "method": "hybrid",
            "query": query,
            "results_count": len(results),
            "latency_ms": int((end_time - start_time) * 1000),
            "results": results
        }
    
    def calculate_relevance_score(self, results: List[Dict], query: str) -> float:
        """
        Calculate a simple relevance score based on keyword overlap
        This is a basic metric - in production, use human evaluation or more sophisticated metrics
        """
        if not results:
            return 0.0
        
        query_terms = set(query.lower().split())
        total_relevance = 0.0
        
        for result in results:
            content = result.get('content', '').lower()
            content_terms = set(content.split())
            overlap = len(query_terms.intersection(content_terms))
            relevance = overlap / len(query_terms) if query_terms else 0
            total_relevance += relevance
        
        return total_relevance / len(results)
    
    def compare_approaches(self, queries: List[str]) -> Dict[str, Any]:
        """
        Compare all retrieval approaches across multiple queries
        
        Returns:
            Dictionary with comparison results and recommendations
        """
        print("=" * 60)
        print("Retrieval Approach Comparison")
        print("=" * 60)
        
        all_results = {
            "vector_only": [],
            "keyword_only": [],
            "hybrid": []
        }
        
        for query in queries:
            print(f"\nQuery: '{query}'")
            print("-" * 40)
            
            # Evaluate each approach
            vector_result = self.evaluate_vector_search(query)
            keyword_result = self.evaluate_keyword_search(query)
            hybrid_result = self.evaluate_hybrid_search(query)
            
            # Calculate relevance scores
            vector_result['relevance_score'] = self.calculate_relevance_score(vector_result['results'], query)
            keyword_result['relevance_score'] = self.calculate_relevance_score(keyword_result['results'], query)
            hybrid_result['relevance_score'] = self.calculate_relevance_score(hybrid_result['results'], query)
            
            # Store results
            all_results["vector_only"].append(vector_result)
            all_results["keyword_only"].append(keyword_result)
            all_results["hybrid"].append(hybrid_result)
            
            # Print comparison
            print(f"Vector-only:   {vector_result['results_count']} results, {vector_result['latency_ms']}ms, relevance: {vector_result['relevance_score']:.3f}")
            print(f"Keyword-only:  {keyword_result['results_count']} results, {keyword_result['latency_ms']}ms, relevance: {keyword_result['relevance_score']:.3f}")
            print(f"Hybrid:        {hybrid_result['results_count']} results, {hybrid_result['latency_ms']}ms, relevance: {hybrid_result['relevance_score']:.3f}")
        
        # Calculate aggregate statistics
        summary = self.calculate_summary(all_results)
        
        # Determine best approach
        best_approach = self.determine_best_approach(summary)
        
        print("\n" + "=" * 60)
        print("Summary Statistics")
        print("=" * 60)
        for method, stats in summary.items():
            print(f"\n{method}:")
            print(f"  Avg results: {stats['avg_results']:.1f}")
            print(f"  Avg latency: {stats['avg_latency_ms']:.1f}ms")
            print(f"  Avg relevance: {stats['avg_relevance']:.3f}")
        
        print("\n" + "=" * 60)
        print(f"Recommended Approach: {best_approach}")
        print("=" * 60)
        
        return {
            "detailed_results": all_results,
            "summary": summary,
            "recommended_approach": best_approach
        }
    
    def calculate_summary(self, all_results: Dict[str, List[Dict]]) -> Dict[str, Dict]:
        """Calculate summary statistics for each approach"""
        summary = {}
        
        for method, results in all_results.items():
            if not results:
                continue
            
            avg_results = sum(r['results_count'] for r in results) / len(results)
            avg_latency = sum(r['latency_ms'] for r in results) / len(results)
            avg_relevance = sum(r['relevance_score'] for r in results) / len(results)
            
            summary[method] = {
                "avg_results": avg_results,
                "avg_latency_ms": avg_latency,
                "avg_relevance": avg_relevance
            }
        
        return summary
    
    def determine_best_approach(self, summary: Dict[str, Dict]) -> str:
        """
        Determine the best approach based on a weighted score
        Weigh relevance higher than latency
        """
        best_method = None
        best_score = -1
        
        for method, stats in summary.items():
            # Weighted score: 70% relevance, 30% speed (inverse of latency)
            # Normalize latency (lower is better)
            max_latency = max(s['avg_latency_ms'] for s in summary.values())
            speed_score = 1 - (stats['avg_latency_ms'] / max_latency) if max_latency > 0 else 1
            
            combined_score = (stats['avg_relevance'] * 0.7) + (speed_score * 0.3)
            
            if combined_score > best_score:
                best_score = combined_score
                best_method = method
        
        return best_method
    
    def log_evaluation_results(self, comparison_results: Dict[str, Any]):
        """Log evaluation results to database for tracking"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for method, results in comparison_results['detailed_results'].items():
                    for result in results:
                        sql = """
                            INSERT INTO retrieval_evaluations 
                            (method, query, results_count, latency_ms, relevance_score, timestamp)
                            VALUES (%s, %s, %s, %s, %s, NOW())
                        """
                        cursor.execute(sql, (
                            method,
                            result['query'],
                            result['results_count'],
                            result['latency_ms'],
                            result['relevance_score']
                        ))
                
                conn.commit()
                print("\nEvaluation results logged to database")
                
        except Exception as e:
            print(f"Error logging evaluation results: {e}")
            # Create table if it doesn't exist
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS retrieval_evaluations (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            method VARCHAR(50) NOT NULL,
                            query TEXT NOT NULL,
                            results_count INTEGER NOT NULL,
                            latency_ms INTEGER NOT NULL,
                            relevance_score FLOAT NOT NULL,
                            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        )
                    """)
                    conn.commit()
                    print("Created retrieval_evaluations table")
            except Exception as e2:
                print(f"Error creating table: {e2}")


if __name__ == "__main__":
    evaluator = RetrievalEvaluator()
    
    # Test queries covering different aspects
    test_queries = [
        "vector database implementation",
        "machine learning pipeline",
        "docker configuration",
        "API endpoints",
        "database schema"
    ]
    
    # Run comparison
    results = evaluator.compare_approaches(test_queries)
    
    # Log results
    evaluator.log_evaluation_results(results)
    
    print("\n✅ Retrieval evaluation completed!")
    print(f"Recommended approach: {results['recommended_approach']}")
