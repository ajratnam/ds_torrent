import libtorrent as lt
import time
import os
import json
import logging

log = logging.getLogger(__name__)


class TorrentClient:
    def apply_session_settings(self, settings_dict: dict):
        log.info(f"Attempting to apply session settings: {settings_dict}")
        # self.current_settings can be a settings_pack object, ensure we're updating it correctly
        # or that it's a plain dict. Assuming it's kept as a dict.

        successfully_applied_keys = []
        for key, value in settings_dict.items():
            try:
                self.session.apply_settings({key: value})
                log.info(f"Successfully applied setting: {key}: {value}")
                successfully_applied_keys.append(key)
            except RuntimeError as e:
                log.error(f"Error applying individual setting '{key}': {value} -> {e}. Skipping this setting.")

        # Update self.current_settings to reflect the true state of the session
        # Fetch all current settings from the session after attempts.
        effective_settings_pack = self.session.get_settings()
        self.current_settings = {str(k): effective_settings_pack[k] for k in effective_settings_pack}

        log.info(f"Session settings after selective application. Successfully applied keys: {successfully_applied_keys}")
        log.debug(f"Full effective settings in client after apply: {self.current_settings}")

    def get_session_settings(self) -> dict:
        # Ensure this returns a plain dict for easier manipulation and logging downstream
        settings_pack_obj = self.session.get_settings()
        return {str(k): settings_pack_obj[k] for k in settings_pack_obj}

    def _monitor_alerts(self):
        # ... existing code ... 