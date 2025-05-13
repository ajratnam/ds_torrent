from PyQt5.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, 
                           QProgressBar, QMenu, QAction, QAbstractItemView,
                           QWidget, QHBoxLayout, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont

class TorrentProgressBar(QProgressBar):
    """Custom progress bar for torrent progress"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(True)
        self.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 10px;
                margin: 0.5px;
            }
        """)


class TorrentTableWidget(QTableWidget):
    """Table widget for displaying active torrents"""
    # Custom signals
    pause_torrent = pyqtSignal(str)
    resume_torrent = pyqtSignal(str)
    remove_torrent = pyqtSignal(str, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Setup table properties
        self.setColumnCount(8)
        self.setHorizontalHeaderLabels([
            "Name", "Size", "Progress", "Status", 
            "Seeds", "Peers", "Down Speed", "Up Speed"
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
        self.setColumnWidth(4, 60)   # Seeds
        self.setColumnWidth(5, 60)   # Peers
        self.setColumnWidth(6, 100)  # Down Speed
        self.setColumnWidth(7, 100)  # Up Speed
        
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
        
        # Set seeds/peers
        self.setItem(row, 4, QTableWidgetItem(str(status['num_seeds'])))
        self.setItem(row, 5, QTableWidgetItem(str(status['num_peers'])))
        
        # Set speeds
        self.setItem(row, 6, QTableWidgetItem(f"{status['download_rate']:.1f} KB/s"))
        self.setItem(row, 7, QTableWidgetItem(f"{status['upload_rate']:.1f} KB/s"))
        
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
        
        # Seeds/Peers
        self.item(row, 4).setText(str(status['num_seeds']))
        self.item(row, 5).setText(str(status['num_peers']))
        
        # Speeds
        self.item(row, 6).setText(f"{status['download_rate']:.1f} KB/s")
        self.item(row, 7).setText(f"{status['upload_rate']:.1f} KB/s")
        
        # Color coding based on status
        if status['state'] == 'downloading':
            self.item(row, 3).setForeground(QColor(0, 128, 0))  # Green
        elif status['state'] == 'seeding':
            self.item(row, 3).setForeground(QColor(0, 0, 255))  # Blue
        elif status['state'] == 'paused':
            self.item(row, 3).setForeground(QColor(128, 128, 128))  # Gray
        elif 'error' in status['state'].lower():
            self.item(row, 3).setForeground(QColor(255, 0, 0))  # Red
        elif not status['has_metadata']:
            self.item(row, 3).setForeground(QColor(255, 165, 0))  # Orange for fetching metadata
            
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