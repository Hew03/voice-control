import keyboard

class HotkeyManager:
    def __init__(self, config_manager, message_queue):
        self.config_manager = config_manager
        self.message_queue = message_queue
        self.callbacks = {}
        self.is_setup = False
    
    def setup_hotkeys(self):
        """Setup keyboard hooks for hotkeys"""
        try:
            if self.is_setup:
                keyboard.unhook_all()
            
            keyboard.hook(self._on_key_event)
            self.is_setup = True
            return True
        except Exception as e:
            self.message_queue.put(("error", f"Hotkey setup failed: {e}"))
            return False
    
    def register_hotkey(self, hotkey_name, callback):
        """Register a callback for a specific hotkey"""
        self.callbacks[hotkey_name] = callback
    
    def unregister_hotkey(self, hotkey_name):
        """Unregister a hotkey callback"""
        if hotkey_name in self.callbacks:
            del self.callbacks[hotkey_name]
    
    def _on_key_event(self, e):
        """Handle keyboard events"""
        if e.event_type == 'down':
            if e.name == self.config_manager.get('hotkey'):
                if 'recording_toggle' in self.callbacks:
                    self.callbacks['recording_toggle']()
            
            for hotkey_name, callback in self.callbacks.items():
                if hotkey_name != 'recording_toggle':
                    pass
    
    def update_hotkey(self, new_hotkey):
        """Update the main hotkey"""
        self.config_manager.set('hotkey', new_hotkey)
        return self.setup_hotkeys()
    
    def cleanup(self):
        """Cleanup keyboard hooks"""
        try:
            if self.is_setup:
                keyboard.unhook_all()
                self.is_setup = False
        except:
            pass