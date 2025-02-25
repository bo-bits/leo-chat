import os
from pathlib import Path

# Base paths
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = DATA_DIR / "models"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

# Scraping settings
SCRAPING_SOURCES = {
    'usao': "https://www.justice.gov/usao-cdca/pr",
    'latimes': "https://homicide.latimes.com"
}
SCRAPE_DELAY = 1  # seconds between requests

# Text processing settings
CHUNK_SIZE = 300  # words
CHUNK_OVERLAP = 50  # words

# Model settings
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# FAISS settings
INDEX_FILE = DATA_DIR / "faiss_index.index"

# UI settings
MAX_RESULTS = 5  # number of relevant chunks to display

# Use environment variable for MongoDB URL if available
MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017") 