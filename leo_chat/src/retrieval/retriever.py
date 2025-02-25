import sys
from pathlib import Path
import logging
import pickle
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple
import torch
import numpy as np

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from config.config import EMBEDDING_MODEL, INDEX_FILE, MAX_RESULTS
from src.retrieval.data_sources import get_source_for_url, get_available_sources
from src.services.db_service import DatabaseService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentRetriever:
    def __init__(self):
        self.db = DatabaseService()
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        # Use MPS (Apple Silicon) if available, else CUDA, else CPU
        self.device = 'mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"Using device: {self.device}")
        self.model = self.model.to(self.device)
        
        # Load index
        self.index = self.load_index()
        
    def load_index(self) -> faiss.Index:
        """Load the FAISS index from disk."""
        try:
            index = faiss.read_index(str(INDEX_FILE))
            logger.info(f"Loaded FAISS index with {index.ntotal} vectors")
            return index
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}")
            raise

    async def search(self, query: str, k: int = MAX_RESULTS, sources: List[str] = None) -> List[Dict]:
        """Search for relevant documents."""
        # Encode query
        query_embedding = self.model.encode(query)
        
        # Search FAISS index
        D, I = self.index.search(np.array([query_embedding]), k)
        
        results = []
        for i, (distance, faiss_id) in enumerate(zip(D[0], I[0])):
            # Get chunk from MongoDB
            chunk = await self.db.get_chunk_by_faiss_id(int(faiss_id))
            if not chunk:
                continue
            
            # Get article
            article = await self.db.get_article(chunk.article_id)
            if not article:
                continue
            
            # Filter by source if specified
            if sources and article.source not in sources:
                continue
            
            # Calculate score (convert distance to similarity)
            score = 1 / (1 + distance)
            
            results.append({
                'chunk': {
                    'text': chunk.text,
                    'article_title': article.title,
                    'article_date': article.date_published.strftime('%A, %B %d, %Y'),
                    'article_url': article.url,
                    'source': article.source
                },
                'score': score,
                'rank': i + 1
            })
        
        return results

    def format_results(self, results: List[Dict]) -> str:
        """Format search results for display."""
        if not results:
            return "No relevant results found."
        
        formatted = []
        for result in results:
            chunk = result['chunk']
            score = result['score']
            rank = result['rank']
            
            formatted.append(
                f"Result {rank} (Relevance: {score:.3f}):\n"
                f"Article: {chunk['article_title']}\n"
                f"Date: {chunk['article_date']}\n"
                f"URL: {chunk['article_url']}\n"
                f"Excerpt: {chunk['text'][:300]}...\n"
            )
        
        return "\n\n".join(formatted)

    def test_queries(self):
        """Run some test queries to validate the retrieval system."""
        test_queries = [
            "What recent cases involve fraud?",
            "Tell me about drug trafficking cases",
            "Are there any cases involving cybercrime?",
            "What are some recent sentencing decisions?",
        ]
        
        print("\nRunning test queries...")
        for query in test_queries:
            print(f"\nQuery: {query}")
            results = self.search(query)
            print("\nResults:")
            print(self.format_results(results))
            print("-" * 80)

def main():
    """Test the retriever with sample queries."""
    retriever = DocumentRetriever()
    retriever.test_queries()

if __name__ == "__main__":
    main() 