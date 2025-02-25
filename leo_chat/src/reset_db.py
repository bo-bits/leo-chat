import sys
from pathlib import Path
import logging
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from config.config import DATA_DIR, MONGODB_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reset_database():
    """Reset MongoDB collections and FAISS index."""
    # Delete FAISS index
    index_file = DATA_DIR / "faiss_index.index"
    if index_file.exists():
        index_file.unlink()
        logger.info("Deleted FAISS index")
    
    # Reset MongoDB
    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client.leo_chat
        
        # Drop collections
        await db.articles.drop()
        await db.chunks.drop()
        
        logger.info("MongoDB collections dropped")
        
    except Exception as e:
        logger.error(f"Error resetting MongoDB: {e}")
    
    logger.info("Database reset complete")

if __name__ == "__main__":
    asyncio.run(reset_database()) 