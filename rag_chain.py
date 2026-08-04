#!/usr/bin/env python3
"""
Phase 4: Groq RAG Logic & Rate Limit Handling
Connects to Groq using langchain-groq with rate limit handling and caching.
"""

import os
import time
import hashlib
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from langchain_groq import ChatGroq
# from langchain.schema import HumanMessage, SystemMessage
from langchain_core.messages import HumanMessage, SystemMessage
# from langchain.prompts import PromptTemplate
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RAGChain:
    def __init__(self):
        # Initialize Groq LLM
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        
        self.llm = ChatGroq(
            groq_api_key=self.groq_api_key,
            model_name="llama-3.1-8b-instant",
            temperature=0.1,
        )
        
        # Database connection
        self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/rag_portfolio")
        
        # Rate limiting
        self.last_call_time = 0
        self.min_call_interval = 2.0  # 2 seconds between calls
        
        # Cache for responses
        self.response_cache = {}
        self.cache_ttl = 3600  # 1 hour cache TTL
        
        # Import search functionality
        from search import HybridSearch
        self.searcher = HybridSearch()
        
        # System prompt for project analysis
        self.system_prompt = """You are an expert software architect. Based on the GitHub project context, provide concise, helpful insights.
        
        Keep responses short and actionable (2-3 paragraphs max). Focus on:
        - Key architecture patterns
        - Specific improvements
        - Technology recommendations
        
        Be direct and reference actual code/files mentioned in context."""
    
    def get_cache_key(self, question: str, context: str) -> str:
        """Generate cache key for question-context pair"""
        combined = f"{question}:{context}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def check_cache(self, question: str, context: str) -> Optional[str]:
        """Check if response is cached"""
        cache_key = self.get_cache_key(question, context)
        
        if cache_key in self.response_cache:
            cached_data = self.response_cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < timedelta(seconds=self.cache_ttl):
                print("Using cached response")
                return cached_data['response']
            else:
                # Expired cache entry
                del self.response_cache[cache_key]
        
        return None
    
    def cache_response(self, question: str, context: str, response: str):
        """Cache the response"""
        cache_key = self.get_cache_key(question, context)
        self.response_cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now()
        }
    
    def rate_limit_wait(self):
        """Implement rate limiting with sleep"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.min_call_interval:
            wait_time = self.min_call_interval - time_since_last_call
            print(f"Rate limiting: waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)
        
        self.last_call_time = time.time()
    
    def retrieve_context(self, question: str) -> str:
        """Retrieve relevant context using hybrid search"""
        print(f"Retrieving context for: '{question}'")
        context = self.searcher.get_context_for_query(question, max_context_length=2000)
        
        if not context:
            return "No relevant context found in the ingested repositories."
        
        return context
    
    def create_prompt(self, question: str, context: str) -> str:
        """Create the prompt for the LLM"""
        prompt_template = """
        Context from GitHub repositories:
        {context}
        
        User Question: {question}
        
        Based on the provided context, please analyze the user's question and provide helpful insights about the project structure, architecture, or potential improvements.
        
        Response:
        """
        
        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=prompt_template
        )
        
        return prompt.format(context=context, question=question)
    
    def call_groq(self, prompt: str) -> str:
        """Make API call to Groq with rate limiting"""
        self.rate_limit_wait()
        
        try:
            print("Calling Groq API...")
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            return response.content
            
        except Exception as e:
            print(f"Error calling Groq API: {e}")
            return f"I apologize, but I encountered an error while processing your request: {str(e)}"
    
    def ask_sensei(self, question: str) -> Dict[str, any]:
        """
        Main method to ask questions about GitHub projects
        
        Args:
            question: User's question about the projects
            
        Returns:
            Dictionary containing question, context, response, and metadata
        """
        print(f"\n{'='*50}")
        print(f"Question: {question}")
        print(f"{'='*50}")
        
        start_time = time.time()
        
        try:
            # Retrieve context
            context = self.retrieve_context(question)
            
            # Check cache
            cached_response = self.check_cache(question, context)
            if cached_response:
                response_time = time.time() - start_time
                return {
                    "question": question,
                    "context": context,
                    "response": cached_response,
                    "response_time": response_time,
                    "cached": True
                }
            
            # Create prompt
            prompt = self.create_prompt(question, context)
            
            # Get response from Groq
            response = self.call_groq(prompt)
            
            # Cache the response
            self.cache_response(question, context, response)
            
            response_time = time.time() - start_time
            
            result = {
                "question": question,
                "context": context,
                "response": response,
                "response_time": response_time,
                "cached": False
            }
            
            print(f"Response time: {response_time:.2f} seconds")
            print(f"Response: {response}")
            
            return result
            
        except Exception as e:
            print(f"Error in ask_sensei: {e}")
            return {
                "question": question,
                "context": "",
                "response": f"An error occurred: {str(e)}",
                "response_time": time.time() - start_time,
                "cached": False
            }
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            "cached_responses": len(self.response_cache),
            "cache_ttl_seconds": self.cache_ttl,
            "min_call_interval": self.min_call_interval
        }


if __name__ == "__main__":
    # Test the RAG chain
    rag = RAGChain()
    
    # Test questions
    test_questions = [
        "What are the main components of this project?",
        "How is the database structured?",
        "What are some potential improvements to the architecture?"
    ]
    
    for question in test_questions:
        result = rag.ask_sensei(question)
        print(f"\n{'='*50}")
        print(f"Question: {result['question']}")
        print(f"Cached: {result['cached']}")
        print(f"Response Time: {result['response_time']:.2f}s")
        print(f"Response: {result['response']}")
        print(f"{'='*50}\n")
    
    # Show cache stats
    cache_stats = rag.get_cache_stats()
    print(f"Cache Stats: {cache_stats}")
