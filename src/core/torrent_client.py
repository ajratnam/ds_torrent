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
    
    def __init__(self, handle, save_path, source):
        super().__init__()
        self.handle = handle
        self.save_path = save_path
        self.source = source # Store the original source (magnet or filepath)
        self.info = None
        self.files = [] # This will store file details dictionaries
        self.torrent_file = None
        self.last_error = None
        self.added_on = time.time() # Timestamp when torrent was added
        self.num_pieces = 0
        self.piece_length = 0
        
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
                    self.num_pieces = self.info.num_pieces()
                    self.piece_length = self.info.piece_length()
                
                name = self.handle.name()
                total_size = self.info.total_size()

                # Get file details if info is available
                file_statuses = []
                if self.info:
                    fs = self.info.files()
                    file_progress_lt = self.handle.file_progress(flags=lt.torrent_handle.piece_granularity) # Get progress per file
                    file_priorities = self.handle.get_file_priorities()

                    for i in range(fs.num_files()):
                        file_entry = fs.at(i)
                        file_path = file_entry.path
                        file_size = file_entry.size
                        downloaded_bytes = file_progress_lt[i] if i < len(file_progress_lt) else 0
                        priority = file_priorities[i] if i < len(file_priorities) else 0 # Default to 0 if not set
                        file_statuses.append({
                            'path': file_path,
                            'size': file_size,
                            'downloaded': downloaded_bytes,
                            'progress': (downloaded_bytes / file_size * 100) if file_size > 0 else 0,
                            'priority': priority
                        })
                self.files = file_statuses # Update self.files with detailed info
            else:
                # For magnet links without metadata
                name = "Fetching metadata..."
                total_size = 0
                # Get progress from DHT
                if status.has_metadata:
                    name = self.handle.name()
                    info = self.handle.get_torrent_info() # Get info once available
                    total_size = info.total_size()
                    self.num_pieces = info.num_pieces()
                    self.piece_length = info.piece_length()
                
            # Determine state and speeds
            if status.paused:
                state = "paused"
                download_rate = 0
                upload_rate = 0
            else:
                state = status.state.name
                download_rate = status.download_rate / 1024
                upload_rate = status.upload_rate / 1024
                
            # Calculate ETA
            eta_seconds = (total_size - status.total_done) / status.download_payload_rate if status.download_payload_rate > 0 and total_size > status.total_done else float('inf')
            
            # Calculate Ratio
            ratio = status.total_payload_upload / status.total_payload_download if status.total_payload_download > 0 else 0.0

            # Build status dictionary
            status_dict = {
                'name': name,
                'save_path': self.save_path,
                'progress': status.progress * 100,
                'download_rate': download_rate,
                'upload_rate': upload_rate,
                'state': state,
                'num_seeds': status.num_seeds, # Connected seeds
                'num_peers': status.num_peers, # Connected peers (does not include seeds)
                'total_seeds': status.list_seeds, # Total seeds in swarm
                'total_peers': status.list_peers, # Total peers in swarm (does not include seeds)
                'total_download': status.total_download / (1024 * 1024),
                'total_upload': status.total_upload / (1024 * 1024),
                'total_size': total_size,
                'has_metadata': status.has_metadata,
                'info_hash': str(self.handle.info_hash()),
                'error': self.last_error,
                'added_on': self.added_on,
                'eta': eta_seconds,
                'ratio': ratio,
                'num_pieces': self.num_pieces,
                'piece_length': self.piece_length,
                'distributed_copies': status.distributed_copies, # Availability
                'files': self.files if self.handle.has_metadata() else [] # Add files list to status_dict
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
            self.handle.auto_managed(False) # Ensure it stays paused
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
            self.handle.auto_managed(True) # Return to auto-management before resuming
            self.handle.resume()
            
            # Force tracker and DHT re-announce to find peers more quickly
            if self.handle.is_valid(): # Ensure handle is still valid
                self.handle.force_reannounce(0, -1) # 0 seconds, all trackers
                self.handle.force_dht_announce()
                logger.info(f"Forced re-announce for torrent: {str(self.handle.info_hash())}")

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

    def set_file_priority(self, file_index, priority_level):
        """Set the priority for a specific file in the torrent."""
        if not self.handle.is_valid() or not self.handle.has_metadata():
            logger.warning(f"Cannot set file priority for {self.handle.name()}: Handle invalid or no metadata.")
            self.error.emit(str(self.handle.info_hash()), "Cannot set file priority: No metadata or invalid handle.")
            return False
        
        torrent_info = self.handle.get_torrent_info()
        if file_index < 0 or file_index >= torrent_info.num_files():
            logger.warning(f"Invalid file_index {file_index} for torrent {self.handle.name()}.")
            self.error.emit(str(self.handle.info_hash()), f"Cannot set file priority: Invalid file index {file_index}.")
            return False

        try:
            self.handle.file_priority(file_index, priority_level)
            logger.info(f"Set priority for file {file_index} of torrent {self.handle.name()} to {priority_level}")
            # Optionally, re-fetch and emit status to update UI if priority changes affect it immediately
            # status = self.get_status()
            # if status:
            #     self.status_updated.emit(status)
            return True
        except Exception as e:
            logger.error(f"Error setting file priority for {self.handle.name()}, file {file_index}: {str(e)}")
            self.error.emit(str(self.handle.info_hash()), f"Error setting file priority: {str(e)}")
            return False


class TorrentClient(QObject):
    """Main torrent client class that manages the libtorrent session"""
    torrent_added = pyqtSignal(object)
    client_status_updated = pyqtSignal(dict)
    error = pyqtSignal(str)  # error_message
    
    def __init__(self, app_data_dir): # Added app_data_dir for path construction
        super().__init__()
        
        self.app_data_dir = app_data_dir
        self.resume_data_dir = os.path.join(self.app_data_dir, "resume")
        if not os.path.exists(self.resume_data_dir):
            try:
                os.makedirs(self.resume_data_dir)
            except OSError as e:
                logger.error(f"Failed to create resume data directory: {self.resume_data_dir} - {e}")
                # Fallback or error handling if directory creation fails
                self.resume_data_dir = "." # Fallback to current dir, not ideal

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
        
    def _get_resume_filepath(self, info_hash_str):
        return os.path.join(self.resume_data_dir, f"{info_hash_str}.fastresume")

    def add_torrent(self, source, save_path, resume_data_bytes=None):
        """
        Add a new torrent
        
        Args:
            source: Either a magnet link or path to a .torrent file
            save_path: Directory to save downloaded files
            resume_data_bytes: Optional bytes for resuming a torrent
        
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
                    if resume_data_bytes:
                        params.resume_data = resume_data_bytes
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
                    if resume_data_bytes:
                        params.resume_data = resume_data_bytes
                except Exception as e:
                    logger.error(f"Error loading torrent file: {str(e)}")
                    self.error.emit(f"Error loading torrent file: {str(e)}")
                    return None
            
            # Set save path
            params.save_path = save_path
            
            # Add the torrent to the session
            handle = self.session.add_torrent(params)
            
            # Create a handle object
            torrent = TorrentHandle(handle, save_path, source) # Pass source here
            
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
                # First, request resume data to be saved if the handle is valid
                # This is more of a "final save attempt" before removal.
                # The actual saving happens via alert.
                torrent_handle_obj = self.torrents[info_hash].handle
                if torrent_handle_obj.is_valid():
                    torrent_handle_obj.save_resume_data() 

                # Now remove from session
                self.session.remove_torrent(self.torrents[info_hash].handle, lt.session_handle.delete_files if delete_files else 0)
                
                # Delete the resume data file
                resume_filepath = self._get_resume_filepath(info_hash)
                if os.path.exists(resume_filepath):
                    try:
                        os.remove(resume_filepath)
                        logger.info(f"Deleted resume file: {resume_filepath}")
                    except OSError as e:
                        logger.error(f"Error deleting resume file {resume_filepath}: {e}")
                
                del self.torrents[info_hash] # Remove from our tracking dict
            except Exception as e:
                logger.error(f"Error removing torrent {info_hash}: {str(e)}")
                self.error.emit(f"Error removing torrent {info_hash}: {str(e)}")

    def trigger_save_resume_data(self, info_hash_str):
        """Requests libtorrent to save resume data for a specific torrent."""
        if info_hash_str in self.torrents:
            handle = self.torrents[info_hash_str].handle
            if handle.is_valid():
                handle.save_resume_data() # Request flags can be added here if needed
                logger.info(f"Requested resume data save for {info_hash_str}")
            else:
                logger.warning(f"Cannot save resume data, handle invalid for {info_hash_str}")
        else:
            logger.warning(f"Cannot save resume data, torrent not found: {info_hash_str}")

    def _monitor_alerts(self):
        """Monitor libtorrent alerts"""
        while True:
            try:
                alerts = self.session.pop_alerts()
                for alert in alerts:
                    info_hash_str = None
                    if hasattr(alert, 'handle') and alert.handle.is_valid():
                        info_hash_str = str(alert.handle.info_hash())

                    if isinstance(alert, lt.metadata_received_alert):
                        if info_hash_str and info_hash_str in self.torrents:
                            logger.info(f"Metadata received for torrent: {info_hash_str}")
                            # Force a status update, which will repopulate .info
                            status = self.torrents[info_hash_str].get_status()
                            if status:
                                self.torrents[info_hash_str].status_updated.emit(status)
                                
                    elif isinstance(alert, lt.metadata_failed_alert):
                        if info_hash_str and info_hash_str in self.torrents:
                            error_message = f"Metadata fetch failed for {info_hash_str}: {alert.error}"
                            logger.error(error_message)
                            self.torrents[info_hash_str].last_error = str(alert.error)
                            self.torrents[info_hash_str].error.emit(info_hash_str, str(alert.error))
                            # Also emit a status update to reflect the error state in the UI if needed
                            status = self.torrents[info_hash_str].get_status()
                            if status:
                                self.torrents[info_hash_str].status_updated.emit(status)

                    elif isinstance(alert, lt.torrent_finished_alert):
                        if info_hash_str and info_hash_str in self.torrents:
                            logger.info(f"Torrent finished: {info_hash_str}")
                            self.torrents[info_hash_str].completed.emit(info_hash_str)
                            # Ensure status reflects completion
                            status = self.torrents[info_hash_str].get_status()
                            if status:
                                 self.torrents[info_hash_str].status_updated.emit(status)
                                 
                    elif isinstance(alert, lt.torrent_error_alert):
                        if info_hash_str and info_hash_str in self.torrents:
                            error_message = f"Torrent error for {info_hash_str}: {alert.error}"
                            logger.error(error_message)
                            self.torrents[info_hash_str].last_error = str(alert.error)
                            self.torrents[info_hash_str].error.emit(info_hash_str, str(alert.error))
                            # Update status to show error
                            status = self.torrents[info_hash_str].get_status()
                            if status:
                                 self.torrents[info_hash_str].status_updated.emit(status)
                    
                    elif isinstance(alert, lt.save_resume_data_alert):
                        if info_hash_str and hasattr(alert, 'resume_data') and alert.resume_data:
                            filepath = self._get_resume_filepath(info_hash_str)
                            try:
                                resume_data_content = alert.resume_data
                                if isinstance(resume_data_content, dict):
                                    # This is unexpected. Log and skip.
                                    logger.error(f"Save resume data for {info_hash_str} is a dict, not bytes. Content: {resume_data_content}")
                                elif isinstance(resume_data_content, bytes):
                                    with open(filepath, 'wb') as f:
                                        f.write(resume_data_content)
                                    logger.info(f"Saved resume data for {info_hash_str} to {filepath}")
                                else:
                                    logger.error(f"Save resume data for {info_hash_str} is of unexpected type: {type(resume_data_content)}")
                            except IOError as e:
                                logger.error(f"Failed to write resume data for {info_hash_str} to {filepath}: {e}")
                        elif info_hash_str:
                             logger.warning(f"Save resume data alert for {info_hash_str} but no resume_data content or handle invalid.")

                    elif isinstance(alert, lt.save_resume_data_failed_alert):
                        if info_hash_str:
                            logger.error(f"Save resume data failed for {info_hash_str}: {alert.error}")
                        else:
                            logger.error(f"Save resume data failed: {alert.error} (handle no longer valid or unknown)")
                    
                    # Optional: Log other potentially useful alerts for debugging
                    # elif isinstance(alert, lt.dht_reply_alert):
                    #    logger.debug(f"DHT Reply: {alert.message()}")
                    # elif isinstance(alert, lt.peer_connect_alert):
                    #    logger.debug(f"Peer connect: {alert.ip} - {alert.message()}")
                    # elif isinstance(alert, lt.peer_disconnected_alert):
                    #    logger.debug(f"Peer disconnect: {alert.ip} - {alert.message()} - {alert.reason}")

            except Exception as e:
                logger.error(f"Error in alert monitor: {str(e)}")
            time.sleep(0.1) # Reduced sleep time for more responsive alert handling
            
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

    def set_torrent_file_priority(self, info_hash, file_index, priority_level):
        """Set file priority for a torrent identified by info_hash."""
        if info_hash in self.torrents:
            torrent_handle_obj = self.torrents[info_hash]
            return torrent_handle_obj.set_file_priority(file_index, priority_level)
        else:
            logger.warning(f"Cannot set file priority: Torrent {info_hash} not found.")
            self.error.emit(f"Cannot set file priority: Torrent {info_hash} not found.")
            return False