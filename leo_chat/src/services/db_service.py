from typing import List, Optional, Dict
from datetime import datetime
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, TEXT
from bson import ObjectId
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from config.config import MONGODB_URL
from src.models.document import Article, Chunk

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URL)
        self.db = self.client.leo_chat
        self._setup_indexes()
    
    async def _setup_indexes(self):
        """Create necessary indexes."""
        # Articles collection
        await self.db.articles.create_index([("url", ASCENDING)], unique=True)
        await self.db.articles.create_index([("title", TEXT)])
        await self.db.articles.create_index([("source", ASCENDING)])
        await self.db.articles.create_index([("date_published", ASCENDING)])
        
        # Chunks collection
        await self.db.chunks.create_index([("article_id", ASCENDING)])
        await self.db.chunks.create_index([("faiss_id", ASCENDING)], unique=True)
    
    async def article_exists(self, url: str) -> bool:
        """Check if an article with the given URL exists."""
        count = await self.db.articles.count_documents({"url": url})
        return count > 0
    
    async def get_articles_by_source(self, source: str) -> List[Dict]:
        """Get all articles from a specific source."""
        cursor = self.db.articles.find({"source": source})
        return await cursor.to_list(length=None)
    
    async def insert_article(self, article: Article) -> ObjectId:
        """Insert a new article, updating if URL already exists."""
        try:
            result = await self.db.articles.update_one(
                {"url": article.url},
                {"$set": article.dict(by_alias=True)},
                upsert=True
            )
            return result.upserted_id or result.modified_count
        except Exception as e:
            logger.error(f"Error inserting article: {e}")
            raise
    
    async def insert_chunks(self, chunks: List[Chunk]):
        """Insert multiple chunks at once."""
        if not chunks:
            return
        
        chunk_docs = [chunk.dict(by_alias=True) for chunk in chunks]
        await self.db.chunks.insert_many(chunk_docs)
    
    async def get_article(self, article_id: ObjectId) -> Optional[Article]:
        """Get article by ID."""
        doc = await self.db.articles.find_one({"_id": article_id})
        if doc:
            return Article(**doc)
        return None
    
    async def get_chunks_by_article(self, article_id: ObjectId) -> List[Chunk]:
        """Get all chunks for an article."""
        cursor = self.db.chunks.find({"article_id": article_id})
        chunks = await cursor.to_list(length=None)
        return [Chunk(**chunk) for chunk in chunks]
    
    async def get_chunk_by_faiss_id(self, faiss_id: int) -> Optional[Chunk]:
        """Get chunk by its FAISS index ID."""
        doc = await self.db.chunks.find_one({"faiss_id": faiss_id})
        if doc:
            return Chunk(**doc)
        return None
    
    async def get_indexed_articles_count(self, source: str) -> int:
        """Get count of articles that have been processed and indexed."""
        return await self.db.articles.count_documents({
            "source": source,
            "processed": True
        })
    
    async def get_source_stats(self):
        """Get statistics for each source."""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": "$source",
                        "total_articles": {"$sum": 1},
                        "indexed_articles": {
                            "$sum": {
                                "$cond": [
                                    {"$eq": [{"$ifNull": ["$processed", False]}, True]},
                                    1,
                                    0
                                ]
                            }
                        },
                        "latest_date": {"$max": "$date_published"}
                    }
                }
            ]
            cursor = self.db.articles.aggregate(pipeline)
            stats = await cursor.to_list(length=None)
            
            # Ensure each source has all required fields with default values
            processed_stats = []
            for stat in stats:
                processed_stat = {
                    "_id": stat["_id"],
                    "total_articles": stat.get("total_articles", 0),
                    "indexed_articles": stat.get("indexed_articles", 0),
                    "latest_date": stat.get("latest_date")
                }
                processed_stats.append(processed_stat)
            
            return processed_stats
        except Exception as e:
            logger.error(f"Error getting source stats: {e}")
            # Return empty stats as fallback
            return []
    
    async def get_unprocessed_articles(self, batch_size: int) -> List[Article]:
        """Get articles that haven't been processed into chunks yet."""
        cursor = self.db.articles.find(
            {"processed": {"$ne": True}},
            limit=batch_size
        )
        docs = await cursor.to_list(length=batch_size)
        return [Article(**doc) for doc in docs]
    
    async def mark_article_processed(self, article_id: ObjectId):
        """Mark an article as processed."""
        await self.db.articles.update_one(
            {"_id": article_id},
            {"$set": {"processed": True}}
        )
    
    async def get_recent_articles(self, source: str, limit: int) -> List[Dict]:
        """Get the most recently added articles from a specific source."""
        cursor = self.db.articles.find(
            {"source": source},
            sort=[("date_ingested", -1)],
            limit=limit
        )
        return await cursor.to_list(length=limit) 