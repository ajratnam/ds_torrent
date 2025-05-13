from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                            QSpinBox, QPushButton, QLineEdit, QFileDialog,
                            QTabWidget, QWidget, QGroupBox, QFormLayout,
                            QCheckBox, QComboBox, QListWidget, QStackedWidget, QListWidgetItem, QSplitter)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QStyle
import libtorrent as lt
import os

class SettingsDialog(QDialog):
    """Dialog for application settings"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Settings")
        self.setMinimumWidth(600)
        self.setMinimumHeight(450)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup dialog UI with a list/stack layout."""
        main_layout = QVBoxLayout(self)

        content_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(content_splitter, 1)

        # Category List (Left Side)
        self.category_list = QListWidget()
        self.category_list.setMaximumWidth(200)
        self.category_list.setMinimumWidth(120)
        self.category_list.setStyleSheet(""" QListView::item { padding: 8px 5px; } """)
        content_splitter.addWidget(self.category_list)

        # Settings Stack (Right Side)
        self.settings_stack = QStackedWidget()
        content_splitter.addWidget(self.settings_stack)

        # Set initial splitter sizes (e.g., 30% for list, 70% for stack)
        content_splitter.setSizes([150, 350])

        # Create and add pages to the stack
        self.page_general = QWidget()
        self.setup_general_page(self.page_general)
        self.settings_stack.addWidget(self.page_general)

        self.page_connection = QWidget()
        self.setup_connection_page(self.page_connection)
        self.settings_stack.addWidget(self.page_connection)

        self.page_advanced = QWidget()
        self.setup_advanced_page(self.page_advanced)
        self.settings_stack.addWidget(self.page_advanced)
        
        # Populate category list
        icons_base_path = os.path.join(os.path.dirname(__file__), "icons")

        self.item_general = QListWidgetItem("General")
        try:
            icon_general = QIcon(os.path.join(icons_base_path, "settings_general.png"))
            if not icon_general.isNull(): self.item_general.setIcon(icon_general)
            else: self.item_general.setIcon(self.style().standardIcon(QStyle.SP_FileDialogInfoView))
        except: self.item_general.setIcon(self.style().standardIcon(QStyle.SP_FileDialogInfoView))
        self.category_list.addItem(self.item_general)

        self.item_connection = QListWidgetItem("Connection")
        try:
            icon_connection = QIcon(os.path.join(icons_base_path, "settings_connection.png"))
            if not icon_connection.isNull(): self.item_connection.setIcon(icon_connection)
            else: self.item_connection.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        except: self.item_connection.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self.category_list.addItem(self.item_connection)

        self.item_advanced = QListWidgetItem("Advanced")
        try:
            icon_advanced = QIcon(os.path.join(icons_base_path, "settings_advanced.png"))
            if not icon_advanced.isNull(): self.item_advanced.setIcon(icon_advanced)
            else: self.item_advanced.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        except: self.item_advanced.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.category_list.addItem(self.item_advanced)

        self.category_list.setIconSize(QSize(20, 20))
        self.category_list.currentRowChanged.connect(self.settings_stack.setCurrentIndex)
        self.category_list.setCurrentRow(0)

        # Add buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        
        main_layout.addLayout(button_layout)
        
    def setup_general_page(self, page_widget):
        """Setup general settings page."""
        layout = QVBoxLayout(page_widget)
        
        # Download location group
        download_group = QGroupBox("Download Location")
        download_layout = QHBoxLayout(download_group)
        
        self.save_path_edit = QLineEdit()
        parent_obj = self.parent()
        default_path = parent_obj.default_save_path if hasattr(parent_obj, 'default_save_path') else os.path.expanduser("~")
        self.save_path_edit.setText(default_path)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.browse_button.clicked.connect(self.browse_save_path)
        
        download_layout.addWidget(self.save_path_edit)
        download_layout.addWidget(self.browse_button)
        
        layout.addWidget(download_group)
        
        # Interface settings group
        interface_group = QGroupBox("Application Interface")
        interface_layout = QFormLayout(interface_group)
        
        self.start_minimized_check = QCheckBox("Start minimized to system tray")
        self.show_speed_in_title_check = QCheckBox("Show transfer speed in window title")
        self.confirm_on_exit_check = QCheckBox("Confirm before exiting application")
        
        interface_layout.addRow(self.start_minimized_check)
        interface_layout.addRow(self.show_speed_in_title_check)
        interface_layout.addRow(self.confirm_on_exit_check)
        
        layout.addWidget(interface_group)
        layout.addStretch()

    def setup_connection_page(self, page_widget):
        """Setup connection settings page."""
        layout = QVBoxLayout(page_widget)
        
        # Speed limits group
        limits_group = QGroupBox("Speed Limits")
        limits_layout = QFormLayout(limits_group)
        
        self.download_limit_spin = QSpinBox()
        self.download_limit_spin.setRange(0, 100000)
        self.download_limit_spin.setValue(0)
        self.download_limit_spin.setSuffix(" KiB/s (0 = unlimited)")
        self.download_limit_spin.setSpecialValueText("Unlimited")
        
        self.upload_limit_spin = QSpinBox()
        self.upload_limit_spin.setRange(0, 100000)
        self.upload_limit_spin.setValue(0)
        self.upload_limit_spin.setSuffix(" KiB/s (0 = unlimited)")
        self.upload_limit_spin.setSpecialValueText("Unlimited")
        
        limits_layout.addRow("Download limit:", self.download_limit_spin)
        limits_layout.addRow("Upload limit:", self.upload_limit_spin)
        
        layout.addWidget(limits_group)
        
        # Connection settings group
        conn_group = QGroupBox("Network Connection")
        conn_layout = QFormLayout(conn_group)
        
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(6881)
        
        self.max_conn_spin = QSpinBox()
        self.max_conn_spin.setRange(1, 5000)
        self.max_conn_spin.setValue(200)
        
        self.max_conn_per_torrent_spin = QSpinBox()
        self.max_conn_per_torrent_spin.setRange(1, 1000)
        self.max_conn_per_torrent_spin.setValue(50)
        
        conn_layout.addRow("Listening Port:", self.port_spin)
        conn_layout.addRow("Global max connections:", self.max_conn_spin)
        conn_layout.addRow("Max connections per torrent:", self.max_conn_per_torrent_spin)
        
        layout.addWidget(conn_group)
        layout.addStretch()

    def setup_advanced_page(self, page_widget):
        """Setup advanced settings page."""
        layout = QVBoxLayout(page_widget)
        
        # BitTorrent settings group
        bt_group = QGroupBox("BitTorrent Protocol")
        bt_layout = QFormLayout(bt_group)
        
        self.dht_check = QCheckBox("Enable DHT (Distributed Hash Table)")
        self.dht_check.setChecked(True)
        
        self.lsd_check = QCheckBox("Enable LSD (Local Peer Discovery)")
        self.lsd_check.setChecked(True)
        
        self.encryption_combo = QComboBox()
        self.encryption_combo.addItems(["Prefer Encryption", "Require Encryption", "Disable Encryption"])
        self.encryption_combo.setToolTip("Controls how encryption is used for peer connections.")

        bt_layout.addRow(self.dht_check)
        bt_layout.addRow(self.lsd_check)
        bt_layout.addRow("Encryption Mode:", self.encryption_combo)
        
        layout.addWidget(bt_group)
        layout.addStretch()
        
    def populate_interface_settings(self, confirm_on_exit, start_minimized, show_speed_in_title):
        """Populate the interface settings checkboxes."""
        self.confirm_on_exit_check.setChecked(confirm_on_exit)
        self.start_minimized_check.setChecked(start_minimized)
        self.show_speed_in_title_check.setChecked(show_speed_in_title)

    def get_interface_settings(self):
        """Return a dictionary of the interface settings."""
        return {
            'confirm_on_exit': self.confirm_on_exit_check.isChecked(),
            'start_minimized': self.start_minimized_check.isChecked(),
            'show_speed_in_title': self.show_speed_in_title_check.isChecked()
        }

    def populate_client_settings(self, client_settings_dict):
        """Populate connection and advanced settings from a settings dictionary."""
        # Connection Page Widgets
        self.download_limit_spin.setValue(client_settings_dict.get('download_rate_limit', 0) // 1024)
        self.upload_limit_spin.setValue(client_settings_dict.get('upload_rate_limit', 0) // 1024)
        
        listen_interfaces_str = client_settings_dict.get('listen_interfaces', '0.0.0.0:6881')
        try:
            port_str = listen_interfaces_str.split(':')[1]
            port = int(port_str)
            self.port_spin.setValue(port)
        except (IndexError, ValueError) as e:
            print(f"Could not parse port from listen_interfaces: '{listen_interfaces_str}'. Error: {e}")
            self.port_spin.setValue(6881)
        
        self.max_conn_spin.setValue(client_settings_dict.get('connections_limit', 200))
        self.max_conn_per_torrent_spin.setValue(client_settings_dict.get('unchoke_slots_limit', 50))

        # Advanced Page Widgets
        self.dht_check.setChecked(client_settings_dict.get('enable_dht', True))
        self.lsd_check.setChecked(client_settings_dict.get('enable_lsd', True))

        out_policy = client_settings_dict.get('out_enc_policy', lt.enc_level.pe_rc4) 
        in_policy = client_settings_dict.get('in_enc_policy', lt.enc_level.pe_rc4)
        allowed_level = client_settings_dict.get('allowed_enc_level', lt.enc_level.rc4)

        if (out_policy == lt.enc_level.pe_plaintext and
            in_policy == lt.enc_level.pe_plaintext and
            allowed_level == lt.enc_level.plaintext):
            self.encryption_combo.setCurrentIndex(2)
        elif (out_policy == lt.enc_level.pe_rc4 and
              in_policy == lt.enc_level.pe_rc4 and
              allowed_level == lt.enc_level.rc4):
            self.encryption_combo.setCurrentIndex(1)
        else: 
            self.encryption_combo.setCurrentIndex(0)

    def get_client_settings(self):
        """Return a dictionary of client settings with string keys for libtorrent session."""
        settings = {}
        # Connection Page Widgets
        settings['download_rate_limit'] = self.download_limit_spin.value() * 1024
        settings['upload_rate_limit'] = self.upload_limit_spin.value() * 1024
        settings['listen_interfaces'] = f"0.0.0.0:{self.port_spin.value()}"
        settings['connections_limit'] = self.max_conn_spin.value()
        settings['unchoke_slots_limit'] = self.max_conn_per_torrent_spin.value()

        # Advanced Page Widgets
        settings['enable_dht'] = self.dht_check.isChecked()
        settings['enable_lsd'] = self.lsd_check.isChecked()

        enc_index = self.encryption_combo.currentIndex()
        if enc_index == 0:
            settings['out_enc_policy'] = lt.enc_level.pe_both
            settings['in_enc_policy'] = lt.enc_level.pe_both
            settings['allowed_enc_level'] = lt.enc_level.both
        elif enc_index == 1:
            settings['out_enc_policy'] = lt.enc_level.pe_rc4
            settings['in_enc_policy'] = lt.enc_level.pe_rc4
            settings['allowed_enc_level'] = lt.enc_level.rc4
        elif enc_index == 2:
            settings['out_enc_policy'] = lt.enc_level.pe_plaintext
            settings['in_enc_policy'] = lt.enc_level.pe_plaintext
            settings['allowed_enc_level'] = lt.enc_level.plaintext
        return settings

    def browse_save_path(self):
        """Open file dialog to select download location"""
        current_path = self.save_path_edit.text()
        if not os.path.isdir(current_path):
            current_path = os.path.expanduser("~")

        path = QFileDialog.getExistingDirectory(
            self, "Select Download Location", current_path
        )
        
        if path:
            self.save_path_edit.setText(path)
            
    def get_save_path(self):
        return self.save_path_edit.text()

    def get_download_limit(self):
        """Get the download speed limit in KB/s"""
        return self.download_limit_spin.value()
        
    def get_upload_limit(self):
        """Get the upload speed limit in KB/s"""
        return self.upload_limit_spin.value() 