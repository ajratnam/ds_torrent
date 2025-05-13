import os
import sys
import datetime
import time
import json
import libtorrent as lt # Ensure libtorrent is imported for settings_pack keys
import logging # Added for logging
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                            QHBoxLayout, QLabel, QPushButton, QLineEdit,
                            QTableWidget, QTableWidgetItem, QHeaderView,
                            QProgressBar, QFileDialog, QMessageBox, QComboBox,
                            QSplitter, QStatusBar, QAction, QMenu, QToolBar,
                            QSystemTrayIcon, QInputDialog, QDialog, QStyle)
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
from src.gui.torrent_detail_widget import TorrentDetailWidget

APP_NAME = "PythonBitTorrentClient"
STATE_FILE_NAME = "app_state.json"

log = logging.getLogger(__name__) # Added for logging

# Define KNOWN_GOOD_SETTINGS_KEYS at the module level or ensure it's accessible
# For this example, I'll define a placeholder. Ensure it matches your actual list.
KNOWN_GOOD_SETTINGS_KEYS = [
    'user_agent', 'listen_interfaces', 'download_rate_limit', 'upload_rate_limit',
    'max_connections_global', 'max_half_open_connections',
    'encryption_policy_forced', 'encryption_policy_enabled', 'allowed_enc_level_rc4',
    'allowed_enc_level_plaintext', 'allowed_enc_level_pe',
    'announce_to_all_tiers', 'announce_to_all_trackers',
    'auto_scrape_interval', 'stop_tracker_timeout', 'connection_speed',
    'unchoke_slots_limit', 'max_allowed_in_request_queue',
    'active_downloads', 'active_seeds', 'active_limit'
    # Ensure 'auto_manage_slots' and 'enable_pex' are NOT here if problematic
]

