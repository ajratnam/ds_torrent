from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                            QPushButton, QTableWidget, QTableWidgetItem, 
                            QHeaderView, QAbstractItemView, QProgressBar,
                            QLabel, QComboBox, QMenu, QAction, QMessageBox, 
                            QInputDialog)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QPainter


class SearchResultsTable(QTableWidget):
    """Table for displaying torrent search results"""
    # Signal when user wants to download a torrent
    download_requested = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Setup table properties
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            "Name", "Size", "Seeds", "Leechers", "Source", "Magnet Link"
        ])
        
        # Setup table appearance
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Set column properties
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Name
        
        # Set column widths
        self.setColumnWidth(1, 90)   # Size (increased width slightly)
        self.setColumnWidth(2, 70)   # Seeds (increased width slightly)
        self.setColumnWidth(3, 70)   # Leechers (increased width slightly)
        self.setColumnWidth(4, 100)  # Source (increased width slightly)
        self.setColumnWidth(5, 120)  # Magnet Link (increased width slightly)
        
        # Double click to download
        self.cellDoubleClicked.connect(lambda row, col: self.download_requested.emit(row))
        
    def paintEvent(self, event):
        """Custom paint event to show placeholder text."""
        super().paintEvent(event)
        if self.rowCount() == 0:
            parent_tab = self.parentWidget()
            placeholder_text = "Perform a search to see results."
            if hasattr(parent_tab, 'last_search_had_results') and not parent_tab.last_search_had_results:
                placeholder_text = "No results found for your search."
            elif hasattr(parent_tab, 'is_searching_flag') and parent_tab.is_searching_flag:
                return # Don't show placeholder if a search is actively in progress (progress bar is visible)
            elif hasattr(parent_tab, 'search_sources') and not parent_tab.search_sources:
                placeholder_text = "No search sources available. Please add sources in settings."

            painter = QPainter(self.viewport())
            painter.save()
            font = self.font()
            font.setPointSize(12)
            painter.setFont(font)
            text_color = QColor("#888888") 
            painter.setPen(text_color)
            painter.drawText(self.viewport().rect(), Qt.AlignCenter, placeholder_text)
            painter.restore()

    def show_context_menu(self, position):
        """Show context menu for search results"""
        row = self.rowAt(position.y())
        
        if row >= 0:
            menu = QMenu()
            
            download_action = QAction("Download", self)
            download_action.triggered.connect(lambda: self.download_requested.emit(row))
            
            menu.addAction(download_action)
            menu.exec_(self.viewport().mapToGlobal(position))


