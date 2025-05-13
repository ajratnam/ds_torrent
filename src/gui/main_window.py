import os
import sys
import datetime
import time
import json
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                            QHBoxLayout, QLabel, QPushButton, QLineEdit,
                            QTableWidget, QTableWidgetItem, QHeaderView,
                            QProgressBar, QFileDialog, QMessageBox, QComboBox,
                            QSplitter, QStatusBar, QAction, QMenu, QToolBar,
                            QSystemTrayIcon, QInputDialog, QDialog)
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSlot, QStandardPaths, QByteArray
from PyQt5.QtGui import QIcon, QFont

# Set runtime directory permissions
if sys.platform.startswith('linux'):
    os.environ['XDG_RUNTIME_DIR'] = os.path.expanduser('~/.local/share/runtime')
    os.makedirs(os.environ['XDG_RUNTIME_DIR'], mode=0o700, exist_ok=True)

from src.core.torrent_client import TorrentClient
from src.core.torrent_search import TorrentSearchEngine
from src.gui.torrent_table import TorrentTableWidget
from src.gui.search_tab import SearchTab
from src.gui.settings_dialog import SettingsDialog

APP_NAME = "PythonBitTorrentClient"
STATE_FILE_NAME = "app_state.json"

class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        
        self._init_paths()

        # Setup core components
        self.torrent_client = TorrentClient(self.app_data_dir)
        self.search_engine = TorrentSearchEngine()
        
        # Setup UI
        self.setup_ui()
        
        # Connect signals
        self.connect_signals()
        
        # Default save path (will be overridden by loaded state if available)
        self.default_save_path = os.path.expanduser('~/Downloads')
        
        self.load_app_state()

    def _init_paths(self):
        """Initialize application paths."""
        self.app_data_dir = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
        # Append app name to create a dedicated folder if QStandardPaths doesn't include it
        # (Behavior might vary by OS/Qt version)
        if APP_NAME not in self.app_data_dir:
             self.app_data_dir = os.path.join(self.app_data_dir, APP_NAME)

        if not os.path.exists(self.app_data_dir):
            try:
                os.makedirs(self.app_data_dir, exist_ok=True)
            except OSError as e:
                print(f"Error creating app data directory {self.app_data_dir}: {e}") # Use print for early errors
                # Fallback if necessary, or raise
                self.app_data_dir = "." 

        self.state_file_path = os.path.join(self.app_data_dir, STATE_FILE_NAME)

    def load_app_state(self):
        """Load application state from disk."""
        if not os.path.exists(self.state_file_path):
            print(f"State file not found: {self.state_file_path}. Starting with defaults.")
            return

        try:
            with open(self.state_file_path, 'r') as f:
                state_data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading state file {self.state_file_path}: {e}")
            return

        # Restore window geometry
        geom_hex = state_data.get('window_geometry')
        if geom_hex:
            self.restoreGeometry(QByteArray.fromHex(geom_hex.encode('ascii')))

        # Restore default save path
        self.default_save_path = state_data.get('default_save_path', self.default_save_path)

        # Restore torrent client settings (example for limits)
        client_settings = state_data.get('client_settings', {})
        download_limit = client_settings.get('download_rate_limit', 0)
        upload_limit = client_settings.get('upload_rate_limit', 0)
        self.torrent_client.set_download_limit(download_limit // 1024) # Assuming settings are in bytes/s
        self.torrent_client.set_upload_limit(upload_limit // 1024)

        # Restore torrents
        saved_torrents = state_data.get('torrents', [])
        for torrent_info in saved_torrents:
            source = torrent_info.get('source')
            save_path = torrent_info.get('save_path')
            info_hash = torrent_info.get('info_hash')
            
            if not source or not save_path or not info_hash:
                print(f"Skipping invalid torrent entry: {torrent_info}")
                continue

            resume_data_bytes = None
            resume_file = self.torrent_client._get_resume_filepath(info_hash)
            if os.path.exists(resume_file):
                try:
                    with open(resume_file, 'rb') as rf:
                        resume_data_bytes = rf.read()
                except IOError as e:
                    print(f"Error reading resume file {resume_file}: {e}")
            
            self.torrent_client.add_torrent(source, save_path, resume_data_bytes)
        
        # Restore last active tab
        last_tab_index = state_data.get('last_tab_index', 0)
        if 0 <= last_tab_index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(last_tab_index)
        
        print(f"Application state loaded from {self.state_file_path}")

    def save_app_state(self):
        """Save current application state to disk."""
        state_data = {}

        # Save window geometry
        state_data['window_geometry'] = self.saveGeometry().toHex().data().decode('ascii')

        # Save default save path
        state_data['default_save_path'] = self.default_save_path

        # Save torrent client settings (example for limits from libtorrent settings)
        session_settings_pack = self.torrent_client.session.get_settings()
        state_data['client_settings'] = {
            'download_rate_limit': session_settings_pack['download_rate_limit'],
            'upload_rate_limit': session_settings_pack['upload_rate_limit'],
            # Add other relevant libtorrent settings if managed by your UI
        }

        # Save active torrents
        active_torrents_state = []
        for info_hash, torrent_handle_obj in self.torrent_client.torrents.items():
            # Request resume data to be generated and saved by the alert handler
            self.torrent_client.trigger_save_resume_data(info_hash)
            active_torrents_state.append({
                'source': torrent_handle_obj.source,
                'save_path': torrent_handle_obj.save_path,
                'info_hash': info_hash
            })
        state_data['torrents'] = active_torrents_state
        
        # Save current active tab
        state_data['last_tab_index'] = self.tab_widget.currentIndex()

        try:
            with open(self.state_file_path, 'w') as f:
                json.dump(state_data, f, indent=4)
            print(f"Application state saved to {self.state_file_path}")
        except IOError as e:
            print(f"Error saving state file {self.state_file_path}: {e}")

    def setup_ui(self):
        """Setup the user interface"""
        # Main window properties
        self.setWindowTitle("Python BitTorrent Client")
        self.setMinimumSize(1000, 600)
        
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.setup_torrents_tab()
        self.setup_search_tab()
        
        # Setup toolbar
        self.setup_toolbar()
        
        # Setup statusbar
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Add status labels
        self.status_dht = QLabel("DHT: Initializing...")
        self.status_download = QLabel("↓ 0.0 KB/s")
        self.status_upload = QLabel("↑ 0.0 KB/s")
        
        self.statusbar.addPermanentWidget(self.status_dht)
        self.statusbar.addPermanentWidget(self.status_download)
        self.statusbar.addPermanentWidget(self.status_upload)
        
        # Setup update timer for status
        self.update_timer = QTimer()
        self.update_timer.setInterval(1000)
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start()
        
    def setup_toolbar(self):
        """Setup the main toolbar"""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(self.toolbar)
        
        # Add torrent action
        self.action_add_torrent = QAction("Add Torrent", self)
        self.action_add_torrent.triggered.connect(self.add_torrent_dialog)
        self.toolbar.addAction(self.action_add_torrent)
        
        # Add magnet link action
        self.action_add_magnet = QAction("Add Magnet", self)
        self.action_add_magnet.triggered.connect(self.add_magnet_dialog)
        self.toolbar.addAction(self.action_add_magnet)
        
        self.toolbar.addSeparator()
        
        # Resume all action
        self.action_resume_all = QAction("Resume All", self)
        self.action_resume_all.triggered.connect(self.resume_all_torrents)
        self.toolbar.addAction(self.action_resume_all)
        
        # Pause all action
        self.action_pause_all = QAction("Pause All", self)
        self.action_pause_all.triggered.connect(self.pause_all_torrents)
        self.toolbar.addAction(self.action_pause_all)
        
        self.toolbar.addSeparator()
        
        # Settings action
        self.action_settings = QAction("Settings", self)
        self.action_settings.triggered.connect(self.show_settings)
        self.toolbar.addAction(self.action_settings)
        
    def setup_torrents_tab(self):
        """Setup the torrents tab"""
        self.torrents_tab = QWidget()
        self.tab_widget.addTab(self.torrents_tab, "Torrents")
        
        layout = QVBoxLayout(self.torrents_tab)
        
        # Create torrent table
        self.torrent_table = TorrentTableWidget()
        layout.addWidget(self.torrent_table)
        
    def setup_search_tab(self):
        """Setup the search tab"""
        self.search_tab = SearchTab(self.search_engine)
        self.tab_widget.addTab(self.search_tab, "Search")
        
        # Connect download signal
        self.search_tab.download_torrent.connect(self.download_from_search)
        
    def connect_signals(self):
        """Connect all signals from core components to UI"""
        # Torrent client signals
        self.torrent_client.torrent_added.connect(self.on_torrent_added)
        self.torrent_client.client_status_updated.connect(self.on_client_status_updated)
        self.torrent_client.error.connect(self.on_error)
        
        # Table signals
        self.torrent_table.pause_torrent.connect(self.pause_torrent)
        self.torrent_table.resume_torrent.connect(self.resume_torrent)
        self.torrent_table.remove_torrent.connect(self.handle_remove_torrent)
        
        # Search engine signals
        self.search_engine.search_error.connect(self.on_error)
        
    @pyqtSlot(object)
    def on_torrent_added(self, torrent):
        """Handle torrent added signal"""
        # Add to torrent table
        self.torrent_table.add_torrent(torrent)
        
        # Connect status update signal
        torrent.status_updated.connect(self.torrent_table.update_torrent_status)
        torrent.completed.connect(self.on_torrent_completed)
        
    @pyqtSlot(dict)
    def on_client_status_updated(self, status):
        """Handle client status update"""
        # Update status bar
        self.status_download.setText(f"↓ {status['download_rate']:.1f} KB/s")
        self.status_upload.setText(f"↑ {status['upload_rate']:.1f} KB/s")
        
    @pyqtSlot(str)
    def on_torrent_completed(self, info_hash):
        """Handle torrent completed signal"""
        # Show notification
        QMessageBox.information(self, "Download Complete", 
                               f"Torrent download complete: {self.torrent_client.torrents[info_hash].get_status()['name']}")
        
    def update_status(self):
        """Update status information periodically"""
        # Update DHT status
        if self.torrent_client.session.is_dht_running():
            dht_nodes = self.torrent_client.session.status().dht_nodes
            self.status_dht.setText(f"DHT: {dht_nodes} nodes")
        else:
            self.status_dht.setText("DHT: Off")
        
    def on_error(self, error_message):
        """Handle error messages"""
        QMessageBox.critical(self, "Error", error_message)
        
    def add_torrent_dialog(self):
        """Show dialog to add a torrent file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Torrent File", "", "Torrent Files (*.torrent)"
        )
        
        if file_path:
            save_path = QFileDialog.getExistingDirectory(
                self, "Select Save Location", self.default_save_path
            )
            
            if save_path:
                torrent = self.torrent_client.add_torrent(file_path, save_path)
                if not torrent:
                    QMessageBox.warning(self, "Warning", "Failed to add torrent. Check the error message for details.")
                
    def add_magnet_dialog(self):
        """Show dialog to add a magnet link"""
        magnet_link, ok = QInputDialog.getText(
            self, "Add Magnet Link", "Enter Magnet Link:"
        )
        
        if ok and magnet_link:
            if not magnet_link.startswith('magnet:'):
                QMessageBox.warning(self, "Invalid Link", "Please enter a valid magnet link starting with 'magnet:'")
                return
                
            save_path = QFileDialog.getExistingDirectory(
                self, "Select Save Location", self.default_save_path
            )
            
            if save_path:
                torrent = self.torrent_client.add_torrent(magnet_link, save_path)
                if not torrent:
                    QMessageBox.warning(self, "Warning", "Failed to add magnet link. Check the error message for details.")
                
    def download_from_search(self, magnet_link):
        """Download a torrent from search results"""
        save_path = QFileDialog.getExistingDirectory(
            self, "Select Save Location", self.default_save_path
        )
        
        if save_path:
            torrent = self.torrent_client.add_torrent(magnet_link, save_path)
            if not torrent:
                QMessageBox.warning(self, "Warning", "Failed to add torrent from search. Check the error message for details.")
            else:
                # Switch to the Torrents tab
                for i in range(self.tab_widget.count()):
                    if self.tab_widget.tabText(i) == "Torrents":
                        self.tab_widget.setCurrentIndex(i)
                        break
                
    def pause_torrent(self, info_hash):
        """Pause a torrent"""
        if info_hash in self.torrent_client.torrents:
            self.torrent_client.torrents[info_hash].pause()
            
    def resume_torrent(self, info_hash):
        """Resume a torrent"""
        if info_hash in self.torrent_client.torrents:
            self.torrent_client.torrents[info_hash].resume()
            
    def handle_remove_torrent(self, info_hash, delete_files=False):
        """Remove a torrent from the client"""
        self.torrent_client.remove_torrent(info_hash, delete_files)
        self.torrent_table.remove_torrent_row(info_hash)
        
    def pause_all_torrents(self):
        """Pause all torrents"""
        for torrent in self.torrent_client.torrents.values():
            torrent.pause()
            
    def resume_all_torrents(self):
        """Resume all torrents"""
        for torrent in self.torrent_client.torrents.values():
            torrent.resume()
            
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        # TODO: Populate dialog with current settings before showing
        current_settings = self.torrent_client.session.get_settings()
        dialog.download_limit_spin.setValue(current_settings['download_rate_limit'] // 1024 if current_settings['download_rate_limit'] > 0 else 0)
        dialog.upload_limit_spin.setValue(current_settings['upload_rate_limit'] // 1024 if current_settings['upload_rate_limit'] > 0 else 0)
        # Make sure save_path_edit exists on dialog or self.default_save_path is used correctly
        # dialog.save_path_edit.setText(self.default_save_path) 

        if dialog.exec_() == QDialog.Accepted: # QDialog.Accepted should now work
            # Apply settings
            download_limit = dialog.download_limit_spin.value() 
            upload_limit = dialog.upload_limit_spin.value()   
            
            self.torrent_client.set_download_limit(download_limit) 
            self.torrent_client.set_upload_limit(upload_limit)
            
            # Save default save path
            if hasattr(dialog, 'save_path_edit'): # Check if dialog has this attribute
                 self.default_save_path = dialog.save_path_edit.text()
            
            self.save_app_state() 
            
    def closeEvent(self, event):
        """Handle window close event"""
        # Optionally, skip confirmation if a setting indicates so
        reply = QMessageBox.question(
            self, "Confirm Exit",
            "Are you sure you want to exit? Active downloads will be stopped, and state will be saved.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            print("Saving application state before closing...")
            self.save_app_state()
            # Allow some time for async operations like resume data saving to be processed by libtorrent alerts
            # This is a simple delay; a more robust solution would use signals or event loops.
            time.sleep(0.5) # Give alerts a moment to process
            event.accept()
        else:
            event.ignore() 