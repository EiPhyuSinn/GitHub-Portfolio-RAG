#!/usr/bin/env python3
"""
Phase 5: Evaluation & Monitoring
Logs every RAG interaction into the metrics table with faithfulness scoring.
"""

import os
import time
import re
from typing import Dict, List, Set
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RAGEvaluator:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/rag_portfolio")
        
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
    
    def extract_key_terms(self, text: str) -> Set[str]:
        """Extract key terms from text for faithfulness scoring"""
        # Simple keyword extraction - can be enhanced with NLP
        # Remove common words and extract meaningful terms
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        # Extract words and normalize
        words = re.findall(r'\b\w+\b', text.lower())
        key_terms = {word for word in words if len(word) > 3 and word not in common_words}
        
        return key_terms
    
    def calculate_faithfulness_score(self, context: List[str], response: str) -> float:
        """
        Calculate faithfulness score by checking if key terms from context appear in response
        
        Args:
            context: List of context strings from retrieved documents
            response: LLM response string
            
        Returns:
            Faithfulness score between 0.0 and 1.0
        """
        if not context or not response:
            return 0.0
        
        # Combine all context
        combined_context = " ".join(context).lower()
        response_text = response.lower()
        
        # Extract key terms from context
        context_terms = self.extract_key_terms(combined_context)
        
        if not context_terms:
            return 0.5  # Default score if no key terms found
        
        # Count how many context terms appear in response
        response_terms = self.extract_key_terms(response_text)
        
        # Calculate overlap
        overlap = context_terms.intersection(response_terms)
        faithfulness = len(overlap) / len(context_terms)
        
        # Bonus for longer, more detailed responses
        length_bonus = min(len(response.split()) / 100, 0.2)  # Max 0.2 bonus
        
        final_score = min(faithfulness + length_bonus, 1.0)
        
        return final_score
    
    def log_interaction(self, question: str, retrieved_context: List[str], 
                       llm_response: str, response_latency_ms: int):
        """
        Log RAG interaction to metrics table
        
        Args:
            question: User's question
            retrieved_context: List of context strings used for generation
            llm_response: LLM's response
            response_latency_ms: Response time in milliseconds
        """
        # Calculate faithfulness score
        faithfulness_score = self.calculate_faithfulness_score(retrieved_context, llm_response)
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert metrics
                sql = """
                    INSERT INTO metrics 
                    (question, retrieved_context, llm_response, faithfulness_score, response_latency_ms)
                    VALUES (%s, %s, %s, %s, %s)
                """
                
                cursor.execute(sql, (
                    question,
                    retrieved_context,
                    llm_response,
                    faithfulness_score,
                    response_latency_ms
                ))
                
                conn.commit()
                
                print(f"Logged interaction with faithfulness score: {faithfulness_score:.3f}")
                
        except Exception as e:
            print(f"Error logging interaction: {e}")
    
    def get_metrics_summary(self, limit: int = 100) -> Dict[str, float]:
        """Get summary statistics from metrics table"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get recent metrics
                sql = """
                    SELECT 
                        AVG(faithfulness_score) as avg_faithfulness,
                        MIN(faithfulness_score) as min_faithfulness,
                        MAX(faithfulness_score) as max_faithfulness,
                        AVG(response_latency_ms) as avg_latency,
                        COUNT(*) as total_interactions
                    FROM metrics
                    ORDER BY timestamp DESC
                    LIMIT %s
                """
                
                cursor.execute(sql, (limit,))
                result = cursor.fetchone()
                
                if result:
                    return {
                        "avg_faithfulness": float(result['avg_faithfulness'] or 0),
                        "min_faithfulness": float(result['min_faithfulness'] or 0),
                        "max_faithfulness": float(result['max_faithfulness'] or 0),
                        "avg_latency_ms": float(result['avg_latency_ms'] or 0),
                        "total_interactions": int(result['total_interactions'])
                    }
                else:
                    return {
                        "avg_faithfulness": 0.0,
                        "min_faithfulness": 0.0,
                        "max_faithfulness": 0.0,
                        "avg_latency_ms": 0.0,
                        "total_interactions": 0
                    }
                    
        except Exception as e:
            print(f"Error getting metrics summary: {e}")
            return {}
    
    def get_recent_interactions(self, limit: int = 10) -> List[Dict]:
        """Get recent interactions for review"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                sql = """
                    SELECT question, llm_response, faithfulness_score, 
                           response_latency_ms, timestamp
                    FROM metrics
                    ORDER BY timestamp DESC
                    LIMIT %s
                """
                
                cursor.execute(sql, (limit,))
                results = cursor.fetchall()
                
                return [dict(row) for row in results]
                
        except Exception as e:
            print(f"Error getting recent interactions: {e}")
            return []
    
    def export_for_grafana(self) -> Dict[str, List]:
        """Export data formatted for Grafana dashboard"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Time series data for faithfulness scores
                cursor.execute("""
                    SELECT 
                        DATE_TRUNC('hour', timestamp) as hour,
                        AVG(faithfulness_score) as avg_faithfulness,
                        COUNT(*) as request_count
                    FROM metrics
                    WHERE timestamp >= NOW() - INTERVAL '24 hours'
                    GROUP BY DATE_TRUNC('hour', timestamp)
                    ORDER BY hour
                """)
                
                time_series = [dict(row) for row in cursor.fetchall()]
                
                # Top questions
                cursor.execute("""
                    SELECT 
                        question,
                        COUNT(*) as count
                    FROM metrics
                    GROUP BY question
                    ORDER BY count DESC
                    LIMIT 10
                """)
                
                top_questions = [dict(row) for row in cursor.fetchall()]
                
                return {
                    "time_series": time_series,
                    "top_questions": top_questions
                }
                
        except Exception as e:
            print(f"Error exporting for Grafana: {e}")
            return {"time_series": [], "top_questions": []}


