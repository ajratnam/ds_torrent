import libtorrent as lt
import time
import os
from threading import Thread
from PyQt5.QtCore import QObject, pyqtSignal
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TorrentHandle(QObject):
    """Class representing a single torrent download"""
    status_updated = pyqtSignal(dict)
    completed = pyqtSignal(str)
    error = pyqtSignal(str, str)  # info_hash, error_message
    
    def __init__(self, handle, save_path):
        super().__init__()
        self.handle = handle
        self.save_path = save_path
        self.info = None
        self.files = []
        self.torrent_file = None
        self.last_error = None
        
    def get_status(self):
        """Get current status of the torrent"""
        try:
            status = self.handle.status()
            
            # Get name and size if we have metadata
            if self.handle.has_metadata():
                if not self.info:
                    self.info = self.handle.get_torrent_info()
                    if hasattr(self.info, 'torrent_file'):
                        self.torrent_file = self.info.torrent_file()
                    self.files = [self.info.files().file_path(i) for i in range(self.info.files().num_files())]
                
                name = self.handle.name()
                total_size = self.info.total_size()
            else:
                # For magnet links without metadata
                name = "Fetching metadata..."
                total_size = 0
                # Get progress from DHT
                if status.has_metadata:
                    name = self.handle.name()
                    total_size = self.handle.get_torrent_info().total_size()
                
            # Determine state and speeds
            if status.paused:
                state = "paused"
                download_rate = 0
                upload_rate = 0
            else:
                state = status.state.name
                download_rate = status.download_rate / 1024
                upload_rate = status.upload_rate / 1024
                
            # Build status dictionary
            status_dict = {
                'name': name,
                'save_path': self.save_path,
                'progress': status.progress * 100,
                'download_rate': download_rate,
                'upload_rate': upload_rate,
                'state': state,
                'num_seeds': status.num_seeds,
                'num_peers': status.num_peers,
                'total_download': status.total_download / (1024 * 1024),
                'total_upload': status.total_upload / (1024 * 1024),
                'total_size': total_size,
                'has_metadata': status.has_metadata,
                'info_hash': str(self.handle.info_hash()),
                'error': self.last_error
            }
            
            return status_dict
            
        except Exception as e:
            logger.error(f"Error getting torrent status: {str(e)}")
            self.last_error = str(e)
            self.error.emit(str(self.handle.info_hash()), str(e))
            return None
        
    def pause(self):
        """Pause the torrent"""
        try:
            self.handle.pause()
            # Force a status update with zero speeds
            status = self.get_status()
            if status:
                status['download_rate'] = 0
                status['upload_rate'] = 0
                self.status_updated.emit(status)
        except Exception as e:
            logger.error(f"Error pausing torrent: {str(e)}")
            self.last_error = str(e)
            self.error.emit(str(self.handle.info_hash()), str(e))
        
    def resume(self):
        """Resume the torrent"""
        try:
            self.handle.resume()
            # Force a status update
            status = self.get_status()
            if status:
                self.status_updated.emit(status)
        except Exception as e:
            logger.error(f"Error resuming torrent: {str(e)}")
            self.last_error = str(e)
            self.error.emit(str(self.handle.info_hash()), str(e))
        
    def remove(self, delete_files=False):
        """Remove the torrent"""
        try:
            lt.session().remove_torrent(self.handle, int(delete_files))
        except Exception as e:
            logger.error(f"Error removing torrent: {str(e)}")
            self.last_error = str(e)
            self.error.emit(str(self.handle.info_hash()), str(e))


