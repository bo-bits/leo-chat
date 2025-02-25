import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from pathlib import Path
import json
import logging
from datetime import datetime
import re
from urllib.parse import urljoin
import sys
from abc import ABC, abstractmethod

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Update the import to use relative path
from config.config import DATA_DIR, SCRAPE_DELAY, SCRAPING_SOURCES
from src.services.db_service import DatabaseService
from src.models.document import Article

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base class for article scrapers."""
    
    def __init__(self, base_url: str, max_articles: Optional[int] = None):
        self.base_url = base_url
        self.max_articles = max_articles
        self.db = DatabaseService()
        self.new_articles_found = 0  # Track new articles found
        self.max_pages_without_new = 10  # Increased from 5 to 10 pages
        self.pages_without_new = 0  # Counter for pages without new articles
    
    @abstractmethod
    def parse_article_links(self, html: str) -> List[str]:
        pass
        
    @abstractmethod
    def scrape_article(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
        pass

    async def _save_article(self, article_data: Dict) -> bool:
        """Save article if it doesn't exist and we haven't reached max_articles."""
        try:
            if self.max_articles and self.new_articles_found >= self.max_articles:
                return False
                
            # Check if article exists
            exists = await self.db.article_exists(article_data['url'])
            if exists:
                return False
            
            # Create and save article
            article = Article(
                title=article_data['title'],
                content=article_data['content'],
                url=article_data['url'],
                source=article_data['source'],
                date_published=datetime.strptime(article_data['date'], '%Y-%m-%d'),
                processed=False
            )
            await self.db.insert_article(article)
            self.new_articles_found += 1
            return True
            
        except Exception as e:
            logger.error(f"Error saving article: {e}")
            return False

    async def _article_exists(self, url: str) -> bool:
        """Check if article already exists in MongoDB."""
        return await self.db.article_exists(url)

    def get_page_url(self, page: int) -> str:
        """Generate URL for a specific page number."""
        if page == 0:
            return self.base_url
        return f"{self.base_url}?page={page}"

    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Fetch a single page with error handling and retries."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.text()
                    logger.warning(f"Failed to fetch {url}, status: {response.status}")
                    return None
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Error fetching {url}: {e}")
                    return None
                await asyncio.sleep(1)
        return None

    def clean_text(self, text: str) -> str:
        """Clean extracted text content."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        # Remove special characters
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        return text

    async def scrape_all_articles(self):
        """Main method to scrape all articles with pagination."""
        async with aiohttp.ClientSession() as session:
            page = 0
            new_articles = 0
            consecutive_empty_pages = 0
            max_empty_pages = 5  # Stop after this many pages with no new articles
            
            while True:
                # Check if we've reached the maximum articles limit
                if self.max_articles and self.new_articles_found >= self.max_articles:
                    logger.info(f"Reached maximum articles limit ({self.max_articles})")
                    break
                
                # Get current page URL
                page_url = self.get_page_url(page)
                logger.info(f"Fetching page {page + 1}...")
                
                # Get page content
                html = await self.fetch_page(session, page_url)
                if not html:
                    logger.error(f"Failed to fetch page {page + 1}")
                    break

                # Get article links from current page
                article_links = self.parse_article_links(html)
                if not article_links:
                    logger.info(f"No articles found on page {page + 1}")
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= max_empty_pages:
                        logger.info(f"No new articles found in {max_empty_pages} consecutive pages. Stopping.")
                        break

                # Process articles
                page_new_articles = 0
                for url in article_links:
                    # Check if we've reached the maximum articles limit
                    if self.max_articles and self.new_articles_found >= self.max_articles:
                        break
                        
                    if await self._article_exists(url):
                        logger.debug(f"Skipping existing article: {url}")
                        continue
                        
                    article = await self.scrape_article(session, url)
                    if article:
                        try:
                            if await self._save_article(article):
                                new_articles += 1
                                page_new_articles += 1
                                logger.info(f"Saved new article: {article['title']}")
                        except Exception as e:
                            logger.error(f"Error saving article {article['title']}: {e}")
                    
                    await asyncio.sleep(SCRAPE_DELAY)
                
                # Reset or increment consecutive empty pages counter
                if page_new_articles > 0:
                    consecutive_empty_pages = 0
                    logger.info(f"Found {page_new_articles} new articles on page {page + 1}")
                else:
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= max_empty_pages:
                        logger.info(f"No new articles found in {max_empty_pages} consecutive pages. Stopping.")
                        break
                
                page += 1
                await asyncio.sleep(SCRAPE_DELAY)

            logger.info(f"Finished scraping: {new_articles} new articles added (total: {self.new_articles_found} articles)")

