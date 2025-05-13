from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QFormLayout, 
                            QLabel, QLineEdit, QGroupBox, QTableWidget, 
                            QTableWidgetItem, QHeaderView, QProgressBar,
                            QMenu, QAction)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor # Import QColor
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
        self.files_tab = QWidget()
        layout = QVBoxLayout(self.files_tab)
        layout.setContentsMargins(5, 5, 5, 5)

        self.files_table = QTableWidget()
        self.files_table.setColumnCount(5)
        self.files_table.setHorizontalHeaderLabels(["Path", "Size", "Progress", "Downloaded", "Priority"])
        self.files_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.files_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.files_table.verticalHeader().setVisible(False)
        self.files_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.files_table.customContextMenuRequested.connect(self._show_files_table_context_menu)

        header = self.files_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch) # Path
        header.setSectionResizeMode(1, QHeaderView.Interactive) # Size
        header.setSectionResizeMode(2, QHeaderView.Stretch) # Progress
        header.setSectionResizeMode(3, QHeaderView.Interactive) # Downloaded
        header.setSectionResizeMode(4, QHeaderView.Interactive) # Priority

        self.files_table.setColumnWidth(1, 100) # Size
        self.files_table.setColumnWidth(3, 100) # Downloaded
        self.files_table.setColumnWidth(4, 100) # Priority
        
        layout.addWidget(self.files_table)
        self.tab_widget.addTab(self.files_tab, "Files")

    def _create_peers_tab(self):
        self.peers_tab = QWidget()
        layout = QVBoxLayout(self.peers_tab)
        layout.setContentsMargins(5, 5, 5, 5)

        self.peers_table = QTableWidget()
        self.peers_table.setColumnCount(9) # IP, Port, Client, Progress, Down, Up, Flags, Type, Source
        self.peers_table.setHorizontalHeaderLabels([
            "IP Address", "Port", "Client", "Progress", 
            "Down Speed", "Up Speed", "Flags", "Conn. Type", "Source"
        ])
        self.peers_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.peers_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.peers_table.verticalHeader().setVisible(False)
        self.peers_table.setAlternatingRowColors(True)

        header = self.peers_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive) # IP Address
        header.setSectionResizeMode(1, QHeaderView.Interactive) # Port
        header.setSectionResizeMode(2, QHeaderView.Stretch)   # Client
        header.setSectionResizeMode(3, QHeaderView.Interactive) # Progress
        header.setSectionResizeMode(6, QHeaderView.Interactive) # Flags
        header.setSectionResizeMode(7, QHeaderView.Interactive) # Conn. Type
        header.setSectionResizeMode(8, QHeaderView.Interactive) # Source

        self.peers_table.setColumnWidth(0, 120) # IP
        self.peers_table.setColumnWidth(1, 50)  # Port
        self.peers_table.setColumnWidth(3, 80)  # Progress
        self.peers_table.setColumnWidth(4, 80)  # Down Speed
        self.peers_table.setColumnWidth(5, 80)  # Up Speed
        self.peers_table.setColumnWidth(6, 80)  # Flags
        self.peers_table.setColumnWidth(7, 80)  # Conn. Type
        self.peers_table.setColumnWidth(8, 80)  # Source
        
        layout.addWidget(self.peers_table)
        self.tab_widget.addTab(self.peers_tab, "Peers")

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
        # libtorrent priorities:
        # 0: Don't download
        # 1: Normal priority
        # 4: Normal (some clients use 4 as default)
        # 6: High priority
        # 7: Maximal priority
        if priority_val == 0:
            return "Don't Download"
        elif priority_val == 1 or priority_val == 4: # Treat 1 and 4 as Normal
            return "Normal"
        elif priority_val == 6:
            return "High"
        elif priority_val == 7:
            return "Maximal"
        else:
            return f"Unknown ({priority_val})"

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
        
        num_pieces = status_dict.get('num_pieces', 0)
        piece_length = status_dict.get('piece_length', 0)
        self.lbl_num_pieces.setText(f"{num_pieces}")
        self.lbl_piece_length.setText(_format_bytes(piece_length))

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
            except:
                self.lbl_added_on.setText("N/A")
        else:
            self.lbl_added_on.setText("N/A")

        # Update files tab
        if hasattr(self, 'files_table'):
            self.files_table.setRowCount(0) # Clear previous entries
            files_data = status_dict.get('files', [])
            if files_data:
                self.files_table.setRowCount(len(files_data))
                for i, file_info in enumerate(files_data):
                    self.files_table.setItem(i, 0, QTableWidgetItem(file_info.get('path', 'N/A')))
                    self.files_table.setItem(i, 1, QTableWidgetItem(_format_bytes(file_info.get('size', 0))))
                    
                    progress_val = file_info.get('progress', 0)
                    progress_bar = QProgressBar()
                    progress_bar.setValue(int(progress_val))
                    progress_bar.setTextVisible(True)
                    progress_bar.setFormat(f"{progress_val:.1f}%")
                    self.files_table.setCellWidget(i, 2, progress_bar)
                    
                    self.files_table.setItem(i, 3, QTableWidgetItem(_format_bytes(file_info.get('downloaded', 0))))
                    priority_str = self._format_file_priority(file_info.get('priority', 0))
                    self.files_table.setItem(i, 4, QTableWidgetItem(priority_str))
            else:
                # Show a message if no files or metadata not yet available
                self.files_table.setRowCount(1)
                no_files_item = QTableWidgetItem("No file information available (or metadata not yet received).")
                no_files_item.setTextAlignment(Qt.AlignCenter)
                self.files_table.setItem(0, 0, no_files_item)
                self.files_table.setSpan(0, 0, 1, self.files_table.columnCount())

        # Update peers tab
        if hasattr(self, 'peers_table'):
            self.peers_table.setRowCount(0)
            peers_data = status_dict.get('peers', [])
            if peers_data:
                self.peers_table.setRowCount(len(peers_data))
                for i, peer_info in enumerate(peers_data):
                    self.peers_table.setItem(i, 0, QTableWidgetItem(peer_info.get('ip', 'N/A')))
                    self.peers_table.setItem(i, 1, QTableWidgetItem(str(peer_info.get('port', 'N/A'))))
                    self.peers_table.setItem(i, 2, QTableWidgetItem(peer_info.get('client', 'N/A')))
                    
                    progress_val = peer_info.get('progress', 0)
                    # Using a simple text item for peer progress, can be changed to a bar if desired
                    item_progress = QTableWidgetItem(f"{progress_val:.1f}%")
                    self.peers_table.setItem(i, 3, item_progress)

                    self.peers_table.setItem(i, 4, QTableWidgetItem(f"{peer_info.get('down_speed', 0):.1f} KB/s"))
                    self.peers_table.setItem(i, 5, QTableWidgetItem(f"{peer_info.get('up_speed', 0):.1f} KB/s"))
                    self.peers_table.setItem(i, 6, QTableWidgetItem(peer_info.get('flags', '-')))
                    self.peers_table.setItem(i, 7, QTableWidgetItem(peer_info.get('connection_type', 'N/A')))
                    self.peers_table.setItem(i, 8, QTableWidgetItem(peer_info.get('source', 'N/A')))
            else:
                self.peers_table.setRowCount(1)
                no_peers_item = QTableWidgetItem("No peer information available.")
                no_peers_item.setTextAlignment(Qt.AlignCenter)
                self.peers_table.setItem(0, 0, no_peers_item)
                self.peers_table.setSpan(0, 0, 1, self.peers_table.columnCount())

    def clear_details(self):
        self._current_info_hash = None # Clear stored info_hash
        self.lbl_name.setText("N/A")
        self.lbl_save_path.setText("N/A")
        self.lbl_info_hash.setText("N/A")
        self.lbl_status.setText("N/A")
        self.lbl_total_size.setText("N/A")
        self.lbl_num_pieces.setText("N/A")
        self.lbl_piece_length.setText("N/A")
        self.lbl_availability.setText("N/A")
        self.lbl_added_on.setText("N/A")
        self.lbl_comment.setText("N/A")
        self.lbl_created_by.setText("N/A")
        self.lbl_creation_date.setText("N/A")

        # Clear files tab
        if hasattr(self, 'files_table'):
            self.files_table.setRowCount(0)
        
        # Clear peers tab
        if hasattr(self, 'peers_table'):
            self.peers_table.setRowCount(0)

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