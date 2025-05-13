from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QFormLayout, 
                            QLabel, QLineEdit, QGroupBox, QTableWidget, 
                            QTableWidgetItem, QHeaderView, QProgressBar,
                            QMenu, QAction)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter # Import QPainter
import datetime
import math # Import math module

def _format_bytes(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024))) # Use math.log and math.floor
    p = math.pow(1024, i) # Use math.pow
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

class FilesTableWidget(QTableWidget): # Create a dedicated class for FilesTable
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["Path", "Size", "Progress", "Downloaded", "Priority"])
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.verticalHeader().setVisible(False)
        self.setContextMenuPolicy(Qt.CustomContextMenu) # Context menu connection will be in TorrentDetailWidget

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch) # Path
        header.setSectionResizeMode(1, QHeaderView.Interactive) # Size
        header.setSectionResizeMode(2, QHeaderView.Stretch) # Progress
        header.setSectionResizeMode(3, QHeaderView.Interactive) # Downloaded
        header.setSectionResizeMode(4, QHeaderView.Interactive) # Priority

        self.setColumnWidth(1, 100) # Size
        self.setColumnWidth(3, 100) # Downloaded
        self.setColumnWidth(4, 100) # Priority

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.rowCount() == 0:
            painter = QPainter(self.viewport())
            painter.save()
            font = self.font()
            font.setPointSize(11) # Slightly smaller for detail view
            painter.setFont(font)
            text_color = QColor("#888888")
            painter.setPen(text_color)
            # Determine if metadata is still loading vs. genuinely no files
            # This might need a flag from TorrentDetailWidget or status_dict
            # if self.parentWidget() and hasattr(self.parentWidget(), '_current_info_hash') and not self.parentWidget()._current_info_hash:
            #     placeholder_text = "Select a torrent to view files."
            # elif self.parentWidget() and hasattr(self.parentWidget(), 'is_metadata_loading') and self.parentWidget().is_metadata_loading:
            #     placeholder_text = "Fetching file information..."
            placeholder_text = "No files in torrent or metadata not yet received."
            painter.drawText(self.viewport().rect(), Qt.AlignCenter, placeholder_text)
            painter.restore()

class PeersTableWidget(QTableWidget): # Create a dedicated class for PeersTable
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(9) 
        self.setHorizontalHeaderLabels([
            "IP Address", "Port", "Client", "Progress", 
            "Down Speed", "Up Speed", "Flags", "Conn. Type", "Source"
        ])
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive) 
        header.setSectionResizeMode(1, QHeaderView.Interactive) 
        header.setSectionResizeMode(2, QHeaderView.Stretch)   
        header.setSectionResizeMode(3, QHeaderView.Interactive) 
        header.setSectionResizeMode(6, QHeaderView.Interactive) 
        header.setSectionResizeMode(7, QHeaderView.Interactive) 
        header.setSectionResizeMode(8, QHeaderView.Interactive) 

        self.setColumnWidth(0, 120) 
        self.setColumnWidth(1, 50)  
        self.setColumnWidth(3, 80)  
        self.setColumnWidth(4, 80)  
        self.setColumnWidth(5, 80)  
        self.setColumnWidth(6, 80)  
        self.setColumnWidth(7, 80)  
        self.setColumnWidth(8, 80)  

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.rowCount() == 0:
            painter = QPainter(self.viewport())
            painter.save()
            font = self.font()
            font.setPointSize(11)
            painter.setFont(font)
            text_color = QColor("#888888")
            painter.setPen(text_color)
            placeholder_text = "No connected peers."
            # if self.parentWidget() and hasattr(self.parentWidget(), '_current_info_hash') and not self.parentWidget()._current_info_hash:
            #     placeholder_text = "Select a torrent to view peers."
            painter.drawText(self.viewport().rect(), Qt.AlignCenter, placeholder_text)
            painter.restore()

