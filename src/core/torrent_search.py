import requests
from bs4 import BeautifulSoup
import re
import time
from threading import Thread
from PyQt5.QtCore import QObject, pyqtSignal
import urllib.parse
import json

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
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'application/json'
        }
        self.search_providers = [
            self._search_thepiratebay
        ]
        self.results = []
        self.is_searching = False
        
    def search(self, query, max_results=50, display_domain=None):
        """
        Search for torrents across all providers
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            display_domain: The domain to display as the source for these results
        """
        if self.is_searching:
            self.search_error.emit("A search is already in progress")
            return
            
        self.is_searching = True
        self.results = []
        self.current_display_domain = display_domain
        
        search_thread = Thread(target=self._search_all_providers, args=(query, max_results))
        search_thread.daemon = True
        search_thread.start()
        
    def _search_all_providers(self, query, max_results):
        """Search all providers and aggregate results"""
        total_providers = len(self.search_providers)
        all_results = []
        
        for i, provider in enumerate(self.search_providers):
            try:
                provider_results = provider(query)
                all_results.extend(provider_results)
                
                # Update progress
                self.search_progress.emit(i + 1, total_providers)
                
            except Exception as e:
                # Continue with other providers if one fails
                self.search_error.emit(f"Error searching provider: {str(e)}")
        
        # Deduplicate results based on info hash
        seen_hashes = set()
        unique_results = []
        
        for result in all_results:
            # Extract info hash from magnet link
            info_hash = None
            if 'xt=urn:btih:' in result.magnet_link:
                info_hash = result.magnet_link.split('xt=urn:btih:')[1].split('&')[0].lower()
            
            if info_hash and info_hash not in seen_hashes:
                seen_hashes.add(info_hash)
                unique_results.append(result)
        
        # Sort by seeds and limit results
        unique_results.sort(key=lambda x: x.seeds, reverse=True)
        self.results = unique_results[:max_results]
        
        self.is_searching = False
        self.search_completed.emit(self.results)
        
    def _search_thepiratebay(self, query):
        """Search ThePirateBay for torrents"""
        results = []
        source_to_display = self.current_display_domain if hasattr(self, 'current_display_domain') and self.current_display_domain else "ThePirateBay"
        
        try:
            # Use TPB API
            encoded_query = urllib.parse.quote(query)
            url = f"https://apibay.org/q.php?q={encoded_query}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            torrents = response.json()
            
            for torrent in torrents:
                if torrent.get('name') and torrent.get('info_hash'):
                    # Convert size to human readable format
                    size_bytes = int(torrent.get('size', 0))
                    size = self._format_size(size_bytes)
                    
                    # Create magnet link
                    magnet_link = f"magnet:?xt=urn:btih:{torrent['info_hash']}&dn={urllib.parse.quote(torrent['name'])}"
                    
                    results.append(
                        TorrentSearchResult(
                            name=torrent['name'],
                            seeds=int(torrent.get('seeders', 0)),
                            leechers=int(torrent.get('leechers', 0)),
                            size=size,
                            magnet_link=magnet_link,
                            source=source_to_display
                        )
                    )
            
        except Exception as e:
            self.search_error.emit(f"Error searching ThePirateBay: {str(e)}")
            
        return results
        
    def _format_size(self, size_bytes):
        """Convert size in bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB" 