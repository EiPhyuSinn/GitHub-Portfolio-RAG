#!/usr/bin/env python3
"""
Simple GitHub ingestion without embeddings for testing
"""
import os
import re
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

class SimpleGitHubLoader:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.headers = {"Authorization": f"token {self.github_token}"} if self.github_token else {}
        
    def extract_repo_info(self, repo_url: str):
        match = re.match(r'https://github\.com/([^/]+)/([^/]+)', repo_url)
        if not match:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")
        return {"owner": match.group(1), "repo": match.group(2)}
    
    def fetch_readme_content(self, owner: str, repo: str):
        url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            readme_data = response.json()
            download_url = readme_data.get("download_url")
            
            if download_url:
                content_response = requests.get(download_url, headers=self.headers)
                content_response.raise_for_status()
                return content_response.text
            else:
                return ""
        except Exception as e:
            print(f"Error fetching README: {e}")
            return ""
    
    def fetch_file_tree(self, owner: str, repo: str):
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            tree_data = response.json()
            files = []
            for item in tree_data.get("tree", []):
                if item["type"] == "blob":
                    files.append({
                        "path": item["path"],
                        "size": item.get("size", 0)
                    })
            return files
        except Exception as e:
            print(f"Error fetching file tree: {e}")
            return []
    
    def store_simple_data(self, repo_url: str, readme_content: str, files: list):
        """Store data without embeddings for testing"""
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/rag_portfolio")
        
        try:
            # Use Docker exec to insert data
            import subprocess
            
            # Insert README content
            if readme_content:
                escaped_content = readme_content.replace("'", "''").replace('"', '""')
                cmd = f'''docker-compose exec postgres psql -U postgres -d rag_portfolio -c "INSERT INTO documents (repo_url, file_path, content, chunk_index, embedding) VALUES ('{repo_url}', 'README.md', '{escaped_content[:500]}...', 0, '{{0.1,0.2,0.3}}') ON CONFLICT (repo_url, file_path, chunk_index) DO UPDATE SET content = EXCLUDED.content;"'''
                
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ README content stored")
                else:
                    print(f"❌ Error storing README: {result.stderr}")
            
            # Insert file list
            if files:
                file_list = "\\n".join([f["path"] for f in files[:20]])  # Limit to 20 files
                escaped_files = file_list.replace("'", "''").replace('"', '""')
                cmd = f'''docker-compose exec postgres psql -U postgres -d rag_portfolio -c "INSERT INTO documents (repo_url, file_path, content, chunk_index, embedding) VALUES ('{repo_url}', 'file_structure', 'Files:\\n{escaped_files}', 1, '{{0.4,0.5,0.6}}') ON CONFLICT (repo_url, file_path, chunk_index) DO UPDATE SET content = EXCLUDED.content;"'''
                
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ File structure stored")
                else:
                    print(f"❌ Error storing files: {result.stderr}")
            
        except Exception as e:
            print(f"Error storing data: {e}")
    
    def ingest_repository(self, repo_url: str):
        print(f"Ingesting: {repo_url}")
        repo_info = self.extract_repo_info(repo_url)
        owner, repo = repo_info["owner"], repo_info["repo"]
        
        # Fetch data
        readme_content = self.fetch_readme_content(owner, repo)
        files = self.fetch_file_tree(owner, repo)
        
        print(f"README length: {len(readme_content)} chars")
        print(f"Files found: {len(files)}")
        
        # Store data
        self.store_simple_data(repo_url, readme_content, files)
        print("✅ Simple ingestion completed!")

if __name__ == "__main__":
    loader = SimpleGitHubLoader()
    loader.ingest_repository("https://github.com/octocat/Hello-World")
