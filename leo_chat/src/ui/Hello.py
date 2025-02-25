import streamlit as st
print("Running app.py version 2.0")
st.cache_data.clear()
st.cache_resource.clear()

import sys
from pathlib import Path
import logging
import pickle
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Use relative imports
from src.retrieval.retriever import DocumentRetriever
from src.retrieval.data_sources import get_available_sources
from config.config import DATA_DIR, INDEX_FILE, MONGODB_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_database_initialized():
    """Check if the database has been initialized."""
    try:
        # Convert to async function and use async_to_sync
        async def check_db():
            # Connect to MongoDB
            client = AsyncIOMotorClient(MONGODB_URL)
            db = client.leo_chat
            
            # Check if we have processed articles
            processed_articles = await db.articles.count_documents({"processed": True})
            chunk_count = await db.chunks.count_documents({})
            
            # Check if FAISS index exists and we have processed articles and chunks
            if not INDEX_FILE.exists():
                return False
                
            return processed_articles > 0 and chunk_count > 0

        return async_to_sync(check_db())
    except Exception as e:
        logger.error(f"Error checking database initialization: {e}")
        return False

def async_to_sync(coroutine):
    """Convert an async function to sync using a new event loop."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coroutine)

def initialize_retriever():
    """Initialize the retriever with cached loading."""
    if not is_database_initialized():
        return None
        
    if 'retriever' not in st.session_state:
        try:
            st.session_state.retriever = DocumentRetriever()
            logger.info("Retriever initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing retriever: {e}")
            return None
    return st.session_state.retriever

def display_results(results):
    """Display search results in a clean format."""
    for result in results:
        chunk = result['chunk']
        score = result['score']
        
        # Create an expander for each result
        with st.expander(f"📄 {chunk['article_title']} (Relevance: {score:.3f})", expanded=True):
            # Article metadata
            st.markdown(f"**Date:** {chunk['article_date']}")
            st.markdown(f"**Source:** [Read full article]({chunk['article_url']})")
            
            # Article excerpt
            st.markdown("**Excerpt:**")
            st.markdown(chunk['text'])
            
            # Divider
            st.markdown("---")

def handle_search():
    """Handle the search when triggered by enter or button click."""
    if st.session_state.query:  # Only search if query is not empty
        st.session_state.search_performed = True
        with st.spinner("Searching..."):
            try:
                # Get results with source filtering
                results = st.session_state.retriever.search(
                    st.session_state.query, 
                    k=st.session_state.num_results,
                    sources=st.session_state.enabled_sources
                )
                
                # Filter by minimum score
                results = [r for r in results if r['score'] >= st.session_state.min_score]
                
                # Display results in main area
                if results:
                    st.success(f"Found {len(results)} relevant results")
                    display_results(results)
                else:
                    st.warning("No relevant results found. Try adjusting your search terms, lowering the minimum relevance score, or selecting additional data sources.")
                
            except Exception as e:
                logger.error(f"Error during search: {e}")
                st.error("An error occurred during the search. Please try again.")

def main():
    st.set_page_config(
        page_title="LEO-Chat",
        page_icon="👮",
        layout="wide"
    )
    
    st.title("👮 Welcome to LEO-Chat")
    
    # Check database status
    if not is_database_initialized():
        st.warning("""
        ### 📚 No Documents Found
        
        The search database is empty. Head to the [Library](Library) page to:
        1. Add documents to the system
        2. View document statistics
        3. Manage your document sources
        """)
    
    # Introduction
    st.markdown("""
    LEO-Chat is a secure, local intelligence tool that enables law enforcement personnel to efficiently 
    query and analyze press releases from the U.S. Attorney's Office (Central District of California).
    
    ### Key Features
    - 🔍 **Semantic Search**: Find relevant documents based on meaning, not just keywords
    - 🏢 **Multiple Sources**: Search across USAO press releases and other supported sources
    - 💻 **Local Processing**: All data processing and search happens on your machine
    - 📄 **Document Upload**: Support for PDF, DOCX, and TXT files
    - ⚙️ **Configurable**: Adjust relevance scores and number of results
    - 🔒 **Secure**: No external API calls or data transmission
    """)
    
    # Navigation section
    st.markdown("### Navigation")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("""
        **🔍 Search**
        
        Search through press releases and documents using natural language queries.
        
        [Go to Search](Search)
        """)
    
    with col2:
        st.info("""
        **📚 Library**
        
        Browse all indexed documents and view source statistics.
        
        [Go to Library](Library)
        """)
    
    with col3:
        st.info("""
        **⚙️ Settings**
        
        Configure search parameters and manage data sources.
        
        Access via Search page sidebar
        """)
    
    # Security note
    st.markdown("---")
    st.markdown("""
    ### Security Note
    This tool operates entirely offline. All processing happens locally on your machine, making it 
    suitable for handling sensitive information. No data is sent to external services.
    
    ### Getting Started
    1. Go to the **Search** page
    2. Use the sidebar to configure search settings
    3. Enter your query or try an example question
    4. View results with relevance scores
    
    ### Need Help?
    - Check the sidebar in the Search page for example questions
    - Use the Library page to browse available documents
    - Adjust search settings to refine results
    """)

if __name__ == "__main__":
    main() 