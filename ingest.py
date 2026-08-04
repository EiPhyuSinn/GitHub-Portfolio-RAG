#!/usr/bin/env python3
"""
Phase 2: GitHub Data Loader
Fetches README.md and file tree structure from GitHub, chunks content, and stores in database.
"""

import os
import re
import time
from typing import List, Dict, Any
import requests
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from sentence_transformers import SentenceTransformer
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GitHubDataLoader:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.headers = {"Authorization": f"token {self.github_token}"} if self.github_token else {}
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
        )
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def extract_repo_info(self, repo_url: str) -> Dict[str, str]:
        """Extract owner and repo name from GitHub URL"""
        match = re.match(r'https://github\.com/([^/]+)/([^/]+)', repo_url)
        if not match:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")
        return {"owner": match.group(1), "repo": match.group(2)}
    
    def fetch_readme_content(self, owner: str, repo: str) -> str:
        """Fetch README.md content from GitHub API"""
        url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        
        try:
            response = requests.get(url, headers=self.headers)
            # response.raise_for_status()
            
            # Get download URL for README content
            readme_data = response.json()
            download_url = readme_data.get("download_url")
            
            if download_url:
                content_response = requests.get(download_url, headers=self.headers)
                content_response.raise_for_status()
                return content_response.text
            else:
                return ""
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching README: {e}")
            return ""
    
    def fetch_file_tree(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Fetch file tree structure from GitHub API"""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
        
        try:
            response = requests.get(url, headers=self.headers)
            # response.raise_for_status()
            
            tree_data = response.json()
            print(f"Fetched file tree with {len(tree_data.get('tree', []))} items")
            files = []
            
            for item in tree_data.get("tree", []):
                if item["type"] == "blob":  # It's a file
                    files.append({
                        "path": item["path"],
                        "size": item.get("size", 0)
                    })
            
            return files
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching file tree: {e}")
            return []
    
    def create_documents(self, repo_url: str) -> List[Document]:
        """Create Document objects from README and file tree"""
        repo_info = self.extract_repo_info(repo_url)
        owner, repo = repo_info["owner"], repo_info["repo"]
        print(f"Extracted owner: {owner}, repo: {repo}")
      
        documents = []
        
        # Fetch README content
        print(f"Fetching README for {owner}/{repo}...")
        readme_content = self.fetch_readme_content(owner, repo)
        
        if readme_content:
            # Create metadata for README
            readme_metadata = {
                "repo_url": repo_url,
                "file_path": "README.md",
                "file_type": "readme"
            }
            
            # Split README into chunks
            readme_chunks = self.text_splitter.split_text(readme_content)
            for i, chunk in enumerate(readme_chunks):
                chunk_metadata = readme_metadata.copy()
                chunk_metadata["chunk_index"] = i

                print(f'Creating document chunk {i} for README.md with metadata: {chunk_metadata}')
                documents.append(Document(page_content=chunk, metadata=chunk_metadata))
        
        # Fetch file tree
        print(f"Fetching file tree for {owner}/{repo}...")
        files = self.fetch_file_tree(owner, repo)
        
        # Create documents from file paths (as searchable content)
        file_list_content = "\n".join([f["path"] for f in files if f["size"] < 100000])  # Skip large files
        
        if file_list_content:
            file_metadata = {
                "repo_url": repo_url,
                "file_path": "file_structure",
                "file_type": "structure"
            }
            
            file_chunks = self.text_splitter.split_text(file_list_content)
            for i, chunk in enumerate(file_chunks):
                chunk_metadata = file_metadata.copy()
                chunk_metadata["chunk_index"] = i
                documents.append(Document(page_content=chunk, metadata=chunk_metadata))
        
        print(f"Created {len(documents)} document chunks")
        return documents
    
    def embed_documents(self, documents: List[Document]) -> List[List[float]]:
        """Generate embeddings for documents"""
        print("Generating embeddings...")
        texts = [doc.page_content for doc in documents]
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def store_documents(self, repo_url: str, documents: List[Document], embeddings: List[List[float]]):
        """Store documents and embeddings in PostgreSQL"""
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/rag_portfolio")
        
        try:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Prepare data for insertion
            rows = []
            for doc, embedding in zip(documents, embeddings):
                rows.append((
                    doc.metadata["repo_url"],
                    doc.metadata["file_path"],
                    doc.page_content,
                    doc.metadata["chunk_index"],
                    embedding
                ))
            
            # Insert data
            query = """
                INSERT INTO documents (repo_url, file_path, content, chunk_index, embedding)
                VALUES %s
                ON CONFLICT (repo_url, file_path, chunk_index) 
                DO UPDATE SET 
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding
            """
            
            execute_values(cursor, query, rows)
            conn.commit()
            
            print(f"Stored {len(rows)} document chunks in database")
            
        except Exception as e:
            print(f"Error storing documents: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
    
    def ingest_repository(self, repo_url: str):
        """Main method to ingest a GitHub repository"""
        print(f"Starting ingestion for: {repo_url}")
        start_time = time.time()
        
        try:
            # Create documents
            documents = self.create_documents(repo_url)
            
            if not documents:
                print("No documents created. Skipping ingestion.")
                return
            
            # Generate embeddings
            embeddings = self.embed_documents(documents)
            
            # Store in database
            self.store_documents(repo_url, documents, embeddings)
            
            end_time = time.time()
            print(f"Ingestion completed in {end_time - start_time:.2f} seconds")
            
        except Exception as e:
            print(f"Ingestion failed: {e}")


if __name__ == "__main__":
    # Example usage
    loader = GitHubDataLoader()
    
    # Test with a sample repository
    test_repo = "https://github.com/EiPhyuSinn/GitHub-Portfolio-RAG"
    loader.ingest_repository(test_repo)
