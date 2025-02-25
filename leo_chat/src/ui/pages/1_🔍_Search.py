import streamlit as st
import sys
from pathlib import Path
import logging
import asyncio
from typing import List, Dict, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from src.retrieval.retriever import DocumentRetriever
from src.services.db_service import DatabaseService
from config.config import INDEX_FILE, MAX_RESULTS
from src.ui.Hello import async_to_sync

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_search_ready():
    """Check if the system is ready for searching."""
    try:
        db = DatabaseService()
        # Check for processed articles and chunks
        processed_articles = await db.db.articles.count_documents({"processed": True})
        chunk_count = await db.db.chunks.count_documents({})
        
        # Check FAISS index
        index_exists = INDEX_FILE.exists()
        
        logger.info(f"System status: processed_articles={processed_articles}, chunks={chunk_count}, index_exists={index_exists}")
        return processed_articles > 0 and chunk_count > 0 and index_exists
    except Exception as e:
        logger.error(f"Error checking search readiness: {e}")
        return False

def main():
    st.title("🔍 Search")
    
    # Check if system is ready for searching
    if not async_to_sync(check_search_ready()):
        st.warning("""
        📚 No Documents Found
        
        The search database is empty. Head to the [Library](/Library) page to:
        1. Add documents to the system
        2. View document statistics
        3. Manage your document sources
        """)
        return
        
    # Initialize retriever
    retriever = DocumentRetriever()
    
    # Search settings in sidebar
    st.sidebar.markdown("### ⚙️ Search Settings")
    num_results = st.sidebar.number_input(
        "Number of results to show",
        min_value=1,
        max_value=50,
        value=MAX_RESULTS,
        help="Choose how many search results to display"
    )
    
    # Example prompts
    st.sidebar.markdown("### 💡 Example Queries")
    example_queries = [
        "What are recent drug trafficking cases?",
        "Find cases involving firearms violations",
        "Show me cases about financial fraud",
        "What are some recent gang-related cases?",
        "Find cases involving cybercrime"
    ]
    
    for query in example_queries:
        if st.sidebar.button(query, key=f"example_{query}"):
            st.session_state.search_query = query
    
    # Search interface
    query = st.text_input("Enter your search query", value=st.session_state.get('search_query', ''))
    
    if query:
        try:
            results = async_to_sync(retriever.search(query, k=num_results))
            
            if results:
                st.markdown(f"### Results for: *{query}*")
                st.markdown(f"Showing top {len(results)} results")
                
                for result in results:
                    with st.expander(
                        f"**{result['chunk']['article_title']}** - {result['chunk']['article_date']} "
                        f"(Score: {result['score']:.2f})"
                    ):
                        st.markdown(result['chunk']['text'])
                        st.markdown(f"Source: [{result['chunk']['source'].upper()}]({result['chunk']['article_url']})")
            else:
                st.info("No matching results found.")
                
        except Exception as e:
            st.error(f"Error performing search: {str(e)}")
            logger.error(f"Search error: {str(e)}")

if __name__ == "__main__":
    main() 