class TorrentDetailWidget(QWidget):
    """Widget to display detailed information about a selected torrent."""
    # Signal: info_hash, file_index, priority_level
    file_priority_changed = pyqtSignal(str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_info_hash = None # Store the info_hash of the displayed torrent
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0) # Use available space

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Create tabs
        self._create_general_tab()
        self._create_files_tab()
        self._create_peers_tab()
        # self._create_trackers_tab() # Remove this call
        # self._create_speed_tab() # Placeholder for future

    def _create_general_tab(self):
        self.general_tab = QWidget()
        layout = QFormLayout(self.general_tab)
        layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        layout.setLabelAlignment(Qt.AlignRight)

        # Information fields (QLabel for read-only info)
        self.lbl_name = QLabel("N/A")
        self.lbl_save_path = QLabel("N/A")
        self.lbl_info_hash = QLabel("N/A")
        self.lbl_total_size = QLabel("N/A")
        self.lbl_num_pieces = QLabel("N/A")
        self.lbl_piece_length = QLabel("N/A")
        self.lbl_added_on = QLabel("N/A")
        self.lbl_status = QLabel("N/A")
        self.lbl_comment = QLabel("N/A") # Placeholder for torrent comment
        self.lbl_created_by = QLabel("N/A") # Placeholder for creator
        self.lbl_creation_date = QLabel("N/A") # Placeholder for creation date
        self.lbl_availability = QLabel("N/A")

        layout.addRow("<b>Name:</b>", self.lbl_name)
        layout.addRow("<b>Save Path:</b>", self.lbl_save_path)
        layout.addRow("<b>Status:</b>", self.lbl_status)
        layout.addRow("<b>Total Size:</b>", self.lbl_total_size)
        layout.addRow("<b>Info Hash:</b>", self.lbl_info_hash)
        layout.addRow("<b>Pieces:</b>", self.lbl_num_pieces)
        layout.addRow("<b>Piece Length:</b>", self.lbl_piece_length)
        layout.addRow("<b>Availability:</b>", self.lbl_availability)
        layout.addRow("<b>Added On:</b>", self.lbl_added_on)
        # layout.addRow("<b>Comment:</b>", self.lbl_comment) 
        # layout.addRow("<b>Created By:</b>", self.lbl_created_by)
        # layout.addRow("<b>Creation Date:</b>", self.lbl_creation_date)

        self.tab_widget.addTab(self.general_tab, "General")

    def _create_files_tab(self):
        self.files_tab_page = QWidget() # Create a page widget
        layout = QVBoxLayout(self.files_tab_page)
        layout.setContentsMargins(5, 5, 5, 5)

        self.files_table = FilesTableWidget() # Use the new class
        self.files_table.customContextMenuRequested.connect(self._show_files_table_context_menu)
        layout.addWidget(self.files_table)
        self.tab_widget.addTab(self.files_tab_page, "Files")

    def _create_peers_tab(self):
        self.peers_tab_page = QWidget() # Create a page widget
        layout = QVBoxLayout(self.peers_tab_page)
        layout.setContentsMargins(5, 5, 5, 5)

        self.peers_table = PeersTableWidget() # Use the new class
        layout.addWidget(self.peers_table)
        self.tab_widget.addTab(self.peers_tab_page, "Peers")

    def _show_files_table_context_menu(self, position):
        selected_items = self.files_table.selectedItems()
        if not selected_items or self._current_info_hash is None:
            return

        file_index = self.files_table.row(selected_items[0]) # Get the row index, which is the file_index
        if file_index < 0:
            return

        menu = QMenu()
        priorities = {
            "Maximal Priority": 7,
            "High Priority": 6,
            "Normal Priority": 4, # libtorrent default for new files is 4 if not specified
            "Don't Download": 0
        }

        # Get current priority to disable the corresponding menu item (optional)
        # current_priority_text = self.files_table.item(file_index, 4).text()
        # current_priority_val = -1 # Determine this based on text if needed

        for text, level in priorities.items():
            action = QAction(text, self)
            # if level == current_priority_val: # Optional: disable current priority
            #     action.setEnabled(False)
            action.triggered.connect(lambda checked=False, ih=self._current_info_hash, fi=file_index, pl=level: 
                                     self.file_priority_changed.emit(ih, fi, pl))
            menu.addAction(action)
        
        menu.exec_(self.files_table.viewport().mapToGlobal(position))

    def _format_file_priority(self, priority_val):
        default_color = QColor("#E0E0E0") # Default text color from theme
        if priority_val == 0:
            return "Don't Download", QColor("#9E9E9E") # Medium Gray
        elif priority_val == 1 or priority_val == 4: # Treat 1 and 4 as Normal
            return "Normal", default_color
        elif priority_val == 6:
            return "High", QColor("#FFB74D") # Light Orange
        elif priority_val == 7:
            return "Maximal", QColor("#40E0D0") # Vibrant Teal
        else:
            return f"Unknown ({priority_val})", default_color

    def update_details(self, status_dict):
        if not status_dict:
            self.clear_details()
            return
        
        self._current_info_hash = status_dict.get('info_hash') # Store info_hash

        self.lbl_name.setText(status_dict.get('name', 'N/A'))
        self.lbl_name.setToolTip(status_dict.get('name', 'N/A'))
        self.lbl_save_path.setText(status_dict.get('save_path', 'N/A'))
        self.lbl_save_path.setToolTip(status_dict.get('save_path', 'N/A'))
        self.lbl_info_hash.setText(status_dict.get('info_hash', 'N/A'))
        self.lbl_status.setText(status_dict.get('state', 'N/A').capitalize())
        self.lbl_total_size.setText(_format_bytes(status_dict.get('total_size', 0)))
        
        num_pieces_val = status_dict.get('num_pieces', 0)
        piece_length_val = status_dict.get('piece_length', 0)
        self.lbl_num_pieces.setText(f"{num_pieces_val} ({_format_bytes(piece_length_val)} each)")
        # self.lbl_piece_length.setText(_format_bytes(piece_length_val)) # Combined with num_pieces

        availability = status_dict.get('distributed_copies', -1.0)
        if availability == -1.0: # libtorrent often returns -1 for full copies when unknown
            # Calculate from pieces we have / total pieces if possible
            # This is a rough estimate and might not be what 'distributed_copies' truly represents
            # if status_dict.get('progress', 0) > 0 and num_pieces > 0:
            #     pieces_have = int(status_dict.get('progress', 0) / 100.0 * num_pieces)
            #     self.lbl_availability.setText(f"{pieces_have / num_pieces:.2f} (estimated from progress)")
            # else:
            self.lbl_availability.setText("N/A")
        else:
            self.lbl_availability.setText(f"{availability:.2f}")

        added_ts = status_dict.get('added_on')
        if added_ts:
            try:
                dt_object = datetime.datetime.fromtimestamp(added_ts)
                self.lbl_added_on.setText(dt_object.strftime("%Y-%m-%d %H:%M:%S"))
            except ValueError: # Handle potential timestamp conversion errors for very old/future dates
                self.lbl_added_on.setText("Invalid Date")
            except:
                self.lbl_added_on.setText("N/A")
        else:
            self.lbl_added_on.setText("N/A")

        # Update files tab
        if hasattr(self, 'files_table'):
            if self._current_info_hash != status_dict.get('info_hash'): # If torrent changed, clear first
                self.files_table.setRowCount(0)
            files_data = status_dict.get('files', [])
            if files_data:
                self.files_table.setRowCount(len(files_data))
                for i, file_info in enumerate(files_data):
                    self.files_table.setItem(i, 0, QTableWidgetItem(file_info.get('path', 'N/A')))
                    
                    size_item = QTableWidgetItem(_format_bytes(file_info.get('size', 0)))
                    size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.files_table.setItem(i, 1, size_item)
                    
                    progress_val = file_info.get('progress', 0)
                    progress_bar = QProgressBar()
                    progress_bar.setValue(int(progress_val))
                    progress_bar.setTextVisible(True)
                    progress_bar.setFormat(f"{progress_val:.1f}%")
                    # Progress bar styling is handled globally, specific text color if needed:
                    # progress_bar.setStyleSheet("QProgressBar { color: #1E1E1E; } QProgressBar::chunk { background-color: #40E0D0; margin: 1px; }")
                    self.files_table.setCellWidget(i, 2, progress_bar)
                    
                    downloaded_item = QTableWidgetItem(_format_bytes(file_info.get('downloaded', 0)))
                    downloaded_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.files_table.setItem(i, 3, downloaded_item)
                    
                    priority_val = file_info.get('priority', 0)
                    priority_text, priority_color = self._format_file_priority(priority_val)
                    priority_item = QTableWidgetItem(priority_text)
                    priority_item.setForeground(priority_color)
                    priority_item.setTextAlignment(Qt.AlignCenter)
                    self.files_table.setItem(i, 4, priority_item)
            elif not status_dict.get('has_metadata', False):
                self.files_table.setRowCount(0) # Clear if no metadata, placeholder will show "fetching"
            else:
                self.files_table.setRowCount(0) # No files, placeholder will show "No files"
            self.files_table.viewport().update()

        # Update peers tab
        if hasattr(self, 'peers_table'):
            if self._current_info_hash != status_dict.get('info_hash'):
                self.peers_table.setRowCount(0)
            peers_data = status_dict.get('peers', [])
            if peers_data:
                self.peers_table.setRowCount(len(peers_data))
                for i, peer_info in enumerate(peers_data):
                    self.peers_table.setItem(i, 0, QTableWidgetItem(peer_info.get('ip', 'N/A')))
                    
                    port_item = QTableWidgetItem(str(peer_info.get('port', 'N/A')))
                    port_item.setTextAlignment(Qt.AlignCenter)
                    self.peers_table.setItem(i, 1, port_item)
                    
                    self.peers_table.setItem(i, 2, QTableWidgetItem(peer_info.get('client', 'N/A')))
                    
                    progress_val = peer_info.get('progress', 0)
                    item_progress = QTableWidgetItem(f"{progress_val:.1f}%")
                    item_progress.setTextAlignment(Qt.AlignCenter)
                    self.peers_table.setItem(i, 3, item_progress)

                    down_speed_item = QTableWidgetItem(f"{peer_info.get('down_speed', 0):.1f} KB/s")
                    down_speed_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.peers_table.setItem(i, 4, down_speed_item)
                    
                    up_speed_item = QTableWidgetItem(f"{peer_info.get('up_speed', 0):.1f} KB/s")
                    up_speed_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.peers_table.setItem(i, 5, up_speed_item)
                    
                    flags_item = QTableWidgetItem(peer_info.get('flags', '-'))
                    flags_item.setTextAlignment(Qt.AlignCenter)
                    self.peers_table.setItem(i, 6, flags_item)
                    
                    conn_type_item = QTableWidgetItem(peer_info.get('connection_type', 'N/A'))
                    conn_type_item.setTextAlignment(Qt.AlignCenter)
                    self.peers_table.setItem(i, 7, conn_type_item)
                    
                    source_item = QTableWidgetItem(peer_info.get('source', 'N/A'))
                    source_item.setTextAlignment(Qt.AlignCenter)
                    self.peers_table.setItem(i, 8, source_item)
            else:
                self.peers_table.setRowCount(0) # No peers, placeholder will show "No connected peers"
            self.peers_table.viewport().update()

    def clear_details(self):
        self._current_info_hash = None # Clear stored info_hash
        self.lbl_name.setText("Select a torrent to see details")
        self.lbl_save_path.setText("N/A")
        self.lbl_info_hash.setText("N/A")
        self.lbl_status.setText("N/A")
        self.lbl_total_size.setText("N/A")
        self.lbl_num_pieces.setText("N/A")
        # self.lbl_piece_length.setText("N/A") # Removed as it's combined
        self.lbl_availability.setText("N/A")
        self.lbl_added_on.setText("N/A")
        self.lbl_comment.setText("N/A")
        self.lbl_created_by.setText("N/A")
        self.lbl_creation_date.setText("N/A")

        # Clear files tab
        if hasattr(self, 'files_table'):
            self.files_table.setRowCount(0)
            self.files_table.viewport().update() # Show placeholder
        
        # Clear peers tab
        if hasattr(self, 'peers_table'):
            self.peers_table.setRowCount(0)
            self.peers_table.viewport().update() # Show placeholder

# Example usage (for testing, not part of the final app flow here)
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    # Create a dummy status dict for testing
    dummy_status = {
        'name': 'My Test Torrent File Name That Is Quite Long And Should Be Handled.mkv',
        'save_path': '/path/to/my/downloads/folder/also/quite/long',
        'info_hash': '1234567890abcdef1234567890abcdef12345678',
        'state': 'downloading',
        'total_size': 1024 * 1024 * 700, # 700MB
        'num_pieces': 700,
        'piece_length': 1024 * 1024, # 1MB
        'added_on': datetime.datetime.now().timestamp(),
        'distributed_copies': 1.2345
    }
    widget = TorrentDetailWidget()
    widget.update_details(dummy_status)
    widget.show()
    sys.exit(app.exec_()) 