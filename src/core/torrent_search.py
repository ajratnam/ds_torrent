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
        self.headers = {'User-Agent': self.user_agent}
        self.search_providers = [
            self._search_thepiratebay,
            self._search_1337x,
            self._search_rarbg
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
                            source="ThePirateBay"
                        )
                    )
            
        except Exception as e:
            self.search_error.emit(f"Error searching ThePirateBay: {str(e)}")
            
        return results
        
    def _search_1337x(self, query):
        """Search 1337x for torrents"""
        results = []
        
        try:
            # Use 1337x API
            encoded_query = urllib.parse.quote(query)
            url = f"https://apibay.org/1337x.php?q={encoded_query}"
            
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
                            source="1337x"
                        )
                    )
            
        except Exception as e:
            self.search_error.emit(f"Error searching 1337x: {str(e)}")
            
        return results
        
    def _search_rarbg(self, query):
        """Search RARBG for torrents"""
        results = []
        
        try:
            # Use RARBG API
            encoded_query = urllib.parse.quote(query)
            url = f"https://rarbg.to/torrents.php?search={encoded_query}&sort=seeders&order=desc"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            torrent_rows = soup.find_all('tr', class_='lista2')
            
            for row in torrent_rows:
                try:
                    # Extract torrent details
                    name_cell = row.find('td', class_='lista')
                    if not name_cell:
                        continue
                        
                    name = name_cell.find('a').text.strip()
                    magnet_link = name_cell.find('a')['href']
                    
                    # Extract size
                    size_cell = row.find_all('td', class_='lista')[3]
                    size = size_cell.text.strip()
                    
                    # Extract seeds and leechers
                    seeds = int(row.find_all('td', class_='lista')[4].text.strip())
                    leechers = int(row.find_all('td', class_='lista')[5].text.strip())
                    
                    results.append(
                        TorrentSearchResult(
                            name=name,
                            seeds=seeds,
                            leechers=leechers,
                            size=size,
                            magnet_link=magnet_link,
                            source="RARBG"
                        )
                    )
                    
                except (AttributeError, ValueError) as e:
                    continue
                    
        except Exception as e:
            self.search_error.emit(f"Error searching RARBG: {str(e)}")
            
        return results
        
    def _format_size(self, size_bytes):
        """Convert size in bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB" 