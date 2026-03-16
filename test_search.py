
import subprocess

# Test vector search
print("Testing vector search...")
result = subprocess.run('docker-compose exec postgres psql -U postgres -d rag_portfolio -c "SELECT repo_url, file_path, content FROM documents WHERE content LIKE \'%FastAPI%\';"', shell=True, capture_output=True, text=True)
print(result.stdout)

print("\nTesting full-text search...")
result = subprocess.run('docker-compose exec postgres psql -U postgres -d rag_portfolio -c "SELECT repo_url, file_path FROM documents WHERE to_tsvector(\'english\', content) @@ plainto_tsquery(\'english\', \'machine learning\');"', shell=True, capture_output=True, text=True)
print(result.stdout)
