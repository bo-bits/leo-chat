import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import sys
from bson import ObjectId

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from config.config import EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, INDEX_FILE
from src.models.document import Article, Chunk
from src.services.db_service import DatabaseService

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Handles article processing, chunking, and indexing."""
    
    def __init__(self):
        self.db = DatabaseService()
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.index = self._load_or_create_index()
    
    def _create_chunks(self, text: str) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks."""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), CHUNK_SIZE - CHUNK_OVERLAP):
            chunk_words = words[i:i + CHUNK_SIZE]
            chunks.append({
                'text': ' '.join(chunk_words),
                'index': len(chunks)
            })
        
        return chunks
    
    def _load_or_create_index(self) -> faiss.Index:
        """Load existing FAISS index or create a new one."""
        if INDEX_FILE.exists():
            return faiss.read_index(str(INDEX_FILE))
        dimension = self.model.get_sentence_embedding_dimension()
        return faiss.IndexFlatL2(dimension)
    
    async def process_articles(self, article_ids: Optional[List[ObjectId]] = None) -> List[Chunk]:
        """Process specific articles or all unprocessed articles."""
        if article_ids:
            # Convert string IDs to ObjectId if needed
            articles = []
            for aid in article_ids:
                if isinstance(aid, dict) and '_id' in aid:
                    aid = aid['_id']
                article = await self.db.get_article(ObjectId(str(aid)))
                if article:
                    articles.append(article)
        else:
            # Get unprocessed articles with a default batch size of 100
            articles = await self.db.get_unprocessed_articles(batch_size=100)
        
        all_chunks = []
        for article in articles:
            if not article:
                continue
                
            # Create chunks
            chunks = self._create_chunks(article.content)
            chunk_objects = [
                Chunk(
                    text=chunk['text'],
                    chunk_index=chunk['index'],
                    article_id=article.id
                ) for chunk in chunks
            ]
            all_chunks.extend(chunk_objects)
            
            # Mark article as processed
            await self.db.mark_article_processed(article.id)
        
        return all_chunks
    
    async def index_chunks(self, chunks: List[Chunk], batch_size: int = 32):
        """Create embeddings and index chunks."""
        if not chunks:
            return
            
        # Create embeddings
        texts = [chunk.text for chunk in chunks]
        embeddings = self.model.encode(texts)
        
        # Add to FAISS index
        faiss_ids = list(range(self.index.ntotal, self.index.ntotal + len(embeddings)))
        self.index.add(embeddings)
        
        # Update chunks with FAISS IDs and save to MongoDB
        for chunk, faiss_id in zip(chunks, faiss_ids):
            chunk.faiss_id = faiss_id
        await self.db.insert_chunks(chunks)
        
        # Save updated index
        faiss.write_index(self.index, str(INDEX_FILE))
        logger.info(f"Indexed {len(chunks)} chunks. Total vectors: {self.index.ntotal}")

  