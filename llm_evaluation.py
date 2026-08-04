#!/usr/bin/env python3
"""
LLM Evaluation: Compare multiple prompt approaches
Evaluates different prompt templates and system prompts for RAG responses.
"""

import os
import time
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from rag_chain import RAGChain
from search import HybridSearch

load_dotenv()

class LLMEvaluator:
    def __init__(self):
        self.rag_chain = RAGChain()
        self.searcher = HybridSearch()
        self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/rag_portfolio")
        
        # Define different prompt approaches
        self.prompt_approaches = {
            "concise": {
                "system_prompt": """You are an expert software architect. Based on the GitHub project context, provide concise, helpful insights.
                
Keep responses short and actionable (2-3 paragraphs max). Focus on:
- Key architecture patterns
- Specific improvements
- Technology recommendations

Be direct and reference actual code/files mentioned in context.""",
                "user_prompt_template": """Context from GitHub repositories:
{context}

User Question: {question}

Based on the provided context, provide a concise analysis (2-3 paragraphs max)."""
            },
            "detailed": {
                "system_prompt": """You are a senior software engineer and technical writer. Analyze the GitHub project context thoroughly and provide comprehensive insights.

Provide detailed responses that include:
- Architecture overview
- Technology stack analysis
- Code quality assessment
- Potential improvements
- Best practices recommendations

Be thorough and reference specific files and code patterns.""",
                "user_prompt_template": """Context from GitHub repositories:
{context}

User Question: {question}

Provide a detailed technical analysis covering architecture, technologies, and recommendations."""
            },
            "educational": {
                "system_prompt": """You are a technical educator helping developers understand GitHub projects. Explain concepts clearly and provide learning resources.

Your responses should:
- Explain technical concepts in accessible language
- Provide context and background
- Suggest learning resources
- Highlight key takeaways

Be educational and supportive.""",
                "user_prompt_template": """Context from GitHub repositories:
{context}

User Question: {question}

Explain this in an educational way, providing context and helping the user understand the key concepts."""
            }
        }
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
    
    def evaluate_prompt_approach(self, approach_name: str, question: str, context: str) -> Dict[str, Any]:
        """
        Evaluate a specific prompt approach
        
        Args:
            approach_name: Name of the prompt approach
            question: User's question
            context: Retrieved context
            
        Returns:
            Dictionary with evaluation metrics
        """
        approach = self.prompt_approaches[approach_name]
        
        # Temporarily modify the RAG chain's system prompt
        original_system_prompt = self.rag_chain.system_prompt
        self.rag_chain.system_prompt = approach['system_prompt']
        
        # Create the prompt
        prompt = approach['user_prompt_template'].format(context=context, question=question)
        
        # Get response
        start_time = time.time()
        try:
            response = self.rag_chain.call_groq(prompt)
            response_time = time.time() - start_time
            
            # Restore original prompt
            self.rag_chain.system_prompt = original_system_prompt
            
            return {
                "approach": approach_name,
                "question": question,
                "response": response,
                "response_time_ms": int(response_time * 1000),
                "response_length": len(response),
                "word_count": len(response.split())
            }
        except Exception as e:
            self.rag_chain.system_prompt = original_system_prompt
            return {
                "approach": approach_name,
                "question": question,
                "response": f"Error: {str(e)}",
                "response_time_ms": 0,
                "response_length": 0,
                "word_count": 0
            }
    
    def calculate_response_quality(self, response: str, context: str, question: str) -> Dict[str, float]:
        """
        Calculate quality metrics for a response
        This is a basic evaluation - in production, use human evaluation or more sophisticated metrics
        """
        if not response or response.startswith("Error"):
            return {
                "context_relevance": 0.0,
                "question_relevance": 0.0,
                "completeness": 0.0,
                "overall_quality": 0.0
            }
        
        # Check if response mentions context terms
        context_terms = set(context.lower().split())
        response_terms = set(response.lower().split())
        context_overlap = len(context_terms.intersection(response_terms)) / len(context_terms) if context_terms else 0
        
        # Check if response addresses the question
        question_terms = set(question.lower().split())
        question_overlap = len(question_terms.intersection(response_terms)) / len(question_terms) if question_terms else 0
        
        # Check completeness (length-based heuristic)
        word_count = len(response.split())
        completeness = min(word_count / 50, 1.0)  # Assume 50 words is a good minimum
        
        # Overall quality (weighted average)
        overall_quality = (context_overlap * 0.4) + (question_overlap * 0.4) + (completeness * 0.2)
        
        return {
            "context_relevance": context_overlap,
            "question_relevance": question_overlap,
            "completeness": completeness,
            "overall_quality": overall_quality
        }
    
    def compare_prompt_approaches(self, questions: List[str]) -> Dict[str, Any]:
        """
        Compare all prompt approaches across multiple questions
        
        Returns:
            Dictionary with comparison results and recommendations
        """
        print("=" * 60)
        print("LLM Prompt Approach Comparison")
        print("=" * 60)
        
        all_results = {
            "concise": [],
            "detailed": [],
            "educational": []
        }
        
        for question in questions:
            print(f"\nQuestion: '{question}'")
            print("-" * 40)
            
            # Get context
            context = self.searcher.get_context_for_query(question, max_context_length=2000)
            
            # Evaluate each approach
            for approach_name in self.prompt_approaches.keys():
                result = self.evaluate_prompt_approach(approach_name, question, context)
                
                # Calculate quality metrics
                quality = self.calculate_response_quality(result['response'], context, question)
                result.update(quality)
                
                all_results[approach_name].append(result)
                
                print(f"{approach_name:12s}: {result['word_count']:3d} words, {result['response_time_ms']:3d}ms, quality: {result['overall_quality']:.3f}")
        
        # Calculate aggregate statistics
        summary = self.calculate_summary(all_results)
        
        # Determine best approach
        best_approach = self.determine_best_approach(summary)
        
        print("\n" + "=" * 60)
        print("Summary Statistics")
        print("=" * 60)
        for approach, stats in summary.items():
            print(f"\n{approach}:")
            print(f"  Avg word count: {stats['avg_word_count']:.1f}")
            print(f"  Avg response time: {stats['avg_response_time_ms']:.1f}ms")
            print(f"  Avg context relevance: {stats['avg_context_relevance']:.3f}")
            print(f"  Avg question relevance: {stats['avg_question_relevance']:.3f}")
            print(f"  Avg overall quality: {stats['avg_overall_quality']:.3f}")
        
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
        
        for approach, results in all_results.items():
            if not results:
                continue
            
            avg_word_count = sum(r['word_count'] for r in results) / len(results)
            avg_response_time = sum(r['response_time_ms'] for r in results) / len(results)
            avg_context_relevance = sum(r['context_relevance'] for r in results) / len(results)
            avg_question_relevance = sum(r['question_relevance'] for r in results) / len(results)
            avg_overall_quality = sum(r['overall_quality'] for r in results) / len(results)
            
            summary[approach] = {
                "avg_word_count": avg_word_count,
                "avg_response_time_ms": avg_response_time,
                "avg_context_relevance": avg_context_relevance,
                "avg_question_relevance": avg_question_relevance,
                "avg_overall_quality": avg_overall_quality
            }
        
        return summary
    
    def determine_best_approach(self, summary: Dict[str, Dict]) -> str:
        """
        Determine the best approach based on overall quality score
        """
        best_approach = None
        best_score = -1
        
        for approach, stats in summary.items():
            quality_score = stats['avg_overall_quality']
            
            if quality_score > best_score:
                best_score = quality_score
                best_approach = approach
        
        return best_approach
    
    def log_evaluation_results(self, comparison_results: Dict[str, Any]):
        """Log evaluation results to database for tracking"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for approach, results in comparison_results['detailed_results'].items():
                    for result in results:
                        sql = """
                            INSERT INTO llm_evaluations 
                            (approach, question, response, response_time_ms, word_count, 
                             context_relevance, question_relevance, overall_quality, timestamp)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """
                        cursor.execute(sql, (
                            approach,
                            result['question'],
                            result['response'],
                            result['response_time_ms'],
                            result['word_count'],
                            result['context_relevance'],
                            result['question_relevance'],
                            result['overall_quality']
                        ))
                
                conn.commit()
                print("\nLLM evaluation results logged to database")
                
        except Exception as e:
            print(f"Error logging LLM evaluation results: {e}")
            # Create table if it doesn't exist
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS llm_evaluations (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            approach VARCHAR(50) NOT NULL,
                            question TEXT NOT NULL,
                            response TEXT NOT NULL,
                            response_time_ms INTEGER NOT NULL,
                            word_count INTEGER NOT NULL,
                            context_relevance FLOAT NOT NULL,
                            question_relevance FLOAT NOT NULL,
                            overall_quality FLOAT NOT NULL,
                            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        )
                    """)
                    conn.commit()
                    print("Created llm_evaluations table")
            except Exception as e2:
                print(f"Error creating table: {e2}")


if __name__ == "__main__":
    evaluator = LLMEvaluator()
    
    # Test questions
    test_questions = [
        "What are the main components of this project?",
        "How is the database structured?",
        "What technologies are used in this project?"
    ]
    
    # Run comparison
    results = evaluator.compare_prompt_approaches(test_questions)
    
    # Log results
    evaluator.log_evaluation_results(results)
    
    print("\n✅ LLM evaluation completed!")
    print(f"Recommended approach: {results['recommended_approach']}")
