import sys
from pathlib import Path
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List
import mimetypes
from docx import Document
from PyPDF2 import PdfReader

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from config.config import DATA_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LocalFileIngester:
    """Handles ingestion of local files into the article database."""
    
    SUPPORTED_EXTENSIONS = {
        '.txt': 'text/plain',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.pdf': 'application/pdf'
    }
    
    def __init__(self):
        self.articles_dir = DATA_DIR / "articles"
        self.articles_dir.mkdir(exist_ok=True)
    
    def read_text_file(self, file_path: Path) -> str:
        """Read content from a text file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def read_docx_file(self, file_path: Path) -> str:
        """Read content from a .docx file."""
        doc = Document(file_path)
        return '\n'.join(paragraph.text for paragraph in doc.paragraphs if paragraph.text)
    
    def read_pdf_file(self, file_path: Path) -> str:
        """Read content from a PDF file."""
        reader = PdfReader(file_path)
        text = []
        for page in reader.pages:
            text.append(page.extract_text())
        return '\n'.join(text)
        
    def ingest_file(self, file_path: Path, metadata: Optional[Dict] = None) -> bool:
        """
        Ingest a single file into the articles database.
        
        Args:
            file_path: Path to the file to ingest
            metadata: Optional dictionary of metadata about the file
        """
        try:
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return False
            
            # Check file extension
            extension = file_path.suffix.lower()
            if extension not in self.SUPPORTED_EXTENSIONS:
                logger.error(f"Unsupported file type: {extension}")
                return False
            
            # Read content based on file type
            try:
                if extension == '.txt':
                    content = self.read_text_file(file_path)
                elif extension == '.docx':
                    content = self.read_docx_file(file_path)
                elif extension == '.pdf':
                    content = self.read_pdf_file(file_path)
                else:
                    logger.error(f"Unexpected file type: {extension}")
                    return False
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                return False
            
            # Create article object
            article = {
                'url': f"file://{file_path.absolute()}",
                'title': metadata.get('title', file_path.stem),
                'date': metadata.get('date', datetime.now().strftime('%Y-%m-%d')),
                'content': content,
                'scraped_at': datetime.now().isoformat(),
                'metadata': {
                    'source': 'local',
                    'file_path': str(file_path),
                    'file_type': extension[1:],  # Remove the dot
                    **(metadata or {})
                }
            }
            
            # Save article
            safe_title = ''.join(c for c in article['title'] if c.isalnum() or c in (' ', '-', '_'))
            filename = self.articles_dir / f"{safe_title[:50]}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(article, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Successfully ingested {file_path} to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error ingesting file {file_path}: {e}")
            return False
    
    def ingest_directory(self, dir_path: Path, extensions: List[str] = None, recursive: bool = True) -> int:
        """
        Ingest files from a directory with specified extensions.
        
        Args:
            dir_path: Path to directory to scan
            extensions: List of file extensions to process (e.g., ['.pdf', '.docx'])
            recursive: Whether to scan subdirectories
        """
        try:
            if not dir_path.exists():
                logger.error(f"Directory not found: {dir_path}")
                return 0
            
            # Use specified extensions or all supported ones
            valid_extensions = [ext.lower() for ext in (extensions or self.SUPPORTED_EXTENSIONS.keys())]
            
            # Find all matching files
            pattern = '**/*' if recursive else '*'
            files = []
            for ext in valid_extensions:
                files.extend(dir_path.glob(f"{pattern}{ext}"))
            
            success_count = 0
            for file_path in files:
                if self.ingest_file(file_path):
                    success_count += 1
            
            logger.info(f"Successfully ingested {success_count} files from {dir_path}")
            return success_count
            
        except Exception as e:
            logger.error(f"Error ingesting directory {dir_path}: {e}")
            return 0

def main():
    """Command line interface for file ingestion."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ingest local files into the article database')
    parser.add_argument('path', type=Path, help='File or directory to ingest')
    parser.add_argument('--recursive', '-r', action='store_true', help='Recursively scan directories')
    parser.add_argument('--extensions', '-e', nargs='+', 
                       choices=['.txt', '.docx', '.pdf'],
                       default=['.txt', '.docx', '.pdf'],
                       help='File extensions to process')
    
    args = parser.parse_args()
    ingester = LocalFileIngester()
    
    if args.path.is_file():
        ingester.ingest_file(args.path)
    elif args.path.is_dir():
        ingester.ingest_directory(args.path, args.extensions, args.recursive)
    else:
        logger.error(f"Path not found: {args.path}")

if __name__ == "__main__":
    main() 