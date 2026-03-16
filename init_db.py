#!/usr/bin/env python3
"""
Initialize database schema for the RAG system
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def init_database():
    """Initialize database with schema"""
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/rag_portfolio")
    
    # Read schema file
    with open('schema.sql', 'r') as f:
        schema_sql = f.read()
    
    # Connect and execute schema
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Execute schema
        cursor.execute(schema_sql)
        conn.commit()
        
        print("✅ Database schema initialized successfully")
        
        # Verify tables
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN ('documents', 'metrics')
        """)
        tables = cursor.fetchall()
        print(f"📋 Created tables: {[t[0] for t in tables]}")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    init_database()
