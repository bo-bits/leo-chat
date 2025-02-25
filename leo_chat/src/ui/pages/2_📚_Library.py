import streamlit as st
import sys
from pathlib import Path
import logging
import asyncio
from typing import Dict, List, Optional
import pickle

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from src.scraping.scraper import ArticleScraper
from src.processing.processor import DocumentProcessor
from src.services.db_service import DatabaseService
from config.config import SCRAPING_SOURCES, INDEX_FILE
from bson import ObjectId

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def async_to_sync(coroutine):
    """Convert an async function to sync using a new event loop."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coroutine)

async def get_overall_stats() -> Dict:
    """Get overall document statistics."""
    db = DatabaseService()
    total_articles = await db.db.articles.count_documents({})
    indexed_articles = await db.db.articles.count_documents({"processed": True})
    return {
        "total_articles": total_articles,
        "indexed_articles": indexed_articles,
        "unindexed_articles": total_articles - indexed_articles
    }

async def get_source_stats() -> Dict[str, Dict]:
    """Get detailed statistics for each source."""
    db = DatabaseService()
    pipeline = [
        {
            "$group": {
                "_id": "$source",
                "total_articles": {"$sum": 1},
                "indexed_articles": {
                    "$sum": {"$cond": [{"$eq": ["$processed", True]}, 1, 0]}
                }
            }
        }
    ]
    cursor = db.db.articles.aggregate(pipeline)
    stats = await cursor.to_list(length=None)
    
    return {
        stat["_id"]: {
            "total_articles": stat["total_articles"],
            "indexed_articles": stat["indexed_articles"],
            "unindexed_articles": stat["total_articles"] - stat["indexed_articles"]
        } for stat in stats
    }

def display_stats_columns(stats: Dict, source_id: Optional[str] = None):
    """Display statistics in three columns."""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Saved Articles", stats["total_articles"])
    with col2:
        st.metric("Indexed", stats["indexed_articles"])
    with col3:
        st.metric("Not Indexed", stats["unindexed_articles"])
        if stats["unindexed_articles"] > 0:
            create_process_button(
                num_articles=stats["unindexed_articles"],
                button_text="Index Articles",
                source_id=source_id
            )

def source_section(source_id: str, source_url: str, stats: Dict):
    """Display a section for a specific source with scraping controls."""
    source_name = source_id.upper()
    source_stats = stats.get(source_id, {
        "total_articles": 0,
        "indexed_articles": 0,
        "unindexed_articles": 0
    })
    
    st.subheader(f"📰 {source_name}")
    st.markdown(f"Source URL: [{source_url}]({source_url})")
    
    display_stats_columns(source_stats, source_id=source_id)
    
    # Scraping controls
    num_articles = st.number_input(
        f"Number of articles to scrape from {source_name}",
        min_value=1,
        max_value=1000,
        value=10,
        key=f"num_articles_{source_id}"
    )
    
    # Container for scraping results
    scrape_container = st.empty()
    
    if st.button(f"Scrape {source_name}", key=f"scrape_{source_id}", type="primary"):
        with scrape_container.container():
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                scraper = ArticleScraper()
                
                def progress_callback(current, total, msg):
                    if total > 0:
                        progress = min(current/total, 1.0)
                        progress_bar.progress(progress)
                    status_text.text(msg)
                
                articles = asyncio.run(scraper.scrape_source(
                    source_id, 
                    num_articles,
                    progress_callback=progress_callback
                ))
                
                if articles:
                    progress_bar.progress(1.0)
                    status_text.text(f"Successfully saved {len(articles)} new articles")
                    st.success(f"Successfully scraped {len(articles)} new articles from {source_name}")
                    
                    # Process and index newly scraped articles immediately
                    process_status = st.empty()
                    process_progress = st.progress(0)
                    
                    try:
                        article_ids = [article["_id"] for article in articles]
                        
                        def update_progress(msg: str, progress: float):
                            process_status.text(msg)
                            process_progress.progress(progress)
                        
                        success = async_to_sync(
                            process_and_index_articles(
                                article_ids=article_ids,
                                progress_callback=update_progress
                            )
                        )
                        
                        if success:
                            st.success("Successfully processed and indexed articles!")
                            st.rerun()
                        else:
                            st.warning("No chunks were created during processing")
                    except Exception as e:
                        st.error(f"Error during processing and indexing: {str(e)}")
                        logger.error(f"Processing error: {str(e)}")
                else:
                    status_text.text("No new articles found")
                    st.warning(f"No new articles found from {source_name}")
            except Exception as e:
                st.error(f"Error scraping {source_name}: {str(e)}")
                logger.error(f"Scraping error: {str(e)}")

async def get_indexed_count() -> int:
    """Get number of indexed documents from MongoDB."""
    db = DatabaseService()
    return await db.db.chunks.count_documents({})

async def process_and_index_articles(article_ids: Optional[List[ObjectId]] = None, progress_callback=None) -> bool:
    """Process and index specific articles or all unprocessed ones.
    
    Args:
        article_ids: Optional list of specific article IDs to process. If None, processes all unindexed articles.
        progress_callback: Optional callback function(status_msg: str, progress: float) for UI updates
    """
    try:
        processor = DocumentProcessor()
        
        if progress_callback:
            progress_callback("Processing articles into chunks...", 0.25)
            
        # Process articles into chunks
        if article_ids:
            # Convert any dictionary IDs to ObjectId instances
            converted_ids = []
            for aid in article_ids:
                if isinstance(aid, dict) and '_id' in aid:
                    converted_ids.append(ObjectId(str(aid['_id'])))
                elif isinstance(aid, str):
                    converted_ids.append(ObjectId(aid))
                else:
                    converted_ids.append(aid)
            chunks = await processor.process_articles(converted_ids)
        else:
            chunks = await processor.process_articles(None)
            
        if chunks:
            if progress_callback:
                progress_callback(f"Indexing {len(chunks)} chunks...", 0.5)
                
            # Index the chunks
            await processor.index_chunks(chunks)
            
            if progress_callback:
                progress_callback("Processing and indexing complete!", 1.0)
            return True
            
        return False
    except Exception as e:
        logger.error(f"Error in process_and_index_articles: {e}")
        raise

def create_process_button(num_articles: int, article_ids: Optional[List[ObjectId]] = None, button_text: Optional[str] = None, source_id: Optional[str] = None):
    """Create a standardized processing button with progress tracking.
    
    Args:
        num_articles: Number of articles to process (for display purposes)
        article_ids: Optional list of specific article IDs to process
        button_text: Optional custom button text
        source_id: Optional source identifier for creating unique button keys
    """
    # Create unique button key based on context
    if article_ids:
        button_key = f"process_specific_{article_ids[0]}"
    else:
        button_key = f"process_all_{source_id or 'overall'}"
        
    button_text = button_text or f"Process & Index {num_articles} articles"
    
    if st.button(button_text, key=button_key, type="primary"):
        process_status = st.empty()
        process_progress = st.progress(0)
        
        try:
            def update_progress(msg: str, progress: float):
                process_status.text(msg)
                process_progress.progress(progress)
            
            success = async_to_sync(
                process_and_index_articles(
                    article_ids=article_ids,
                    progress_callback=update_progress
                )
            )
            
            if success:
                st.success("Successfully processed and indexed articles!")
                st.rerun()
            else:
                st.warning("No chunks were created during processing")
        except Exception as e:
            st.error(f"Error during processing and indexing: {str(e)}")
            logger.error(f"Processing error: {str(e)}")

def main():
    st.title("📚 Document Library")
    
    # Section 1: Overall Statistics
    overall_stats = async_to_sync(get_overall_stats())
    display_stats_columns(overall_stats, source_id=None)
    
    st.markdown("---")
    
    # Section 2: Source Statistics
    with st.expander("🔍 Sources", expanded=True):
        source_stats = async_to_sync(get_source_stats())
        
        for source_id, source_url in SCRAPING_SOURCES.items():
            source_section(source_id, source_url, source_stats)
            st.markdown("---")
    
    # Section 3: Advanced Settings
    with st.expander("⚙️ Advanced Settings"):
        st.warning("Danger Zone")
        if st.button("Reset Database", type="secondary"):
            if st.checkbox("I understand this will delete all indexed documents"):
                from src.reset_db import reset_database
                async_to_sync(reset_database())
                st.success("Database reset complete!")
                st.rerun()

if __name__ == "__main__":
    main()


