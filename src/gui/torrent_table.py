from PyQt5.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, 
                           QProgressBar, QMenu, QAction, QAbstractItemView,
                           QWidget, QHBoxLayout, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont
from datetime import datetime

class TorrentProgressBar(QProgressBar):
    """Custom progress bar for torrent progress"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(True)
        # Ensure progress bar text is visible against the dark background
        # self.setStyleSheet("QProgressBar { color: #1E1E1E; } QProgressBar::chunk { background-color: #40E0D0; margin: 0.5px; border-radius: 2px; }") # Styling now handled by global style.qss


class TorrentTableWidget(QTableWidget):
    """Table widget for displaying active torrents"""
    # Custom signals
    pause_torrent = pyqtSignal(str)
    resume_torrent = pyqtSignal(str)
    remove_torrent = pyqtSignal(str, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Setup table properties
        self.setColumnCount(11)  # Increased column count
        self.setHorizontalHeaderLabels([
            "Name", "Size", "Progress", "Status", 
            "Seeds", "Peers", "Down Speed", "Up Speed",
            "ETA", "Ratio", "Added On" # New columns
        ])
        
        # Setup table appearance
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Stretch columns
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Name
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Progress
        
        # Set column widths
        self.setColumnWidth(1, 80)   # Size
        self.setColumnWidth(3, 100)  # Status
        self.setColumnWidth(4, 70)   # Seeds (conn/total)
        self.setColumnWidth(5, 70)   # Peers (conn/total)
        self.setColumnWidth(6, 90)  # Down Speed
        self.setColumnWidth(7, 90)  # Up Speed
        self.setColumnWidth(8, 80)   # ETA
        self.setColumnWidth(9, 60)   # Ratio
        self.setColumnWidth(10, 120) # Added On
        
        # Store torrent info hashes for each row
        self.torrent_hashes = {}
        
    def add_torrent(self, torrent):
        """Add a torrent to the table"""
        # Get initial status
        status = torrent.get_status()
        
        # Add a new row
        row = self.rowCount()
        self.insertRow(row)
        
        # Set torrent name
        self.setItem(row, 0, QTableWidgetItem(status['name']))
        
        # Set size (will be updated when metadata is received)
        self.setItem(row, 1, QTableWidgetItem("Calculating..."))
        
        # Set progress bar
        progress_bar = TorrentProgressBar()
        progress_bar.setValue(int(status['progress']))
        self.setCellWidget(row, 2, progress_bar)
        
        # Set status
        self.setItem(row, 3, QTableWidgetItem(status['state']))
        
        # Set seeds/peers (Connected / Total in swarm)
        self.setItem(row, 4, QTableWidgetItem(f"{status['num_seeds']} ({status['total_seeds']})"))
        self.setItem(row, 5, QTableWidgetItem(f"{status['num_peers']} ({status['total_peers']})"))
        
        # Set speeds
        self.setItem(row, 6, QTableWidgetItem(f"{status['download_rate']:.1f} KB/s"))
        self.setItem(row, 7, QTableWidgetItem(f"{status['upload_rate']:.1f} KB/s"))
        
        # Set ETA
        self.setItem(row, 8, QTableWidgetItem(self._format_eta(status['eta'])))
        
        # Set Ratio
        self.setItem(row, 9, QTableWidgetItem(f"{status['ratio']:.2f}"))
        
        # Set Added On
        self.setItem(row, 10, QTableWidgetItem(self._format_timestamp(status['added_on'])))
        
        # Store the info hash
        info_hash = str(torrent.handle.info_hash())
        self.torrent_hashes[row] = info_hash
        
    def update_torrent_status(self, status):
        """Update torrent status in the table"""
        # Find the row for this torrent
        info_hash = str(status['info_hash'])
        row = None
        
        for i, hash_val in self.torrent_hashes.items():
            if hash_val == info_hash:
                row = i
                break
                
        if row is None:
            # Find by name instead
            for i in range(self.rowCount()):
                if self.item(i, 0).text() == status['name']:
                    row = i
                    break
                    
        if row is None:
            return
            
        # Update values
        
        # Name (might be updated after metadata is received)
        self.item(row, 0).setText(status['name'])
        
        # Size (might be updated after metadata is received)
        if status['total_size'] > 0:
            size_gb = status['total_size'] / (1024**3)
            self.item(row, 1).setText(f"{size_gb:.2f} GB")
        else:
            self.item(row, 1).setText("Calculating...")
        
        # Progress
        progress_bar = self.cellWidget(row, 2)
        if progress_bar:
            progress_bar.setValue(int(status['progress']))
            progress_bar.setFormat(f"{status['progress']:.1f}%")
            
        # Status
        self.item(row, 3).setText(status['state'])
        
        # Seeds/Peers (Connected / Total in swarm)
        self.item(row, 4).setText(f"{status['num_seeds']} ({status['total_seeds']})")
        self.item(row, 5).setText(f"{status['num_peers']} ({status['total_peers']})")
        
        # Speeds
        self.item(row, 6).setText(f"{status['download_rate']:.1f} KB/s")
        self.item(row, 7).setText(f"{status['upload_rate']:.1f} KB/s")
        
        # ETA
        self.item(row, 8).setText(self._format_eta(status['eta']))
        
        # Ratio
        self.item(row, 9).setText(f"{status['ratio']:.2f}")
        
        # Added On (This generally doesn't change, but in case of a load, it's good to refresh)
        # self.item(row, 10).setText(self._format_timestamp(status['added_on'])) 
        # Added on should ideally be set once when the torrent is added or loaded from state.
        # Re-setting it here on every status update might be redundant unless it can change.

        # Color coding based on status
        state_text = status['state'].lower()
        status_item = self.item(row, 3)

        if 'downloading' in state_text:
            status_item.setForeground(QColor("#40E0D0"))  # Vibrant Teal
        elif 'seeding' in state_text:
            status_item.setForeground(QColor("#76FF03"))  # Bright Green
        elif 'paused' in state_text:
            status_item.setForeground(QColor("#9E9E9E"))  # Medium Gray
        elif 'error' in state_text:
            status_item.setForeground(QColor("#FF5252"))  # Bright Red
        elif not status['has_metadata'] or 'fetching metadata' in state_text or 'checking' in state_text:
            status_item.setForeground(QColor("#FFC107"))  # Amber/Yellow
        else: # Default color from stylesheet
            status_item.setForeground(QColor("#E0E0E0"))

    def remove_torrent_row(self, info_hash):
        """Remove a torrent from the table"""
        for row, hash_val in list(self.torrent_hashes.items()):
            if hash_val == info_hash:
                self.removeRow(row)
                del self.torrent_hashes[row]
                # Renumber keys
                self.torrent_hashes = {i: self.torrent_hashes[key] for i, key in 
                                     enumerate(sorted(self.torrent_hashes.keys()))}
                break
                
    def _format_eta(self, seconds):
        if seconds == float('inf') or seconds < 0:
            return "∞"
        
        current_row = self.currentRow()
        current_status = "unknown"
        if current_row >= 0 and self.item(current_row, 3):
            current_status = self.item(current_row, 3).text().lower()

        if seconds == 0 and current_status not in ["seeding", "finished", "paused", "completed"]:
             return "Stalled"

        days = int(seconds // 86400)
        seconds %= 86400
        hours = int(seconds // 3600)
        seconds %= 3600
        minutes = int(seconds // 60)
        
        if days > 0:
            return f"{days}d {hours}h"
        if hours > 0:
            return f"{hours}h {minutes}m"
        if minutes > 0:
            return f"{minutes}m"
        return "< 1m"

    def _format_timestamp(self, timestamp):
        try:
            # Assuming timestamp is a float from time.time()
            dt_object = datetime.fromtimestamp(timestamp)
            return dt_object.strftime("%Y-%m-%d %H:%M:%S")
        except TypeError: # Handle potential None or malformed
            return "N/A"

    def show_context_menu(self, position):
        """Show context menu for torrent actions"""
        row = self.rowAt(position.y())
        
        if row >= 0:
            menu = QMenu()
            
            pause_action = QAction("Pause", self)
            resume_action = QAction("Resume", self)
            remove_action = QAction("Remove", self)
            remove_with_data_action = QAction("Remove with Data", self)
            
            menu.addAction(pause_action)
            menu.addAction(resume_action)
            menu.addSeparator()
            menu.addAction(remove_action)
            menu.addAction(remove_with_data_action)
            
            # Get selected info hash
            info_hash = self.torrent_hashes.get(row)
            
            # Connect actions
            pause_action.triggered.connect(lambda: self.pause_torrent.emit(info_hash))
            resume_action.triggered.connect(lambda: self.resume_torrent.emit(info_hash))
            remove_action.triggered.connect(lambda: self.remove_torrent.emit(info_hash, False))
            remove_with_data_action.triggered.connect(lambda: self.remove_torrent.emit(info_hash, True))
            
            # Show the menu
            menu.exec_(self.viewport().mapToGlobal(position)) 