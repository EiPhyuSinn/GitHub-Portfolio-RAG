#!/bin/bash

echo "🚀 Running GitHub Portfolio RAG System Test"
echo "=========================================="

# Step 1: Test database connection
echo "1. Testing database connection..."
docker-compose exec postgres psql -U postgres -d rag_portfolio -c "SELECT '✅ Database connected!' as status;"

# Step 2: Show tables
echo -e "\n2. Checking tables..."
docker-compose exec postgres psql -U postgres -d rag_portfolio -c "\dt"

# Step 3: Test ingestion (using a small repo)
echo -e "\n3. Testing GitHub ingestion..."
docker cp ingest.py rag_postgres:/tmp/ingest.py
docker cp .env rag_postgres:/tmp/.env

# Install dependencies in container and run ingestion
docker-compose exec postgres bash -c "
cd /tmp
pip install requests sentence-transformers psycopg2-binary python-dotenv langchain langchain-groq
python -c '
import os
os.chdir(\"/tmp\")
from ingest import GitHubDataLoader
loader = GitHubDataLoader()
try:
    loader.ingest_repository(\"https://github.com/octocat/Hello-World\")
    print(\"✅ Ingestion completed!\")
except Exception as e:
    print(f\"❌ Ingestion failed: {e}\")
'
"

# Step 4: Check ingested data
echo -e "\n4. Checking ingested data..."
docker-compose exec postgres psql -U postgres -d rag_portfolio -c "SELECT COUNT(*) as document_count FROM documents;"

echo -e "\n🎉 Test completed!"
echo "You can now:"
echo "- Access Grafana: http://localhost:3000 (admin/admin)"
echo "- Check database: docker-compose exec postgres psql -U postgres -d rag_portfolio"
