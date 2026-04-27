#!/usr/bin/env python3
"""
Streamlit UI for GitHub Portfolio RAG System
"""

import streamlit as st
import time
from rag_chain import RAGChain
from search import HybridSearch

# Page config
st.set_page_config(
    page_title="GitHub Portfolio RAG",
    page_icon="🔍",
    layout="centered"
)

# Initialize session state
if 'rag_chain' not in st.session_state:
    st.session_state.rag_chain = RAGChain()
if 'searcher' not in st.session_state:
    st.session_state.searcher = HybridSearch()

def main():
    st.title("🔍 GitHub Portfolio RAG System")
    st.markdown("Ask questions about indexed GitHub repositories")
    
    # Sidebar
    with st.sidebar:
        st.header("📊 System Info")
        
        # Show database stats
        try:
            with st.session_state.searcher.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM documents")
                doc_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM metrics")
                metrics_count = cursor.fetchone()[0]
                
                st.metric("📄 Documents", doc_count)
                st.metric("📈 Queries", metrics_count)
        except Exception as e:
            st.error(f"Database error: {e}")
    
    # Main chat interface
    st.header("💬 Ask About GitHub Repositories")
    
    # Chat history
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("What do you want to know about the repositories?"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            with st.spinner("Searching and generating response..."):
                try:
                    start_time = time.time()
                    result = st.session_state.rag_chain.ask_sensei(prompt)
                    response_time = time.time() - start_time
                    
                    # Add assistant message
                    st.session_state.messages.append({"role": "assistant", "content": result['response']})
                    
                    # Show metrics
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("⚡ Response Time", f"{response_time:.2f}s")
                    with col2:
                        if 'context_used' in result:
                            st.metric("📄 Context Chunks", len(result['context_used']))
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        # Rerun to display new messages
        st.rerun()
    
    # Repository management section
    st.header("📥 Repository Management")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Add Repository")
        repo_url = st.text_input("GitHub Repository URL", placeholder="https://github.com/username/repo")
        if st.button("📥 Ingest Repository", type="primary"):
            if repo_url:
                with st.spinner("Ingesting repository..."):
                    try:
                        from ingest import GitHubDataLoader
                        loader = GitHubDataLoader()
                        loader.ingest_repository(repo_url)
                        st.success(f"✅ Successfully ingested {repo_url}")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("Please enter a repository URL")
    
    with col2:
        st.subheader("Search Documents")
        search_query = st.text_input("Search Query", placeholder="Search in documents...")
        if st.button("🔍 Search"):
            if search_query:
                with st.spinner("Searching..."):
                    try:
                        results = st.session_state.searcher.hybrid_search(search_query, limit=5)
                        st.success(f"Found {len(results)} results")
                        
                        for i, result in enumerate(results, 1):
                            with st.expander(f"Result {i}: {result['file_path']}"):
                                st.code(result['content'][:500] + "..." if len(result['content']) > 500 else result['content'])
                                st.caption(f"Repository: {result['repo_url']}")
                    except Exception as e:
                        st.error(f"❌ Search error: {str(e)}")

if __name__ == "__main__":
    main()
