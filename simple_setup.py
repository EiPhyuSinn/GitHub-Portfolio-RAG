#!/usr/bin/env python3
"""
Simple setup script that works with Docker PostgreSQL
"""
import subprocess
import time
import os

def run_command(cmd, description):
    """Run a command and show results"""
    print(f"\n🔧 {description}")
    print(f"Command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Success: {result.stdout}")
        else:
            print(f"❌ Error: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    print("🚀 GitHub Portfolio RAG System Setup")
    print("=" * 50)
    
    # Step 1: Check Docker services
    run_command("docker-compose ps", "Checking Docker services")
    
    # Step 2: Test database connection
    run_command(
        'docker-compose exec postgres psql -U postgres -d rag_portfolio -c "SELECT \'Database connected!\' as status;"',
        "Testing database connection"
    )
    
    # Step 3: Create a simple test script
    test_script = '''
import requests
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Test GitHub API
def test_github():
    try:
        response = requests.get("https://api.github.com/repos/octocat/Hello-World")
        if response.status_code == 200:
            print("✅ GitHub API working")
            return True
        else:
            print(f"❌ GitHub API error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ GitHub API failed: {e}")
        return False

# Test database insertion
def test_database():
    try:
        # Using Docker exec to insert test data
        import subprocess
        cmd = '''docker-compose exec postgres psql -U postgres -d rag_portfolio -c "INSERT INTO documents (repo_url, file_path, content, chunk_index, embedding) VALUES (\'https://github.com/test/repo\', \'test.py\', \'print("Hello World")\', 0, \'{0.1,0.2,0.3}\') ON CONFLICT DO NOTHING;"'''
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Database insertion working")
            return True
        else:
            print(f"❌ Database insertion failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Running basic tests...")
    test_github()
    test_database()
    print("🎉 Tests completed!")
'''
    
    with open('test_basic.py', 'w') as f:
        f.write(test_script)
    
    print("\n🧪 Running basic functionality tests...")
    run_command("source venv/bin/activate && python test_basic.py", "Running basic tests")
    
    # Step 4: Show next steps
    print("\n📋 Next Steps:")
    print("1. Add your GROQ_API_KEY to .env file")
    print("2. Run: python ingest.py (to ingest GitHub repositories)")
    print("3. Run: python rag_chain.py (to ask questions)")
    print("4. Access Grafana: http://localhost:3000 (admin/admin)")
    
    print("\n🎯 Quick Test Commands:")
    print("# Test GitHub ingestion:")
    print("source venv/bin/activate && python -c \"from ingest import GitHubDataLoader; loader = GitHubDataLoader(); loader.ingest_repository('https://github.com/octocat/Hello-World')\"")
    
    print("\n# Test RAG chain:")
    print("source venv/bin/activate && python -c \"from rag_chain import RAGChain; rag = RAGChain(); result = rag.ask_sensei('What is this repository about?'); print(result['response'])\"")

if __name__ == "__main__":
    main()
