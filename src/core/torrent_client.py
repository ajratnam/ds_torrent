import libtorrent as lt
import time
import os
from threading import Thread
from PyQt5.QtCore import QObject, pyqtSignal
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
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
        self.is_completed_flag = False # New flag for completion status
        
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
            
            # Get Peer Info
            peer_list = []
            if self.handle.is_valid(): # Ensure handle is valid before getting peer info
                for peer_info in self.handle.get_peer_info():
                    # Decode client name if possible
                    client_name = peer_info.client.decode('utf-8', 'ignore') if peer_info.client else "N/A"
                    # Format flags
                    flags_str = self._format_peer_flags(peer_info.flags)
                    conn_type_str = self._format_connection_type(peer_info.connection_type)

                    # Log raw peer progress
                    # logger.debug(f"Peer {peer_info.ip[0]}:{peer_info.ip[1]} raw progress: {peer_info.progress}, client: {client_name}")

                    peer_list.append({
                        'ip': peer_info.ip[0],
                        'port': peer_info.ip[1],
                        'client': client_name,
                        'progress': peer_info.progress * 100,
                        'down_speed': peer_info.down_speed / 1024,
                        'up_speed': peer_info.up_speed / 1024,
                        'flags': flags_str,
                        'connection_type': conn_type_str,
                        'source': self._format_peer_source_flags(peer_info.source) # e.g., DHT, PEX, LPD
                    })

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
                'files': self.files if self.handle.has_metadata() else [], # Add files list to status_dict
                'peers': peer_list
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

    # Helper methods for formatting peer info
    def _format_peer_flags(self, flags):
        flag_map = {
            lt.peer_info.interesting: "I", # We are interested in the peer
            lt.peer_info.choked: "C",       # We are choked by the peer
            lt.peer_info.remote_interested: "i", # Peer is interested in us
            lt.peer_info.remote_choked: "c",   # Peer is choked by us
            lt.peer_info.supports_extensions: "E", # Supports extensions
            lt.peer_info.outgoing_connection: "O", # Outgoing connection
            lt.peer_info.handshake: "H",         # Handshake completed
            lt.peer_info.connecting: "N",      # Connecting
            lt.peer_info.on_parole: "P",         # On parole (optimistic unchoke)
            lt.peer_info.seed: "S",              # Peer is a seed
            lt.peer_info.optimistic_unchoke: "U", # Optimistic unchoke
            lt.peer_info.snubbed: "X",           # Snubbed
            lt.peer_info.upload_only: "L",     # Upload only
            lt.peer_info.endgame_mode: "G",    # In endgame mode
            lt.peer_info.holepunched: "V",     # Holepunched
            # lt.peer_info.local_connection: "LC", # This might conflict with upload_only 'L' if not careful
        }
        s = []
        for flag, char in flag_map.items():
            if flags & flag:
                s.append(char)
        return "".join(s) if s else "-"

    def _format_connection_type(self, conn_type):
        conn_map = {
            lt.peer_info.standard_bittorrent: "BT", # Generic BitTorrent connection
            lt.peer_info.web_seed: "Web",
            lt.peer_info.http_seed: "HTTP",
            # We are removing explicit uTP detection for now due to compatibility issues
            # lt.peer_info.bittorrent_utp: "uTP" 
        }
        
        formatted_type = conn_map.get(conn_type)
        if formatted_type:
            return formatted_type
        else:
            return f"Unknown({conn_type})"

    def _format_peer_source_flags(self, source_flags):
        source_map = {
            lt.peer_info.tracker: "Tr",
            lt.peer_info.dht: "DHT",
            lt.peer_info.pex: "PEX",
            lt.peer_info.lsd: "LSD",
            lt.peer_info.resume_data: "Res"
            # Removed incoming_connection due to persistent errors
            # lt.peer_info.incoming_connection: "In" 
        }
        s = []
        for flag, char in source_map.items():
            if source_flags & flag:
                s.append(char)
        return ",".join(s) if s else "-"

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
        
    def get_session_settings(self):
        """Return the current libtorrent session settings pack."""
        return self.session.get_settings() # This returns a settings_pack dictionary (actually an object)

    def apply_session_settings(self, settings_dict_str_keys):
        """Apply a dictionary of settings (with string keys) to the libtorrent session."""
        try:
            # libtorrent session.apply_settings() can typically handle a dictionary 
            # with string keys mapping to their respective values.
            self.session.apply_settings(settings_dict_str_keys)
            # logger.info(f"Applied session settings: {settings_dict_str_keys}")
            
            # Important: Check if listen_interfaces was changed and needs special handling.
            # If 'listen_interfaces' is in settings_dict_str_keys and the port or IP changed,
            # it might be necessary to call self.session.listen_on() again.
            # For now, we assume apply_settings handles this, or it's managed by a restart if needed.
            # Example: if 'listen_interfaces' in settings_dict_str_keys:
            #    new_listen_interfaces = settings_dict_str_keys['listen_interfaces']
            #    # Potentially parse and call self.session.listen_on(port, ip, flags)
            #    # This is complex due to parsing IP and port, and existing listen sockets.
            #    # For simplicity, we rely on apply_settings or a client restart for listen port changes.

        except Exception as e:
            logger.error(f"Error applying session settings: {e}")
            self.error.emit(f"Error applying session settings: {e}")
        
    def _get_resume_filepath(self, info_hash_str):
        return os.path.join(self.resume_data_dir, f"{info_hash_str}.fastresume")

    def add_torrent(self, source, save_path, resume_data_bytes=None, is_completed_on_load=False):
        """
        Add a new torrent. For completed magnet links, we add normally and rely on recheck.
        
        Args:
            source: Either a magnet link or path to a .torrent file
            save_path: Directory to save downloaded files
            resume_data_bytes: Optional bytes for resuming a torrent. For magnets, this is now primarily
                               used to decide if a recheck is needed, not for direct seed_mode.
            is_completed_on_load: Boolean indicating if the torrent should be marked as completed on load
        
        Returns:
            TorrentHandle object or None on failure
        """
        handle = None 
        params = None 

        try:
            if source.startswith('magnet:'):
                try:
                    logger.info(f"Processing magnet link for add_torrent: {source[:70]}...")
                    params = lt.parse_magnet_uri(source)
                    params.save_path = save_path
                    
                    # Standard flags: auto managed, not paused.
                    # We will NOT set upload_mode or seed_mode here for magnets, even if completed_on_load.
                    # We also WON'T set resume_data here for magnets due to the ArgumentError.
                    params.flags |= lt.torrent_flags.auto_managed 
                    params.flags &= ~lt.torrent_flags.paused

                    if is_completed_on_load:
                        logger.info(f"Magnet is_completed_on_load ({source[:70]}...). Will add normally and rely on metadata + recheck.")
                        # Resume data is not applied here directly for magnets to avoid ArgumentError.
                    elif resume_data_bytes:
                        # For non-completed magnets, if we had a way to apply resume_data without error, we would.
                        # But since it errors, we omit it. The torrent will start fresh or from existing files found by recheck.
                        logger.info(f"Magnet is NOT completed_on_load, but has resume_data. Will add normally. {source[:70]}")

                    logger.debug(
                        f"Attempting self.session.add_torrent for magnet (NO resume_data, NO upload/seed_mode). "
                        f"Name: '{params.name if hasattr(params, 'name') else 'N/A'}', "
                        f"InfoHashes: '{params.info_hashes if hasattr(params, 'info_hashes') else 'N/A'}', "
                        f"SavePath: '{params.save_path}', Flags: {params.flags}"
                    )
                    handle = self.session.add_torrent(params)
                    logger.info(f"self.session.add_torrent call completed for magnet {source[:70]}. Handle valid: {handle.is_valid()}")

                except Exception as e:
                    logger.error(f"Error in magnet processing block for [{source[:70]}...]: {type(e).__name__} - {str(e)}")
                    self.error.emit(f"Error processing magnet link: {str(e)}")
                    return None
            # Handle torrent files (can still use resume_data and seed_mode directly if ti is present)
            else:
                params = lt.add_torrent_params() 
                try:
                    logger.info(f"Processing .torrent file for add_torrent: {source}")
                    info = lt.torrent_info(source)
                    params.ti = info # Crucial: torrent_info is present
                    params.save_path = save_path
                    params.flags |= lt.torrent_flags.auto_managed
                    params.flags &= ~lt.torrent_flags.paused 

                    if is_completed_on_load and resume_data_bytes:
                        logger.info(f"File is completed_on_load. Assigning resume_data ({len(resume_data_bytes)} bytes) BEFORE setting SEED_MODE.")
                        params.resume_data = resume_data_bytes # Assign resume_data FIRST
                        params.flags |= lt.torrent_flags.seed_mode # THEN set seed_mode (preferred for files)
                        logger.info(f"SEED_MODE flag set for completed file {source}.")
                    elif resume_data_bytes: 
                        params.resume_data = resume_data_bytes
                    
                    logger.debug(
                        f"Attempting self.session.add_torrent for file. "
                        f"Name: '{params.name if hasattr(params, 'name') else 'N/A'}', "
                        f"SavePath: '{params.save_path}', Flags: {params.flags}, "
                        f"ResumeData: {len(params.resume_data) if hasattr(params, 'resume_data') and params.resume_data else 'None'}"
                    )
                    handle = self.session.add_torrent(params)
                    logger.info(f"self.session.add_torrent call completed for file {source}. Handle valid: {handle.is_valid()}")

                except Exception as e:
                    logger.error(f"Error loading torrent file {source}: {str(e)}")
                    self.error.emit(f"Error loading torrent file: {str(e)}")
                    return None
            
            if not handle or not handle.is_valid():
                logger.error(f"Failed to obtain a valid torrent handle for {source[:70]}...")
                self.error.emit(f"Failed to add torrent: {source[:70]}...")
                return None

            torrent_handle_wrapper = TorrentHandle(handle, save_path, source)
            
            if is_completed_on_load:
                torrent_handle_wrapper.is_completed_flag = True
                logger.info(f"Torrent {source[:70]} marked with is_completed_flag = True in wrapper.")

            info_hash = str(handle.info_hash())
            self.torrents[info_hash] = torrent_handle_wrapper
            
            # Force recheck for completed magnets (after metadata) or any torrent with resume data/completed file
            # The actual recheck for magnets will effectively happen once metadata is received and this is called again
            # or if torrent_added signal triggers a recheck in MainWindow based on is_completed_flag.
            if handle.is_valid(): 
                if source.startswith('magnet:'):
                    if is_completed_on_load: # For completed magnets, we want a recheck after metadata
                        logger.info(f"Magnet {info_hash} is_completed_on_load. Will rely on metadata_received and subsequent recheck.")
                        # No immediate force_recheck here as metadata isn't available yet.
                        # The recheck should be triggered by metadata_received_alert logic or UI.
                    elif resume_data_bytes:
                         # If it's a magnet that wasn't marked completed but had resume data (which we couldn't apply)
                         # a recheck after metadata might still be useful.
                        logger.info(f"Magnet {info_hash} had resume_data (not applied). Recheck will occur after metadata.")

                elif resume_data_bytes or (not source.startswith('magnet:') and is_completed_on_load):
                    # This covers .torrent files with resume data, or completed .torrent files.
                    logger.info(f"File-based torrent {info_hash} with resume_data/completed_flag. Triggering immediate recheck.")
                    handle.force_recheck()
            
            torrent_handle_wrapper.error.connect(lambda ih, msg: self.error.emit(f"Torrent {ih}: {msg}"))
            self.torrent_added.emit(torrent_handle_wrapper)
            return torrent_handle_wrapper
            
        except Exception as e: 
            logger.error(f"Outer scope error adding torrent {source[:70]}...: {type(e).__name__} - {str(e)}")
            self.error.emit(f"Outer scope error adding torrent: {str(e)}")
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
                    torrent_handle_obj.save_resume_data(lt.torrent_handle.save_info_dict)
                    logger.info(f"Requested resume data save (with info_dict) for {info_hash} before removal.")

                # Now remove from session
                self.session.remove_torrent(self.torrents[info_hash].handle, lt.session.delete_files if delete_files else 0)
                
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
                # Request flags can be added here if needed
                handle.save_resume_data(lt.torrent_handle.save_info_dict) 
                logger.info(f"Requested resume data save (with info_dict) for {info_hash_str}")
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
                            torrent_obj = self.torrents[info_hash_str]
                            status = torrent_obj.get_status()
                            if status:
                                torrent_obj.status_updated.emit(status)
                                
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
                            torrent_obj = self.torrents[info_hash_str]
                            
                            should_notify = not torrent_obj.is_completed_flag # Check flag BEFORE setting it
                            torrent_obj.is_completed_flag = True # Set the flag

                            if should_notify:
                                torrent_obj.completed.emit(info_hash_str) # Only emit if it wasn't already complete
                            
                            # Ensure status reflects completion anyway for UI updates
                            status = torrent_obj.get_status()
                            if status:
                                 torrent_obj.status_updated.emit(status)
                                 
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
                                    # Bencode the dictionary to bytes before writing
                                    logger.info(f"Resume data for {info_hash_str} is a dict, bencoding it.")
                                    bencoded_data = lt.bencode(resume_data_content)
                                    with open(filepath, 'wb') as f:
                                        f.write(bencoded_data)
                                    logger.info(f"Saved bencoded resume data for {info_hash_str} to {filepath}")
                                elif isinstance(resume_data_content, bytes):
                                    with open(filepath, 'wb') as f:
                                        f.write(resume_data_content)
                                    logger.info(f"Saved resume data (bytes) for {info_hash_str} to {filepath}")
                                else:
                                    logger.error(f"Save resume data for {info_hash_str} is of unexpected type: {type(resume_data_content)}")
                            except IOError as e:
                                logger.error(f"Failed to write resume data for {info_hash_str} to {filepath}: {e}")
                            except Exception as e: # Catch potential bencode errors or other issues
                                logger.error(f"Error processing or writing resume data for {info_hash_str}: {e}")
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