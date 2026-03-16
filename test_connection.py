#!/usr/bin/env python3
"""
Test database connection and setup
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    """Test different connection methods"""
    urls = [
        "postgresql://postgres:password@localhost:5432/rag_portfolio",
        "postgresql://postgres@localhost:5432/rag_portfolio", 
        "postgresql://postgres:password@127.0.0.1:5432/rag_portfolio",
        "postgresql://postgres@127.0.0.1:5432/rag_portfolio",
    ]
    
    for url in urls:
        try:
            print(f"Testing: {url}")
            conn = psycopg2.connect(url)
            cursor = conn.cursor()
            cursor.execute("SELECT 'Connected!' as status")
            result = cursor.fetchone()
            print(f"✅ SUCCESS: {result[0]}")
            
            # Check tables
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            tables = cursor.fetchall()
            print(f"📋 Tables: {[t[0] for t in tables]}")
            
            conn.close()
            return url
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    return None

if __name__ == "__main__":
    working_url = test_connection()
    if working_url:
        print(f"\n🎯 Working URL: {working_url}")
        # Save it to .env
        with open('.env', 'w') as f:
            f.write(f"GROQ_API_KEY=your_groq_api_key_here\n")
            f.write(f"GITHUB_TOKEN=your_github_token_here\n")
            f.write(f"DATABASE_URL={working_url}\n")
        print("✅ Updated .env file with working database URL")
    else:
        print("❌ No working connection found")