class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        
        self._init_paths()

        # Setup core components
        self.torrent_client = TorrentClient(self.app_data_dir)
        self.search_engine = TorrentSearchEngine()
        
        # UI Related flags / App settings
        self.confirm_on_exit_flag = True # Default
        self.start_minimized_flag = False # Default
        self.show_speed_in_title_flag = False # Default
        
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
            # Apply default client settings if no state file
            self.torrent_client.apply_session_settings({}) # Apply default libtorrent settings
            return

        try:
            with open(self.state_file_path, 'r') as f:
                state_data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading state file {self.state_file_path}: {e}")
            self.torrent_client.apply_session_settings({}) # Apply default libtorrent settings on error
            return

        # Restore window geometry
        geom_hex = state_data.get('window_geometry')
        if geom_hex:
            self.restoreGeometry(QByteArray.fromHex(geom_hex.encode('ascii')))

        # Restore default save path
        self.default_save_path = state_data.get('default_save_path', self.default_save_path)
        # The save_path_edit in SettingsDialog will be populated when show_settings() is called.

        # Restore interface settings
        self.confirm_on_exit_flag = state_data.get('ui_confirm_on_exit', self.confirm_on_exit_flag)
        self.start_minimized_flag = state_data.get('ui_start_minimized', self.start_minimized_flag)
        self.show_speed_in_title_flag = state_data.get('ui_show_speed_in_title', self.show_speed_in_title_flag)

        # Restore torrent client settings
        client_settings_json = state_data.get('client_settings', {})
        if client_settings_json: 
            # Filter out unknown keys before applying
            filtered_client_settings = {
                k: v for k, v in client_settings_json.items() if k in KNOWN_GOOD_SETTINGS_KEYS
            }
            if filtered_client_settings:
                if self.torrent_client:
                    self.torrent_client.apply_session_settings(filtered_client_settings)
                    # Cache the loaded & applied settings for the settings dialog
                    self.client_settings_cache = dict(filtered_client_settings) 
                else:
                    print("Torrent client not available during load_app_state to apply settings.")
            else:
                print("No client settings to apply after filtering.")
                self.client_settings_cache = {} # Reset cache if no settings loaded
        else:
            print("No 'client_settings' key found in app_state.json.")
            self.client_settings_cache = {} # Reset cache
        
        # Ensure torrent_client is initialized before trying to get its default settings
        if self.torrent_client and not self.client_settings_cache:
            # If no settings were loaded, populate cache with current (default) client settings
            try:
                self.client_settings_cache = self.torrent_client.get_session_settings()
                print(f"Initialized client_settings_cache with defaults from torrent_client: {self.client_settings_cache}")
            except Exception as e:
                print(f"Error getting default settings from torrent_client: {e}")
                self.client_settings_cache = {}

        # Restore torrents
        saved_torrents = state_data.get('torrents', [])
        for torrent_info in saved_torrents:
            source = torrent_info.get('source')
            save_path = torrent_info.get('save_path')
            info_hash = torrent_info.get('info_hash')
            is_completed = torrent_info.get('is_completed', False) # Load the flag, default to False
            
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
            
            self.torrent_client.add_torrent(source, save_path, resume_data_bytes, is_completed_on_load=is_completed)
        
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
        # Ensure self.default_save_path is up-to-date if changed in settings dialog
        if hasattr(self, 'settings_dialog') and self.settings_dialog: # Check if settings_dialog was shown
            # This assumes get_general_settings() or similar exists or path is directly accessed
            # For now, we assume self.default_save_path is updated by show_settings if dialog is accepted
             pass # self.default_save_path should be updated by show_settings
        state_data['default_save_path'] = self.default_save_path

        # Save interface settings
        state_data['ui_confirm_on_exit'] = self.confirm_on_exit_flag
        state_data['ui_start_minimized'] = self.start_minimized_flag
        state_data['ui_show_speed_in_title'] = self.show_speed_in_title_flag

        # Save torrent client settings from libtorrent session settings
        # These will be saved with string keys for JSON compatibility
        current_lt_settings_dict = self.torrent_client.get_session_settings() # Assuming this returns a dictionary
        
        # --- Remove temporary debug: Print all available setting keys from libtorrent ---
        # if isinstance(current_lt_settings_dict, dict):
        #     print("Available libtorrent setting keys:", sorted(current_lt_settings_dict.keys()))
        # --- End temporary debug ---

        client_settings_to_save = {
            # Connection Tab
            'download_rate_limit': current_lt_settings_dict.get('download_rate_limit', 0),
            'upload_rate_limit': current_lt_settings_dict.get('upload_rate_limit', 0),
            'listen_interfaces': current_lt_settings_dict.get('listen_interfaces', '0.0.0.0:6881'),
            'connections_limit': current_lt_settings_dict.get('connections_limit', 100),
            'unchoke_slots_limit': current_lt_settings_dict.get('unchoke_slots_limit', 8),
            # Advanced Tab
            'enable_dht': current_lt_settings_dict.get('enable_dht', True),
            # 'peer_exchange': current_lt_settings_dict.get('peer_exchange', True), # Remove PEX
            'enable_lsd': current_lt_settings_dict.get('enable_lsd', True),
            # Encryption settings - these are integer values representing enums
            'out_enc_policy': current_lt_settings_dict.get('out_enc_policy', lt.enc_level.pe_rc4),
            'in_enc_policy': current_lt_settings_dict.get('in_enc_policy', lt.enc_level.pe_rc4),
            'allowed_enc_level': current_lt_settings_dict.get('allowed_enc_level', lt.enc_level.rc4),
        }
        state_data['client_settings'] = client_settings_to_save

        # Save active torrents
        active_torrents_state = []
        for info_hash, torrent_handle_obj in self.torrent_client.torrents.items():
            # Request resume data to be generated and saved by the alert handler
            self.torrent_client.trigger_save_resume_data(info_hash)
            active_torrents_state.append({
                'source': torrent_handle_obj.source,
                'save_path': torrent_handle_obj.save_path,
                'info_hash': info_hash,
                'is_completed': torrent_handle_obj.is_completed_flag # Save the flag
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
        
        # Create main splitter for torrents list and details view
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_layout.addWidget(self.main_splitter)

        # Create tab widget (will go into the top part of the splitter)
        self.tab_widget = QTabWidget()
        self.main_splitter.addWidget(self.tab_widget)
        
        # Create tabs
        self.setup_torrents_tab()
        self.setup_search_tab()
        
        # Create the torrent detail widget
        self.torrent_detail_widget = TorrentDetailWidget()
        self.main_splitter.addWidget(self.torrent_detail_widget)
        
        # Adjust splitter sizes (e.g., 65% for table area, 35% for details)
        self.main_splitter.setSizes([int(self.height() * 0.65), int(self.height() * 0.35)])
        
        # Setup toolbar
        self.setup_toolbar()
        
        # Setup statusbar
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Add status labels
        self.status_dht_icon = QLabel()
        self.status_dht_label = QLabel("DHT: Initializing...")
        self.status_download = QLabel("↓ 0.0 KB/s")
        self.status_upload = QLabel("↑ 0.0 KB/s")

        self.status_download.setMinimumWidth(100)
        self.status_upload.setMinimumWidth(100)
        self.status_dht_label.setMinimumWidth(120)
        
        self.statusbar.addPermanentWidget(self.status_dht_icon)
        self.statusbar.addPermanentWidget(self.status_dht_label)
        self.statusbar.addPermanentWidget(self.status_download)
        self.statusbar.addPermanentWidget(self.status_upload)
        
        # Setup update timer for status
        self.update_timer = QTimer()
        self.update_timer.setInterval(1000)
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start()
        
        # Connect detail widget signals
        self.torrent_detail_widget.file_priority_changed.connect(self.on_file_priority_changed)
        
    def setup_toolbar(self):
        """Setup the main toolbar"""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(self.toolbar)
        
        # Add torrent action
        self.action_add_torrent = QAction(self.style().standardIcon(QStyle.SP_FileIcon), "Add Torrent", self)
        self.action_add_torrent.triggered.connect(self.add_torrent_dialog)
        self.toolbar.addAction(self.action_add_torrent)
        
        # Add magnet link action
        self.action_add_magnet = QAction(self.style().standardIcon(QStyle.SP_DirLinkIcon), "Add Magnet", self)
        self.action_add_magnet.triggered.connect(self.add_magnet_dialog)
        self.toolbar.addAction(self.action_add_magnet)
        
        self.toolbar.addSeparator()
        
        # Resume all action
        self.action_resume_all = QAction(self.style().standardIcon(QStyle.SP_MediaPlay), "Resume All", self)
        self.action_resume_all.triggered.connect(self.resume_all_torrents)
        self.toolbar.addAction(self.action_resume_all)
        
        # Pause all action
        self.action_pause_all = QAction(self.style().standardIcon(QStyle.SP_MediaPause), "Pause All", self)
        self.action_pause_all.triggered.connect(self.pause_all_torrents)
        self.toolbar.addAction(self.action_pause_all)
        
        self.toolbar.addSeparator()
        
        # Settings action
        self.action_settings = QAction(self.style().standardIcon(QStyle.SP_FileDialogDetailedView), "Settings", self)
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
        
        # Table signals
        self.torrent_table.pause_torrent.connect(self.pause_torrent)
        self.torrent_table.resume_torrent.connect(self.resume_torrent)
        self.torrent_table.remove_torrent.connect(self.handle_remove_torrent)
        self.torrent_table.itemSelectionChanged.connect(self.on_torrent_selection_changed)
        
        # Search engine signals
        self.search_engine.search_error.connect(self.on_error)
        
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
        self.torrent_table.itemSelectionChanged.connect(self.on_torrent_selection_changed)
        
        # Search engine signals
        self.search_engine.search_error.connect(self.on_error)
        
    @pyqtSlot(object)
    def on_torrent_added(self, torrent):
        """Handle torrent added signal"""
        # Add to torrent table
        self.torrent_table.add_torrent(torrent)
        
        # Connect status update signal
        torrent.status_updated.connect(self.torrent_table.update_torrent_status)
        torrent.status_updated.connect(self.refresh_active_torrent_details)
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
            self.status_dht_label.setText(f"DHT: {dht_nodes} nodes")
            self.status_dht_icon.setPixmap(self.style().standardIcon(QStyle.SP_DialogApplyButton).pixmap(QSize(16,16))) # Green check / connected icon
            self.status_dht_icon.setToolTip("DHT Connected")
        else:
            self.status_dht_label.setText("DHT: Off")
            self.status_dht_icon.setPixmap(self.style().standardIcon(QStyle.SP_DialogCancelButton).pixmap(QSize(16,16))) # Red X / disconnected icon
            self.status_dht_icon.setToolTip("DHT Disconnected")
        
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
        # Create (or get) the instance of SettingsDialog
        # It might be better to create it once, or ensure it's parented correctly if created each time.
        # For now, following the existing pattern of creating it here.
        self.settings_dialog = SettingsDialog(self) # Store as instance variable if needed by save_app_state

        # Populate general settings (save path)
        self.settings_dialog.save_path_edit.setText(self.default_save_path)
        
        # Populate interface settings
        self.settings_dialog.populate_interface_settings(
            self.confirm_on_exit_flag,
            self.start_minimized_flag,
            self.show_speed_in_title_flag
        )

        # Populate client settings from TorrentClient (Connection & Advanced tabs)
        current_client_settings_pack = self.torrent_client.get_session_settings() # Returns settings_pack
        self.settings_dialog.populate_client_settings(current_client_settings_pack)
        

        if self.settings_dialog.exec_() == QDialog.Accepted:
            # Apply and save general settings
            new_save_path = self.settings_dialog.save_path_edit.text()
            if os.path.isdir(new_save_path): # Basic validation
                self.default_save_path = new_save_path
            else:
                QMessageBox.warning(self, "Invalid Path", f"The specified download path is not valid: {new_save_path}")
                # Optionally, do not proceed with other settings if path is critical and invalid

            # Apply and save interface settings
            interface_settings = self.settings_dialog.get_interface_settings()
            self.confirm_on_exit_flag = interface_settings['confirm_on_exit']
            self.start_minimized_flag = interface_settings['start_minimized']
            self.show_speed_in_title_flag = interface_settings['show_speed_in_title']
            
            # Apply new client settings to TorrentClient
            new_client_settings_dict = self.settings_dialog.get_client_settings() # Returns dict with lt.settings_pack keys
            self.torrent_client.apply_session_settings(new_client_settings_dict)
            
            self.save_app_state() 

    def closeEvent(self, event):
        """Handle window close event"""
        # Optionally, skip confirmation if a setting indicates so
        reply = QMessageBox.question(
            self, "Confirm Exit",
            "Are you sure you want to exit? Active downloads will be stopped, and state will be saved.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        ) if self.confirm_on_exit_flag else QMessageBox.Yes # Skip if flag is false
        
        if reply == QMessageBox.Yes:
            print("Saving application state before closing...")
            # Pause all torrents and trigger resume data save for each
            for info_hash, torrent_handle_obj_wrapper in self.torrent_client.torrents.items():
                if torrent_handle_obj_wrapper.handle.is_valid():
                    print(f"Pausing and triggering save resume for {info_hash}")
                    torrent_handle_obj_wrapper.pause() # Pause the torrent
                    # Triggering save_resume_data again here ensures it's requested after pause
                    self.torrent_client.trigger_save_resume_data(info_hash)

            self.save_app_state() # This will again call trigger_save_resume_data for active ones, which is fine.
            
            # Allow some time for async operations like resume data saving to be processed by libtorrent alerts
            # This is a simple delay; a more robust solution would use signals or event loops.
            # Consider increasing this slightly if resume data still seems incomplete.
            print("Waiting for resume data to be processed...")
            time.sleep(1.0) # Increased sleep time slightly
            print("Exiting.")
            event.accept()
        else:
            event.ignore() 

    def on_torrent_selection_changed(self):
        selected_rows = self.torrent_table.selectionModel().selectedRows()
        if not selected_rows:
            # No selection, clear detail area
            if hasattr(self, 'torrent_detail_widget'): 
                 self.torrent_detail_widget.clear_details()
            return

        selected_row_index = selected_rows[0].row()
        if selected_row_index < self.torrent_table.rowCount() and self.torrent_table.torrent_hashes.get(selected_row_index):
            info_hash = self.torrent_table.torrent_hashes[selected_row_index]
            if info_hash in self.torrent_client.torrents:
                torrent_handle_obj = self.torrent_client.torrents[info_hash]
                status = torrent_handle_obj.get_status()
                
                if hasattr(self, 'torrent_detail_widget') and status:
                    self.torrent_detail_widget.update_details(status)
            else:
                # Info hash known by table but not by client (should be rare, implies inconsistency)
                if hasattr(self, 'torrent_detail_widget'):
                    self.torrent_detail_widget.clear_details()
                    # Optionally, add a message like: self.torrent_detail_widget.lbl_name.setText("Error: Torrent data not found in client.")
        else:
             # Invalid row or info_hash not found in table's mapping
             if hasattr(self, 'torrent_detail_widget'):
                 self.torrent_detail_widget.clear_details()
                 # Optionally, add a message like: self.torrent_detail_widget.lbl_name.setText("Please select a valid torrent.") 

    @pyqtSlot(dict)
    def refresh_active_torrent_details(self, status_dict):
        if not hasattr(self, 'torrent_detail_widget') or not self.torrent_detail_widget._current_info_hash:
            return # Detail widget not ready or no torrent selected in it
        
        if status_dict and status_dict.get('info_hash') == self.torrent_detail_widget._current_info_hash:
            self.torrent_detail_widget.update_details(status_dict)

    @pyqtSlot(str, int, int)
    def on_file_priority_changed(self, info_hash, file_index, priority_level):
        success = self.torrent_client.set_torrent_file_priority(info_hash, file_index, priority_level)
        if success:
            # Refresh the torrent details to show the updated priority
            # This assumes the status_updated signal from TorrentHandle will eventually update the table
            # For immediate feedback in the detail panel, we can re-fetch and update here.
            if info_hash in self.torrent_client.torrents:
                status = self.torrent_client.torrents[info_hash].get_status()
                if hasattr(self, 'torrent_detail_widget') and status:
                    self.torrent_detail_widget.update_details(status)
                # Also, request the main table to update that specific torrent's display if needed,
                # though the TorrentHandle's status_updated signal should ideally cover this.
                # self.torrent_table.update_torrent_status(status) 
            QMessageBox.information(self, "Priority Set", f"Priority for file index {file_index} set to {priority_level}.")
        else:
            QMessageBox.warning(self, "Error", "Could not set file priority. Check logs.") 