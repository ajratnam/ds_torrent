import requests
from bs4 import BeautifulSoup
import re
import time
from threading import Thread
from PyQt5.QtCore import QObject, pyqtSignal

class TorrentSearchResult:
    """Class representing a single torrent search result"""
    def __init__(self, name, seeds, leechers, size, magnet_link, source):
        self.name = name
        self.seeds = seeds
        self.leechers = leechers
        self.size = size
        self.magnet_link = magnet_link
        self.source = source
        
    def __str__(self):
        return f"{self.name} - {self.size} - Seeds: {self.seeds} - Leechers: {self.leechers}"


class TorrentSearchEngine(QObject):
    """Search engine for finding torrents across multiple sites"""
    search_completed = pyqtSignal(list)
    search_error = pyqtSignal(str)
    search_progress = pyqtSignal(int, int)
    
    def __init__(self):
        super().__init__()
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        self.headers = {'User-Agent': self.user_agent}
        self.search_providers = [
            self._search_thepiratebay,
            self._search_1337x,
            # Add more providers as needed
        ]
        self.results = []
        self.is_searching = False
        
    def search(self, query, max_results=50):
        """
        Search for torrents across all providers
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
        """
        if self.is_searching:
            self.search_error.emit("A search is already in progress")
            return
            
        self.is_searching = True
        self.results = []
        
        search_thread = Thread(target=self._search_all_providers, args=(query, max_results))
        search_thread.daemon = True
        search_thread.start()
        
    def _search_all_providers(self, query, max_results):
        """Search all providers and aggregate results"""
        total_providers = len(self.search_providers)
        
        for i, provider in enumerate(self.search_providers):
            try:
                provider_results = provider(query)
                self.results.extend(provider_results)
                
                # Sort by seeds
                self.results.sort(key=lambda x: x.seeds, reverse=True)
                
                # Limit results
                self.results = self.results[:max_results]
                
                # Update progress
                self.search_progress.emit(i + 1, total_providers)
                
            except Exception as e:
                # Continue with other providers if one fails
                self.search_error.emit(f"Error searching provider: {str(e)}")
        
        self.is_searching = False
        self.search_completed.emit(self.results)
        
    def _search_thepiratebay(self, query):
        """Search ThePirateBay for torrents"""
        results = []
        
        try:
            # Simulate search - in a real app, you would implement actual API calls
            # This is a simplified example to show the structure
            url = f"https://thepiratebay.org/search/{query}/0/99/0"
            
            # Note: In a production app, you'd need to handle actual site structure
            # This is just a placeholder for demonstration purposes
            results.append(
                TorrentSearchResult(
                    name=f"Sample TPB result for: {query}",
                    seeds=100,
                    leechers=10,
                    size="1.5 GB",
                    magnet_link="magnet:?xt=urn:btih:SAMPLE_HASH&dn=Sample",
                    source="ThePirateBay"
                )
            )
            
            # Sleep to simulate network delay
            time.sleep(0.5)
            
        except Exception as e:
            self.search_error.emit(f"Error searching ThePirateBay: {str(e)}")
            
        return results
        
    def _search_1337x(self, query):
        """Search 1337x for torrents"""
        results = []
        
        try:
            # Simulate search - in a real app, you would implement actual API calls
            # This is a simplified example to show the structure
            url = f"https://1337x.to/search/{query}/1/"
            
            # Note: In a production app, you'd need to handle actual site structure
            # This is just a placeholder for demonstration purposes
            results.append(
                TorrentSearchResult(
                    name=f"Sample 1337x result for: {query}",
                    seeds=200,
                    leechers=20,
                    size="2.5 GB",
                    magnet_link="magnet:?xt=urn:btih:SAMPLE_HASH_1337X&dn=Sample",
                    source="1337x"
                )
            )
            
            # Sleep to simulate network delay
            time.sleep(0.5)
            
        except Exception as e:
            self.search_error.emit(f"Error searching 1337x: {str(e)}")
            
        return results 