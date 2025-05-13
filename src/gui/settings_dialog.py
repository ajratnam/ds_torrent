from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                            QSpinBox, QPushButton, QLineEdit, QFileDialog,
                            QTabWidget, QWidget, QGroupBox, QFormLayout,
                            QCheckBox, QComboBox)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QStyle
import libtorrent as lt

class SettingsDialog(QDialog):
    """Dialog for application settings"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout(self)
        
        # Create tabs
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create general settings tab
        self.general_tab = QWidget()
        self.tab_widget.addTab(self.general_tab, "General")
        
        # Create connection settings tab
        self.connection_tab = QWidget()
        self.tab_widget.addTab(self.connection_tab, "Connection")
        
        # Create advanced settings tab
        self.advanced_tab = QWidget()
        self.tab_widget.addTab(self.advanced_tab, "Advanced")
        
        # Setup tabs
        self.setup_general_tab()
        self.setup_connection_tab()
        self.setup_advanced_tab()
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
    def setup_general_tab(self):
        """Setup general settings tab"""
        layout = QVBoxLayout(self.general_tab)
        
        # Download location group
        download_group = QGroupBox("Download Location")
        download_layout = QHBoxLayout(download_group)
        
        self.save_path_edit = QLineEdit()
        self.save_path_edit.setText(self.parent().default_save_path)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.browse_button.clicked.connect(self.browse_save_path)
        
        download_layout.addWidget(self.save_path_edit)
        download_layout.addWidget(self.browse_button)
        
        layout.addWidget(download_group)
        
        # Interface settings group
        interface_group = QGroupBox("Interface")
        interface_layout = QFormLayout(interface_group)
        
        self.start_minimized_check = QCheckBox()
        self.show_speed_in_title_check = QCheckBox()
        self.confirm_on_exit_check = QCheckBox()
        
        interface_layout.addRow("Start minimized to tray:", self.start_minimized_check)
        interface_layout.addRow("Show speed in window title:", self.show_speed_in_title_check)
        interface_layout.addRow("Confirm on exit:", self.confirm_on_exit_check)
        
        layout.addWidget(interface_group)
        
        # Add stretch to push everything to the top
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
        # Connection Tab
        self.download_limit_spin.setValue(client_settings_dict.get('download_rate_limit', 0) // 1024)
        self.upload_limit_spin.setValue(client_settings_dict.get('upload_rate_limit', 0) // 1024)
        
        listen_interfaces_str = client_settings_dict.get('listen_interfaces', '0.0.0.0:6881')
        try:
            port = int(listen_interfaces_str.split(':')[1])
            self.port_spin.setValue(port)
        except (IndexError, ValueError) as e:
            print(f"Could not parse port from listen_interfaces: '{listen_interfaces_str}'. Error: {e}")
            self.port_spin.setValue(6881)
        self.max_conn_spin.setValue(client_settings_dict.get('connections_limit', 100))
        default_unchoke_slots = 8
        self.max_conn_per_torrent_spin.setValue(client_settings_dict.get('unchoke_slots_limit', default_unchoke_slots))

        # Advanced Tab
        self.dht_check.setChecked(client_settings_dict.get('enable_dht', True))
        self.lsd_check.setChecked(client_settings_dict.get('enable_lsd', True))

        # Encryption settings
        # Values in client_settings_dict for these are expected to be integers from libtorrent constants
        # For policies (out_enc_policy, in_enc_policy), use pe_* variants from lt.enc_level
        # For allowed level (allowed_enc_level), use direct variants from lt.enc_level
        out_policy = client_settings_dict.get('out_enc_policy', lt.enc_level.pe_rc4) 
        in_policy = client_settings_dict.get('in_enc_policy', lt.enc_level.pe_rc4)
        allowed_level = client_settings_dict.get('allowed_enc_level', lt.enc_level.rc4)

        if (out_policy == lt.enc_level.pe_plaintext and
            in_policy == lt.enc_level.pe_plaintext and
            allowed_level == lt.enc_level.plaintext):
            self.encryption_combo.setCurrentIndex(2) # Disable
        elif (out_policy == lt.enc_level.pe_rc4 and
              in_policy == lt.enc_level.pe_rc4 and
              allowed_level == lt.enc_level.rc4):
            self.encryption_combo.setCurrentIndex(1) # Require
        else: # Covers 'both' policies (pe_both) and 'both' allowed_level, or defaults to Prefer
              # lt.enc_level.pe_both for policies, lt.enc_level.both for level maps to "Prefer" UI
            self.encryption_combo.setCurrentIndex(0) # Prefer

    def get_client_settings(self):
        """Return a dictionary of client settings with string keys for libtorrent session."""
        settings = {}
        # Connection Tab
        settings['download_rate_limit'] = self.download_limit_spin.value() * 1024
        settings['upload_rate_limit'] = self.upload_limit_spin.value() * 1024
        settings['listen_interfaces'] = f"0.0.0.0:{self.port_spin.value()}"
        settings['connections_limit'] = self.max_conn_spin.value()
        settings['unchoke_slots_limit'] = self.max_conn_per_torrent_spin.value()

        # Advanced Tab
        settings['enable_dht'] = self.dht_check.isChecked()
        settings['enable_lsd'] = self.lsd_check.isChecked()

        # Encryption
        # UI "Prefer Encryption" (idx 0)  => out_enc_policy=pe_both, in_enc_policy=pe_both, allowed_enc_level=both
        # UI "Require Encryption" (idx 1) => out_enc_policy=pe_rc4, in_enc_policy=pe_rc4, allowed_enc_level=rc4
        # UI "Disable Encryption" (idx 2) => out_enc_policy=pe_plaintext, in_enc_policy=pe_plaintext, allowed_enc_level=plaintext
        enc_index = self.encryption_combo.currentIndex()
        if enc_index == 0: # Prefer encryption
            settings['out_enc_policy'] = lt.enc_level.pe_both
            settings['in_enc_policy'] = lt.enc_level.pe_both
            settings['allowed_enc_level'] = lt.enc_level.both
        elif enc_index == 1: # Require encryption
            settings['out_enc_policy'] = lt.enc_level.pe_rc4
            settings['in_enc_policy'] = lt.enc_level.pe_rc4
            settings['allowed_enc_level'] = lt.enc_level.rc4
        elif enc_index == 2: # Disable encryption
            settings['out_enc_policy'] = lt.enc_level.pe_plaintext
            settings['in_enc_policy'] = lt.enc_level.pe_plaintext
            settings['allowed_enc_level'] = lt.enc_level.plaintext
        return settings

    def setup_connection_tab(self):
        """Setup connection settings tab"""
        layout = QVBoxLayout(self.connection_tab)
        
        # Speed limits group
        limits_group = QGroupBox("Speed Limits")
        limits_layout = QFormLayout(limits_group)
        
        self.download_limit_spin = QSpinBox()
        self.download_limit_spin.setRange(0, 10000)
        self.download_limit_spin.setValue(0)
        self.download_limit_spin.setSuffix(" KiB/s (0: unlimited)")
        
        self.upload_limit_spin = QSpinBox()
        self.upload_limit_spin.setRange(0, 10000)
        self.upload_limit_spin.setValue(0)
        self.upload_limit_spin.setSuffix(" KiB/s (0: unlimited)")
        
        limits_layout.addRow("Download limit:", self.download_limit_spin)
        limits_layout.addRow("Upload limit:", self.upload_limit_spin)
        
        layout.addWidget(limits_group)
        
        # Connection settings group
        conn_group = QGroupBox("Connection Settings")
        conn_layout = QFormLayout(conn_group)
        
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(6881)
        
        self.max_conn_spin = QSpinBox()
        self.max_conn_spin.setRange(1, 500)
        self.max_conn_spin.setValue(100)
        
        self.max_conn_per_torrent_spin = QSpinBox()
        self.max_conn_per_torrent_spin.setRange(1, 100)
        self.max_conn_per_torrent_spin.setValue(50)
        
        conn_layout.addRow("Port used:", self.port_spin)
        conn_layout.addRow("Max connections:", self.max_conn_spin)
        conn_layout.addRow("Max connections per torrent:", self.max_conn_per_torrent_spin)
        
        layout.addWidget(conn_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
    def setup_advanced_tab(self):
        """Setup advanced settings tab"""
        layout = QVBoxLayout(self.advanced_tab)
        
        # BitTorrent settings group
        bt_group = QGroupBox("BitTorrent")
        bt_layout = QFormLayout(bt_group)
        
        self.dht_check = QCheckBox()
        self.dht_check.setChecked(True)
        
        self.lsd_check = QCheckBox()
        self.lsd_check.setChecked(True)
        
        self.encryption_combo = QComboBox()
        self.encryption_combo.addItems(["Prefer encryption", "Require encryption", "Disable encryption"])
        
        bt_layout.addRow("Enable DHT:", self.dht_check)
        bt_layout.addRow("Enable Local Peer Discovery:", self.lsd_check)
        bt_layout.addRow("Encryption mode:", self.encryption_combo)
        
        layout.addWidget(bt_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
    def browse_save_path(self):
        """Open file dialog to select download location"""
        path = QFileDialog.getExistingDirectory(
            self, "Select Download Location", self.save_path_edit.text()
        )
        
        if path:
            self.save_path_edit.setText(path)
            
    def get_download_limit(self):
        """Get the download speed limit in KB/s"""
        return self.download_limit_spin.value()
        
    def get_upload_limit(self):
        """Get the upload speed limit in KB/s"""
        return self.upload_limit_spin.value() 