class USAOScraper(BaseScraper):
    """Scraper for U.S. Attorney's Office press releases."""
    
    def __init__(self, max_articles: Optional[int] = None):
        super().__init__('https://www.justice.gov', max_articles)
        self.section_path = '/usao-cdca/pr'  # Path for Central District of California press releases
    
    async def scrape_all_articles(self) -> int:
        """Scrape articles from USAO website."""
        page = 0  # USAO site uses 0-based pagination
        
        async with aiohttp.ClientSession() as session:
            while True:
                if self.max_articles and self.new_articles_found >= self.max_articles:
                    break
                    
                if self.pages_without_new >= self.max_pages_without_new:
                    logger.info(f"Stopping after {self.max_pages_without_new} pages without new articles")
                    break
                
                url = f"{self.base_url}{self.section_path}?page={page}"
                logger.info(f"Fetching page {page} from {url}")
                
                html = await self.fetch_page(session, url)
                if not html:
                    break
                
                # Get article links from page
                article_links = self.parse_article_links(html)
                if not article_links:
                    break
                
                # Track if we found any new articles on this page
                new_on_page = 0
                
                for link in article_links:
                    # Skip if we've reached max articles
                    if self.max_articles and self.new_articles_found >= self.max_articles:
                        break
                        
                    # Skip if article already exists
                    if await self._article_exists(link):
                        continue
                    
                    # Scrape article
                    article = await self.scrape_article(session, link)
                    if not article:
                        continue
                    
                    try:
                        if await self._save_article(article):
                            new_on_page += 1
                            logger.info(f"Saved new article: {article['title']} ({self.new_articles_found}/{self.max_articles if self.max_articles else 'unlimited'})")
                    except Exception as e:
                        logger.error(f"Error saving article {article['title']}: {e}")
                
                if new_on_page == 0:
                    self.pages_without_new += 1
                else:
                    self.pages_without_new = 0  # Reset counter when we find new articles
                    
                page += 1
                await asyncio.sleep(SCRAPE_DELAY)
        
        return self.new_articles_found

    def parse_article_links(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        # The news articles are typically in the main content area
        # Try multiple possible selectors as the site structure might vary
        selectors = [
            'div.views-row a',  # Common Drupal view structure
            'div.field-content a',  # Alternative Drupal structure
            'h2.node-title a',  # Another common pattern
            'div.view-content a',  # Generic view content
            'article a',  # Generic article links
        ]
        
        for selector in selectors:
            found_links = soup.select(selector)
            for link in found_links:
                href = link.get('href')
                if href and '/usao-cdca/pr/' in href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in links:  # Avoid duplicates
                        links.append(full_url)
        
        # If we still don't find links, try a more generic approach
        if not links:
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/usao-cdca/pr/' in href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in links:
                        links.append(full_url)
        
        logger.info(f"Found {len(links)} article links")
        
        # Add debug information if no links are found
        if not links:
            logger.debug("HTML structure:")
            logger.debug(soup.prettify()[:1000])  # First 1000 chars for debugging
            
        return links

    async def scrape_article(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
        """Scrape a single article with content cleaning."""
        if await self._article_exists(url):
            logger.info(f"Skipping already scraped article: {url}")
            return None

        html = await self.fetch_page(session, url)
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title - try multiple selectors
            title_selectors = [
                'h1.page-title',
                'h1.usa-page-title',
                'h1.node-title',
                'h1'  # fallback
            ]
            title = None
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.text.strip()
                    break
            title = title or "Untitled"
            
            # Updated date extraction and parsing
            date_selectors = [
                'span.date-display-single',
                'time',
                'div.submitted',
                'meta[property="article:published_time"]'
            ]
            date_str = None
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_str = date_elem.get('content', '') or date_elem.text
                    date_str = date_str.strip()
                    break
            
            # Parse and format the date
            try:
                if date_str:
                    # Try parsing various date formats
                    for fmt in [
                        '%A, %B %d, %Y',  # Wednesday, February 5, 2025
                        '%Y-%m-%d',       # 2025-02-05
                        '%B %d, %Y',      # February 5, 2025
                        '%m/%d/%Y',       # 02/05/2025
                    ]:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            date_str = parsed_date.strftime('%Y-%m-%d')
                            break
                        except ValueError:
                            continue
                
                # If parsing fails, use current date
                if not date_str:
                    date_str = datetime.now().strftime('%Y-%m-%d')
            except Exception as e:
                logger.warning(f"Error parsing date '{date_str}': {e}. Using current date.")
                date_str = datetime.now().strftime('%Y-%m-%d')
            
            # Extract content - Updated selectors and logic for USAO website
            content = ""
            
            # First try the main article content div
            content_elem = soup.select_one('div.field-name-body div.field-items div.field-item')
            
            if content_elem:
                # Remove unwanted elements
                for unwanted in content_elem.select('script, style, nav, header, footer, .usa-banner, .usa-nav, .usa-menu-btn'):
                    unwanted.decompose()
                
                # Get all paragraphs
                paragraphs = content_elem.find_all('p')
                content = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            
            # If no content found, try alternative selectors
            if not content:
                alternative_selectors = [
                    'div.field-name-body',
                    'article div.usa-prose',
                    'main article',
                    'div[property="content:encoded"]'
                ]
                
                for selector in alternative_selectors:
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        # Remove unwanted elements
                        for unwanted in content_elem.select('script, style, nav, header, footer, .usa-banner, .usa-nav, .usa-menu-btn'):
                            unwanted.decompose()
                        
                        # Get all paragraphs
                        paragraphs = content_elem.find_all('p')
                        content = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                        if content:
                            break
            
            content = self.clean_text(content)
            
            if not content:
                logger.warning(f"No content found for article: {url}")
                # Log the HTML structure for debugging
                logger.debug(f"HTML structure for {url}:")
                logger.debug(soup.prettify()[:2000])  # First 2000 chars
                return None

            # Add debug logging for content
            logger.debug(f"Extracted content preview: {content[:200]}...")

            article = {
                'url': url,
                'title': title,
                'date': date_str,  # This will now be in YYYY-MM-DD format
                'content': content,
                'scraped_at': datetime.now().isoformat(),
                'source': 'usao'
            }
            
            logger.info(f"Successfully scraped article: {title}")
            return article

        except Exception as e:
            logger.error(f"Error parsing article {url}: {e}")
            return None

class LATimesScraper(BaseScraper):
    def __init__(self, max_articles: Optional[int] = None):
        super().__init__(SCRAPING_SOURCES['latimes'], max_articles)

    async def scrape_all_articles(self) -> int:
        """Scrape all articles from LA Times Homicide Report."""
        page = 0
        new_articles = 0
        
        async with aiohttp.ClientSession() as session:
            while True:
                if self.max_articles and self.new_articles_found >= self.max_articles:
                    break
                    
                url = self.get_page_url(page)
                html = await self.fetch_page(session, url)
                if not html:
                    break
                
                # Get article links from page
                article_links = self.parse_article_links(html)
                if not article_links:
                    break
                
                # Process articles on this page
                page_new_articles = 0
                for link in article_links:
                    if self.max_articles and self.new_articles_found >= self.max_articles:
                        break
                        
                    # Skip if article already exists
                    if await self._article_exists(link):
                        continue
                    
                    # Scrape article
                    article = await self.scrape_article(session, link)
                    if not article:
                        continue
                    
                    try:
                        if await self._save_article(article):
                            new_articles += 1
                            page_new_articles += 1
                            logger.info(f"Saved new article: {article['title']}")
                    except Exception as e:
                        logger.error(f"Error saving article {article['title']}: {e}")
                
                if page_new_articles == 0:
                    # No new articles on this page, stop scraping
                    break
                    
                page += 1
                await asyncio.sleep(SCRAPE_DELAY)
        
        return new_articles

    # These methods are not used since we're using the API
    def parse_article_links(self, html: str) -> List[str]:
        return []
        
    async def scrape_article(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
        return None

class ArticleScraper:
    """Main scraper class that coordinates scraping from multiple sources."""
    
    def __init__(self):
        self.scrapers = {
            'usao': USAOScraper,
            'latimes': LATimesScraper
        }
        self.db = DatabaseService()
    
    async def scrape_source(self, source: str, num_articles: int, progress_callback=None) -> List[Dict]:
        """Scrape articles from a specific source."""
        if source not in self.scrapers:
            raise ValueError(f"Unknown source: {source}")
            
        scraper = self.scrapers[source](max_articles=num_articles)
        
        async def scrape_with_progress():
            if progress_callback:
                progress_callback(0, num_articles, "Starting scraper...")
                
                original_save = scraper._save_article
                articles_processed = 0
                
                async def save_with_progress(article_data):
                    nonlocal articles_processed
                    success = await original_save(article_data)
                    if success:
                        articles_processed += 1
                        progress_callback(
                            min(articles_processed, num_articles),
                            num_articles,
                            f"Saved: {article_data.get('title', 'Unknown article')} ({articles_processed} of {num_articles})"
                        )
                    return success
                
                scraper._save_article = save_with_progress
            
            new_articles_count = await scraper.scrape_all_articles()
            return new_articles_count
        
        new_count = await scrape_with_progress()
        if new_count == 0:
            return []
            
        # Return only the newly scraped articles
        articles = await self.db.get_recent_articles(source, limit=new_count)
        return articles

    async def scrape_all_sources(self) -> List[Dict]:
        """Scrape articles from all configured sources."""
        all_articles = []
        for source in self.scrapers:
            try:
                scraper = self.scrapers[source]()
                await scraper.scrape_all_articles()
                articles = await self.db.get_articles_by_source(source)
                all_articles.extend(articles)
            except Exception as e:
                logger.error(f"Error scraping {source}: {e}")
        return all_articles

async def run_scrapers(max_articles: Optional[int], sources: List[str], concurrent: bool = False):
    """
    Run the specified scrapers either sequentially or concurrently.
    
    Args:
        max_articles: Maximum number of articles to scrape per source
        sources: List of source names to scrape
        concurrent: If True, run scrapers concurrently; if False, run sequentially
    """
    scrapers = {
        'usao': lambda: USAOScraper(max_articles=max_articles),
        'latimes': lambda: LATimesScraper(max_articles=max_articles)
    }
    
    if concurrent:
        tasks = [scrapers[source]().scrape_all_articles() for source in sources]
        await asyncio.gather(*tasks)
    else:
        for source in sources:
            scraper = scrapers[source]()
            await scraper.scrape_all_articles()

def main():
    """Entry point for running the scrapers."""
    import argparse
    parser = argparse.ArgumentParser(description='Scrape articles from multiple sources')
    parser.add_argument('--max-articles', type=int, 
                       help='Maximum number of articles to scrape per source (default: unlimited)')
    parser.add_argument('--sources', nargs='+', choices=['usao', 'latimes'], 
                       default=['usao', 'latimes'],  # Changed to include both sources by default
                       help='Which sources to scrape (default: both usao and latimes)')
    parser.add_argument('--concurrent', action='store_true',
                       default=True,  # Changed to run concurrently by default
                       help='Run scrapers concurrently instead of sequentially (default: True)')
    args = parser.parse_args()
    
    asyncio.run(run_scrapers(args.max_articles, args.sources, args.concurrent))

if __name__ == "__main__":
    main() 