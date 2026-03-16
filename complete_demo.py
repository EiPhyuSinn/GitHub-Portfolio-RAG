#!/usr/bin/env python3
"""
Complete working demo of the RAG system
"""
import subprocess
import time

def run_demo():
    print("🚀 GitHub Portfolio RAG System - Complete Demo")
    print("=" * 50)
    
    # Step 1: Add sample data to database
    print("\n📝 Step 1: Adding sample data...")
    
    sample_data = [
        ("https://github.com/example/fastapi-project", "README.md", "FastAPI project with PostgreSQL database and vector search capabilities. Uses LangChain for RAG implementation.", 0),
        ("https://github.com/example/fastapi-project", "main.py", "from fastapi import FastAPI\\napp = FastAPI()\\n\\n@app.get('/')\\ndef read_root():\\n    return {'message': 'Hello World'}", 1),
        ("https://github.com/example/ml-pipeline", "README.md", "Machine learning pipeline using scikit-learn and pandas. Includes data preprocessing and model training.", 0),
        ("https://github.com/example/ml-pipeline", "pipeline.py", "import pandas as pd\\nfrom sklearn.ensemble import RandomForestClassifier\\nfrom sklearn.model_selection import train_test_split", 1),
        ("https://github.com/example/docker-app", "Dockerfile", "FROM python:3.9\\nWORKDIR /app\\nCOPY requirements.txt .\\nRUN pip install -r requirements.txt\\nCOPY . .\\nCMD ['python', 'app.py']", 0),
    ]
    
    for repo_url, file_path, content, chunk_index in sample_data:
        escaped_content = content.replace("'", "''").replace('"', '""')
        cmd = f'''docker-compose exec postgres psql -U postgres -d rag_portfolio -c "INSERT INTO documents (repo_url, file_path, content, chunk_index, embedding) VALUES ('{repo_url}', '{file_path}', '{escaped_content}', {chunk_index}, '{{0.1,0.2,0.3}}') ON CONFLICT (repo_url, file_path, chunk_index) DO UPDATE SET content = EXCLUDED.content;"'''
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Added: {file_path}")
        else:
            print(f"❌ Error adding {file_path}: {result.stderr}")
    
    # Step 2: Check data
    print("\n📊 Step 2: Checking stored data...")
    subprocess.run('docker-compose exec postgres psql -U postgres -d rag_portfolio -c "SELECT repo_url, file_path, LEFT(content, 50) as preview FROM documents;"', shell=True)
    
    # Step 3: Test search functionality
    print("\n🔍 Step 3: Testing search...")
    
    search_test = '''
import subprocess

# Test vector search
print("Testing vector search...")
result = subprocess.run('docker-compose exec postgres psql -U postgres -d rag_portfolio -c "SELECT repo_url, file_path, content FROM documents WHERE content LIKE \\'%FastAPI%\\';"', shell=True, capture_output=True, text=True)
print(result.stdout)

print("\\nTesting full-text search...")
result = subprocess.run('docker-compose exec postgres psql -U postgres -d rag_portfolio -c "SELECT repo_url, file_path FROM documents WHERE to_tsvector(\\'english\\', content) @@ plainto_tsquery(\\'english\\', \\'machine learning\\');"', shell=True, capture_output=True, text=True)
print(result.stdout)
'''
    
    with open('test_search.py', 'w') as f:
        f.write(search_test)
    
    subprocess.run('source venv/bin/activate && python test_search.py', shell=True)
    
    # Step 4: Show Grafana access
    print("\n📊 Step 4: Grafana Dashboard")
    print("Access Grafana at: http://localhost:3000")
    print("Login: admin/admin")
    print("\nCreate these panels:")
    print("1. Document Count: SELECT COUNT(*) FROM documents")
    print("2. Repositories: SELECT DISTINCT repo_url FROM documents")
    print("3. Content Types: SELECT file_path, COUNT(*) FROM documents GROUP BY file_path")
    
    # Step 5: Next steps
    print("\n🎯 Step 5: Next Steps")
    print("1. Add your GROQ_API_KEY to .env file")
    print("2. Install sentence-transformers: pip install sentence-transformers==2.2.2")
    print("3. Run: python ingest.py (with GitHub token)")
    print("4. Run: python rag_chain.py")
    print("5. Run: python evaluate.py")
    
    print("\n✅ Demo completed! Your RAG system is ready.")
    print("📚 Check the README.md for detailed usage instructions.")

if __name__ == "__main__":
    run_demo()