class SearchTab(QWidget):
    """Tab for searching torrents"""
    # Signal when user wants to download a torrent
    download_torrent = pyqtSignal(str)
    
    def __init__(self, search_engine, search_sources, parent=None):
        super().__init__(parent)
        
        self.search_engine = search_engine
        self.search_sources = search_sources
        self.search_results = []
        self.last_search_had_results = True # Assume true initially, or set based on actual state
        self.is_searching_flag = False # To track if a search is ongoing
        
        # Setup UI
        self.setup_ui()
        
        # Connect signals
        self.connect_signals()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Search bar area
        search_area = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search terms...")
        self.search_input.returnPressed.connect(self.perform_search)
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.perform_search)
        
        self.sort_by = QComboBox()
        self.sort_by.addItems(["Seeds", "Leechers", "Size", "Name"])
        
        search_area.addWidget(QLabel("Search:"))
        search_area.addWidget(self.search_input, 1)
        search_area.addWidget(QLabel("Sort by:"))
        search_area.addWidget(self.sort_by)
        search_area.addWidget(self.search_button)
        
        layout.addLayout(search_area)
        
        # Status area
        status_area = QHBoxLayout()
        
        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        status_area.addWidget(self.status_label, 1)
        status_area.addWidget(self.progress_bar)
        
        layout.addLayout(status_area)
        
        # Results table
        self.results_table = SearchResultsTable()
        layout.addWidget(self.results_table)
        
    def connect_signals(self):
        """Connect signals from search engine"""
        # Search engine signals
        self.search_engine.search_completed.connect(self.on_search_completed)
        self.search_engine.search_error.connect(self.on_search_error)
        self.search_engine.search_progress.connect(self.on_search_progress)
        
        # Table signals
        self.results_table.download_requested.connect(self.on_download_requested)
        
    def perform_search(self):
        """Execute the search"""
        query = self.search_input.text()
        
        if not query:
            return
            
        if not self.search_sources:
            QMessageBox.warning(self, "No Search Sources", 
                                "No search sources configured. Please add sources in Settings.")
            self.results_table.viewport().update() # Ensure placeholder is updated
            return
            
        # Clear previous results
        self.results_table.setRowCount(0)
        self.search_results = []
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.is_searching_flag = True # Set searching flag
        self.last_search_had_results = True # Reset this flag before a new search
        self.results_table.viewport().update() # Ensure placeholder is cleared/updated
        
        # Update status
        self.status_label.setText(f"Searching for: {query}")
        
        # Start search
        display_domain = self.search_sources[0] if self.search_sources else None # Get first source for display
        self.search_engine.search(query, display_domain=display_domain)
        
    @pyqtSlot(list)
    def on_search_completed(self, results):
        """Handle search completion"""
        self.is_searching_flag = False
        self.search_results = results
        self.last_search_had_results = bool(results)
        
        # Sort results according to the selected option
        sort_column = self.sort_by.currentText().lower()
        if sort_column == "seeds":
            results.sort(key=lambda x: x.seeds, reverse=True)
        elif sort_column == "leechers":
            results.sort(key=lambda x: x.leechers, reverse=True)
        elif sort_column == "size":
            # Size is a string, so this is just a rough approximation
            results.sort(key=lambda x: x.size, reverse=True)
        elif sort_column == "name":
            results.sort(key=lambda x: x.name)
            
        # Update table with results
        self.results_table.setRowCount(len(results))
        
        for i, result in enumerate(results):
            # Name
            self.results_table.setItem(i, 0, QTableWidgetItem(result.name))
            
            # Size
            self.results_table.setItem(i, 1, QTableWidgetItem(result.size))
            
            # Seeds
            seeds_item = QTableWidgetItem(str(result.seeds))
            seeds_item.setForeground(QColor("#76FF03"))  # Bright Green (Consistent with TorrentTable)
            seeds_item.setTextAlignment(Qt.AlignCenter) # Center align
            self.results_table.setItem(i, 2, seeds_item)
            
            # Leechers
            leechers_item = QTableWidgetItem(str(result.leechers))
            leechers_item.setForeground(QColor("#64B5F6")) # Light Blue
            leechers_item.setTextAlignment(Qt.AlignCenter) # Center align
            self.results_table.setItem(i, 3, leechers_item)
            
            # Source
            source_item = QTableWidgetItem(result.source)
            source_item.setTextAlignment(Qt.AlignCenter) # Center align
            self.results_table.setItem(i, 4, source_item)
            
            # Magnet link (shortened)
            magnet_short = result.magnet_link[:20] + "..."
            magnet_item = QTableWidgetItem(magnet_short)
            magnet_item.setToolTip(result.magnet_link) # Show full link on hover
            self.results_table.setItem(i, 5, magnet_item)
            
        # Hide progress bar
        self.progress_bar.setVisible(False)
        
        # Update status
        self.status_label.setText(f"Found {len(results)} results")
        self.results_table.viewport().update() # Update to show results or new placeholder
        
    @pyqtSlot(str)
    def on_search_error(self, error_msg):
        """Handle search errors"""
        self.is_searching_flag = False
        self.last_search_had_results = False # Assume error means no results for placeholder purposes
        # Hide progress bar
        self.progress_bar.setVisible(False)
        
        # Update status
        self.status_label.setText(f"Error: {error_msg}")
        self.status_label.setStyleSheet("color: #FF5252;") # Error color for status label
        self.results_table.viewport().update() # Update to show "no results" or error related placeholder
        
    @pyqtSlot(int, int)
    def on_search_progress(self, current, total):
        """Handle search progress updates"""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"Searching... {progress}%") # Update status label during progress
        self.status_label.setStyleSheet("color: #E0E0E0;") # Reset to default color
        
    def on_download_requested(self, row):
        """Handle download request for a torrent"""
        if row < 0 or row >= len(self.search_results):
            return
            
        # Get the selected torrent
        result = self.search_results[row]
        
        # Emit signal to download
        self.download_torrent.emit(result.magnet_link) 

    def update_search_sources(self, new_sources):
        """Update the internal list of search sources."""
        self.search_sources = new_sources
        # If sources are now available, we might want to refresh the placeholder text
        # or enable the search button if it was disabled.
        self.results_table.viewport().update() # Trigger a repaint to update placeholder if needed 