class TorrentClient(QObject):
    """Main torrent client class that manages the libtorrent session"""
    torrent_added = pyqtSignal(object)
    client_status_updated = pyqtSignal(dict)
    error = pyqtSignal(str)  # error_message
    
    def __init__(self):
        super().__init__()
        
        # Create libtorrent session
        self.session = lt.session()
        
        # Apply settings
        settings = {
            'alert_mask': lt.alert.category_t.all_categories,
            'enable_dht': True,
            'enable_lsd': True,
            'enable_natpmp': True,
            'enable_upnp': True,
            'listen_interfaces': '0.0.0.0:6881',
            'download_rate_limit': 0,  # No limit
            'upload_rate_limit': 0,    # No limit
            'active_downloads': -1,    # No limit
            'active_seeds': -1,        # No limit
            'active_limit': -1,        # No limit
            'dht_bootstrap_nodes': 'router.bittorrent.com:6881,router.utorrent.com:6881,dht.transmissionbt.com:6881'
        }
        self.session.apply_settings(settings)
        
        # Start DHT
        self.session.start_dht()
        
        # Store handles
        self.torrents = {}
        
        # Start the alert handling thread
        self.monitor_thread = Thread(target=self._monitor_alerts)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        # Status update thread
        self.update_thread = Thread(target=self._update_status)
        self.update_thread.daemon = True
        self.update_thread.start()
        
    def add_torrent(self, source, save_path):
        """
        Add a new torrent
        
        Args:
            source: Either a magnet link or path to a .torrent file
            save_path: Directory to save downloaded files
        
        Returns:
            TorrentHandle object
        """
        try:
            params = lt.add_torrent_params()
            
            # Handle magnet links
            if source.startswith('magnet:'):
                try:
                    params = lt.parse_magnet_uri(source)
                    # Set flags for magnet links
                    params.flags |= lt.torrent_flags.auto_managed
                    params.flags &= ~lt.torrent_flags.paused
                except Exception as e:
                    logger.error(f"Error parsing magnet link: {str(e)}")
                    self.error.emit(f"Error parsing magnet link: {str(e)}")
                    return None
            # Handle torrent files
            else:
                try:
                    # Load the .torrent file
                    info = lt.torrent_info(source)
                    params.ti = info
                    # Set flags for torrent files
                    params.flags |= lt.torrent_flags.auto_managed
                    params.flags &= ~lt.torrent_flags.paused
                except Exception as e:
                    logger.error(f"Error loading torrent file: {str(e)}")
                    self.error.emit(f"Error loading torrent file: {str(e)}")
                    return None
            
            # Set save path
            params.save_path = save_path
            
            # Add the torrent to the session
            handle = self.session.add_torrent(params)
            
            # Create a handle object
            torrent = TorrentHandle(handle, save_path)
            
            # Store the handle
            info_hash = str(handle.info_hash())
            self.torrents[info_hash] = torrent
            
            # Start the torrent
            handle.set_sequential_download(False)
            handle.set_priority(1)
            
            # For torrent files, verify files exist
            if not source.startswith('magnet:'):
                try:
                    # Check if save path exists
                    if not os.path.exists(save_path):
                        os.makedirs(save_path)
                except Exception as e:
                    logger.error(f"Error creating save directory: {str(e)}")
                    self.error.emit(f"Error creating save directory: {str(e)}")
            
            # Connect error signal
            torrent.error.connect(lambda info_hash, msg: self.error.emit(f"Torrent {info_hash}: {msg}"))
            
            # Emit the signal
            self.torrent_added.emit(torrent)
            
            return torrent
            
        except Exception as e:
            logger.error(f"Error adding torrent: {str(e)}")
            self.error.emit(f"Error adding torrent: {str(e)}")
            return None
    
    def remove_torrent(self, info_hash, delete_files=False):
        """Remove a torrent by its info hash"""
        if info_hash in self.torrents:
            try:
                torrent = self.torrents[info_hash]
                torrent.remove(delete_files)
                del self.torrents[info_hash]
            except Exception as e:
                logger.error(f"Error removing torrent: {str(e)}")
                self.error.emit(f"Error removing torrent: {str(e)}")
            
    def _monitor_alerts(self):
        """Monitor libtorrent alerts"""
        while True:
            try:
                alerts = self.session.pop_alerts()
                for alert in alerts:
                    if isinstance(alert, lt.torrent_finished_alert):
                        info_hash = str(alert.handle.info_hash())
                        if info_hash in self.torrents:
                            # Emit completed signal
                            self.torrents[info_hash].completed.emit(info_hash)
                    elif isinstance(alert, lt.torrent_error_alert):
                        info_hash = str(alert.handle.info_hash())
                        if info_hash in self.torrents:
                            self.torrents[info_hash].error.emit(info_hash, str(alert.error))
            except Exception as e:
                logger.error(f"Error in alert monitor: {str(e)}")
            time.sleep(0.5)
            
    def _update_status(self):
        """Update status of all torrents"""
        while True:
            try:
                # Update individual torrent status
                for torrent in self.torrents.values():
                    status = torrent.get_status()
                    if status:
                        torrent.status_updated.emit(status)
                
                # Update overall client status
                download_rate = sum(t.handle.status().download_rate for t in self.torrents.values())
                upload_rate = sum(t.handle.status().upload_rate for t in self.torrents.values())
                
                self.client_status_updated.emit({
                    'num_torrents': len(self.torrents),
                    'download_rate': download_rate / 1024,
                    'upload_rate': upload_rate / 1024
                })
            except Exception as e:
                logger.error(f"Error updating status: {str(e)}")
            time.sleep(1)
            
    def set_download_limit(self, limit_kbps):
        """Set global download rate limit in KiB/s"""
        try:
            self.session.set_download_rate_limit(limit_kbps * 1024)
        except Exception as e:
            logger.error(f"Error setting download limit: {str(e)}")
            self.error.emit(f"Error setting download limit: {str(e)}")
        
    def set_upload_limit(self, limit_kbps):
        """Set global upload rate limit in KiB/s"""
        try:
            self.session.set_upload_rate_limit(limit_kbps * 1024)
        except Exception as e:
            logger.error(f"Error setting upload limit: {str(e)}")
            self.error.emit(f"Error setting upload limit: {str(e)}") 