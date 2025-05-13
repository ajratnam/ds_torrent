from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                            QSpinBox, QPushButton, QLineEdit, QFileDialog,
                            QTabWidget, QWidget, QGroupBox, QFormLayout,
                            QCheckBox, QComboBox)
from PyQt5.QtCore import Qt

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
        
    def setup_general_tab(self):
        """Setup general settings tab"""
        layout = QVBoxLayout(self.general_tab)
        
        # Download location group
        download_group = QGroupBox("Download Location")
        download_layout = QHBoxLayout(download_group)
        
        self.save_path_edit = QLineEdit()
        self.save_path_edit.setText(self.parent().default_save_path)
        
        self.browse_button = QPushButton("Browse...")
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
        
        self.pex_check = QCheckBox()
        self.pex_check.setChecked(True)
        
        self.lsd_check = QCheckBox()
        self.lsd_check.setChecked(True)
        
        self.encryption_combo = QComboBox()
        self.encryption_combo.addItems(["Prefer encryption", "Require encryption", "Disable encryption"])
        
        bt_layout.addRow("Enable DHT:", self.dht_check)
        bt_layout.addRow("Enable Peer Exchange:", self.pex_check)
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