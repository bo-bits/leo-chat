from abc import ABC, abstractmethod
from typing import List, Dict
import re

class DataSource(ABC):
    """Base class for all data sources."""
    
    @property
    @abstractmethod
    def source_id(self) -> str:
        """Unique identifier for this source."""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for the UI."""
        pass
    
    @abstractmethod
    def matches_url(self, url: str) -> bool:
        """Check if a URL belongs to this source."""
        pass

class USAOSource(DataSource):
    source_id = "usao"
    display_name = "U.S. Attorney's Office"
    
    def matches_url(self, url: str) -> bool:
        return "justice.gov/usao-cdca" in url

class LATimesSource(DataSource):
    source_id = "latimes"
    display_name = "LA Times Homicide Report"
    
    def matches_url(self, url: str) -> bool:
        return "homicide.latimes.com" in url

class LocalFileSource(DataSource):
    source_id = "local"
    display_name = "Local Files"
    
    def matches_url(self, url: str) -> bool:
        return url.startswith("file://")

# Registry of all available sources
SOURCES = {
    source.source_id: source() 
    for source in [USAOSource, LATimesSource, LocalFileSource]
}

def get_source_for_url(url: str) -> str:
    """Determine which source a URL belongs to."""
    for source_id, source in SOURCES.items():
        if source.matches_url(url):
            return source_id
    return None

def get_available_sources() -> List[Dict]:
    """Get list of all available sources for the UI."""
    return [
        {"id": source.source_id, "name": source.display_name}
        for source in SOURCES.values()
    ] 