# Enhanced RAG Chain with evaluation
class EvaluatedRAGChain:
    def __init__(self):
        from rag_chain import RAGChain
        self.rag_chain = RAGChain()
        self.evaluator = RAGEvaluator()
    
    def ask_and_evaluate(self, question: str) -> Dict[str, any]:
        """
        Ask question and automatically log evaluation metrics
        
        Args:
            question: User's question
            
        Returns:
            Enhanced result with evaluation metrics
        """
        # Get RAG response
        start_time = time.time()
        result = self.rag_chain.ask_sensei(question)
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Extract context for evaluation
        context = [result['context']] if result['context'] else []
        
        # Log interaction
        self.evaluator.log_interaction(
            question=question,
            retrieved_context=context,
            llm_response=result['response'],
            response_latency_ms=response_time_ms
        )
        
        # Add evaluation metrics to result
        result['response_time_ms'] = response_time_ms
        result['faithfulness_score'] = self.evaluator.calculate_faithfulness_score(
            context, result['response']
        )
        
        return result


if __name__ == "__main__":
    # Test the evaluation system
    evaluated_rag = EvaluatedRAGChain()
    
    # Test question
    test_question = "What are the key components of this project?"
    
    print(f"Testing evaluation with question: {test_question}")
    result = evaluated_rag.ask_and_evaluate(test_question)
    
    print(f"\nEvaluation Results:")
    print(f"Response Time: {result['response_time_ms']}ms")
    print(f"Faithfulness Score: {result['faithfulness_score']:.3f}")
    print(f"Response: {result['response']}")
    
    # Show metrics summary
    evaluator = RAGEvaluator()
    summary = evaluator.get_metrics_summary()
    print(f"\nMetrics Summary: {summary}")
    
    # Show recent interactions
    recent = evaluator.get_recent_interactions(3)
    print(f"\nRecent Interactions:")
    for i, interaction in enumerate(recent, 1):
        print(f"{i}. Faithfulness: {interaction['faithfulness_score']:.3f}, "
              f"Latency: {interaction['response_latency_ms']}ms")
