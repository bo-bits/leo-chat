import sys
from pathlib import Path
import asyncio
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.scraping.scraper import ArticleScraper
from src.indexing.indexer import DocumentIndexer
from config.config import DATA_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_database():
    """Run the complete pipeline to set up the database."""
    try:
        # 1. Scrape articles
        logger.info("Starting article scraping...")
        scraper = ArticleScraper()
        articles = await scraper.scrape_all_sources()
        logger.info(f"Scraped {len(articles)} articles")
        
        # 2. Process and index articles
        logger.info("Processing and indexing articles...")
        indexer = DocumentIndexer()
        
        # Process in batches
        batch_size = 10
        total_batches = (len(articles) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            try:
                logger.info(f"Processing batch {batch_num + 1}/{total_batches}")
                await indexer.process_and_index_all(batch_size)
            except Exception as e:
                logger.error(f"Error processing batch {batch_num + 1}: {e}")
        
        logger.info("Database setup complete!")
        
    except Exception as e:
        logger.error(f"Error during database setup: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(setup_database()) 