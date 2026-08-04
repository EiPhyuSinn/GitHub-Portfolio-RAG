#!/usr/bin/env python3
"""
Flask UI for GitHub Portfolio RAG System
"""

from flask import Flask, render_template, request, jsonify, session
import time
import json
from datetime import datetime
from rag_chain import RAGChain
from search import HybridSearch

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Initialize RAG components
rag_chain = RAGChain()
searcher = HybridSearch()

@app.route('/')
def index():
    """Main page with chat interface"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """API endpoint for chat messages"""
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        # Get RAG response
        start_time = time.time()
        result = rag_chain.ask_sensei(question)
        response_time = time.time() - start_time
        
        # Store metrics
        try:
            with searcher.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO metrics (question, llm_response, response_latency_ms, faithfulness_score)
                    VALUES (%s, %s, %s, %s)
                """, (question, result['response'], int(response_time * 1000), 0.8))  # Placeholder faithfulness score
                conn.commit()
        except Exception as e:
            print(f"Metrics storage error: {e}")
        
        return jsonify({
            'response': result['response'],
            'response_time': f"{response_time:.2f}s",
            'context_used': len(result.get('context', [])),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['POST'])
def search_documents():
    """Search documents directly"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        limit = data.get('limit', 10)
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        results = searcher.hybrid_search(query, limit=limit)
        
        return jsonify({
            'results': results,
            'count': len(results),
            'query': query
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ingest', methods=['POST'])
def ingest_repository():
    """Ingest a new repository"""
    try:
        data = request.get_json()
        repo_url = data.get('repo_url', '')
        
        if not repo_url:
            return jsonify({'error': 'No repository URL provided'}), 400
        
        from ingest import GitHubDataLoader
        loader = GitHubDataLoader()
        loader.ingest_repository(repo_url)
        
        return jsonify({
            'message': f'Successfully ingested {repo_url}',
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """Get database statistics"""
    try:
        conn = searcher.get_connection()
        cursor = conn.cursor()
        
        # Document count
        cursor.execute("SELECT COUNT(*) as count FROM documents")
        doc_count = cursor.fetchone()['count']
        
        # Metrics count
        cursor.execute("SELECT COUNT(*) as count FROM metrics")
        metrics_count = cursor.fetchone()['count']
        
        # Average response time
        cursor.execute("SELECT AVG(response_latency_ms) as avg_time FROM metrics")
        avg_response_time = cursor.fetchone()['avg_time'] or 0
        
        # Average faithfulness score
        cursor.execute("SELECT AVG(faithfulness_score) as avg_score FROM metrics")
        avg_faithfulness = cursor.fetchone()['avg_score'] or 0
        
        # Recent queries
        cursor.execute("""
            SELECT question, faithfulness_score, timestamp 
            FROM metrics 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        recent_queries = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'documents': doc_count,
            'queries': metrics_count,
            'avg_response_time': f"{avg_response_time:.0f}ms",
            'avg_faithfulness': f"{avg_faithfulness:.3f}",
            'recent_queries': [
                {
                    'question': row['question'],
                    'score': row['faithfulness_score'],
                    'timestamp': row['timestamp'].isoformat() if row['timestamp'] else None
                } for row in recent_queries
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/repositories')
def get_repositories():
    """Get list of ingested repositories"""
    try:
        conn = searcher.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT repo_url, COUNT(*) as document_count
            FROM documents 
            GROUP BY repo_url
            ORDER BY repo_url
        """)
        repos = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'repositories': [
                {
                    'url': row['repo_url'],
                    'document_count': row['document_count']
                } for row in repos
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback for a response"""
    try:
        data = request.get_json()
        question = data.get('question', '')
        response = data.get('response', '')
        rating = data.get('rating', None)
        feedback_text = data.get('feedback_text', '')
        
        if not question or not response:
            return jsonify({'error': 'Question and response are required'}), 400
        
        if rating is None or not (1 <= rating <= 5):
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        
        conn = searcher.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_feedback (question, response, rating, feedback_text)
            VALUES (%s, %s, %s, %s)
        """, (question, response, rating, feedback_text))
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Feedback submitted successfully',
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feedback/stats')
def get_feedback_stats():
    """Get feedback statistics"""
    try:
        conn = searcher.get_connection()
        cursor = conn.cursor()
        
        # Average rating
        cursor.execute("SELECT AVG(rating) as avg_rating FROM user_feedback")
        avg_rating = cursor.fetchone()['avg_rating'] or 0
        
        # Total feedback count
        cursor.execute("SELECT COUNT(*) as count FROM user_feedback")
        total_feedback = cursor.fetchone()['count']
        
        # Rating distribution
        cursor.execute("""
            SELECT rating, COUNT(*) as count
            FROM user_feedback
            GROUP BY rating
            ORDER BY rating
        """)
        rating_distribution = {row['rating']: row['count'] for row in cursor.fetchall()}
        
        # Recent feedback
        cursor.execute("""
            SELECT question, rating, feedback_text, timestamp
            FROM user_feedback
            ORDER BY timestamp DESC
            LIMIT 5
        """)
        recent_feedback = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'average_rating': f"{avg_rating:.2f}",
            'total_feedback': total_feedback,
            'rating_distribution': rating_distribution,
            'recent_feedback': [
                {
                    'question': row['question'],
                    'rating': row['rating'],
                    'feedback_text': row['feedback_text'],
                    'timestamp': row['timestamp'].isoformat() if row['timestamp'] else None
                } for row in recent_feedback
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
